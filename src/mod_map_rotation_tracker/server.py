import json
import re
from typing import Optional

import BigWorld
from constants import ARENA_BONUS_TYPE
from debug_utils import LOG_NOTE
from helpers import dependency
from mod_async import CallbackCancelled, async_task, await_event, delay
from mod_async_server import Server
from mod_websocket_server import MessageStream, websocket_protocol
from PlayerEvents import g_playerEvents
from skeletons.connection_mgr import IConnectionManager

PORT = 15457

ORIGIN_WHITELIST = [
    re.compile("^https?://localhost(:[0-9]{1,5})?$"),
    "https://lgfrbcsgo.github.io",
]


connection_manager = dependency.instance(IConnectionManager)


class Listener(object):
    def __init__(self):
        self._stream = None  # type: Optional[MessageStream]

    @async_task
    def on_connect(self, stream):
        # type: (MessageStream) -> ...
        message = json.dumps({"type": "ProtocolVersion", "major": 1, "minor": 0})
        yield stream.send_message(message)

        previous, self._stream = self._stream, stream
        if previous:
            yield previous.close(code=4000, reason="ConnectionSuperseded")

    def on_disconnect(self, stream):
        # type: (MessageStream) -> ...
        if stream == self._stream:
            self._stream = None

    @async_task
    def on_arena_load(self):
        arena = BigWorld.player().arena

        if arena.bonusType != ARENA_BONUS_TYPE.REGULAR:
            return

        yield await_event(arena.onNewVehicleListReceived)

        tiers = {
            vehicle_info["vehicleType"].level
            for vehicle_info in arena.vehicles.values()
        }

        data = {
            "type": "PlayedMap",
            "server": connection_manager.serverUserNameShort,
            "map": arena.arenaType.geometryName,
            "mode": arena.arenaType.gameplayName,
            "bottom_tier": min(tiers),
            "top_tier": max(tiers),
        }

        if self._stream is not None:
            message = json.dumps(data)
            yield self._stream.send_message(message)


def create_protocol(listener):
    # type: (Listener) -> ...

    @websocket_protocol(allowed_origins=ORIGIN_WHITELIST)
    @async_task
    def protocol(server, stream):
        # type: (Server, MessageStream) -> ...
        try:
            yield listener.on_connect(stream)
            while True:
                # ignore all messages
                yield stream.receive_message()
        finally:
            listener.on_disconnect(stream)

    return protocol


class MapRotationServer(object):
    def __init__(self):
        self._listener = Listener()
        protocol = create_protocol(self._listener)
        self._server = Server(protocol, PORT)

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
