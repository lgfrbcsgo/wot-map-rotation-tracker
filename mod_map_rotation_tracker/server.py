import json
import re
from typing import List

import BigWorld
from constants import ARENA_BONUS_TYPE
from debug_utils import LOG_NOTE
from helpers import dependency
from mod_async import CallbackCancelled, async_task, auto_run, await_event, delay, run
from mod_async_server import Server
from mod_websocket_server import MessageStream, websocket_protocol
from PlayerEvents import g_playerEvents
from skeletons.connection_mgr import IConnectionManager

PORT = 15457

ORIGIN_WHITELIST = [
    re.compile("^https?://localhost(:[0-9]{1,5})?$"),
    "https://lgfrbcsgo.github.io",
    "https://livepersoninc.github.io",
]


connection_manager = dependency.instance(IConnectionManager)


class Listener(object):
    def __init__(self):
        self._streams = []  # type: List[MessageStream]

    def on_connect(self, stream):
        # type: (MessageStream) -> ...
        self._streams.append(stream)

    def on_disconnect(self, stream):
        # type: (MessageStream) -> ...
        self._streams.remove(stream)

    @auto_run
    @async_task
    def on_arena_load(self):
        arena = BigWorld.player().arena

        if arena.bonusType != ARENA_BONUS_TYPE.REGULAR:
            return

        yield await_event(arena.onNewVehicleListReceived)

        tier = {
            vehicle_info["vehicleType"].level
            for vehicle_info in arena.vehicles.values()
        }

        data = {
            "server": connection_manager.serverUserNameShort,
            "tier": list(tier),
            "arenaType": arena.arenaType.id,
        }

        message = json.dumps(data)
        for stream in self._streams:
            run(stream.send_message(message))


def create_protocol(listener):
    # type: (Listener) -> ...

    @websocket_protocol(allowed_origins=ORIGIN_WHITELIST)
    @async_task
    def protocol(server, stream):
        # type: (Server, MessageStream) -> ...
        host, port = stream.peer_addr
        origin = stream.handshake_headers["origin"]
        LOG_NOTE(
            "{origin} ([{host}]:{port}) connected.".format(
                origin=origin, host=host, port=port
            )
        )

        listener.on_connect(stream)

        try:
            while True:
                # ignore all messages
                yield stream.receive_message()
        finally:
            listener.on_disconnect(stream)

            LOG_NOTE(
                "{origin} ([{host}]:{port}) disconnected.".format(
                    origin=origin, host=host, port=port
                )
            )

    return protocol


class MapRotationServer(object):
    def __init__(self):
        self._listener = Listener()
        protocol = create_protocol(self._listener)
        self._server = Server(protocol, PORT)

    @auto_run
    @async_task
    def serve(self):
        LOG_NOTE("Listening on port {}".format(PORT))
        g_playerEvents.onAvatarBecomePlayer += self._listener.on_arena_load

        try:
            with self._server as server:
                while not server.closed:
                    server.poll()
                    yield delay(0)
        except CallbackCancelled:
            pass
        finally:
            g_playerEvents.onAvatarBecomePlayer -= self._listener.on_arena_load
            LOG_NOTE("Stopped server")

    def close(self):
        self._server.close()


g_map_rotation_server = MapRotationServer()
