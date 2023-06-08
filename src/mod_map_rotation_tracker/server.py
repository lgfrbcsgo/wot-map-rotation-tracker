import json
import re
from typing import Optional

from debug_utils import LOG_NOTE
from mod_async import CallbackCancelled, async_task, delay
from mod_async_server import Server
from mod_map_rotation_tracker.active_modes_repository import ActiveModesRepository
from mod_map_rotation_tracker.blocked_maps_repository import BlockedMapsRepository
from mod_map_rotation_tracker.played_maps_listener import PlayedMapsListener
from mod_websocket_server import MessageStream, websocket_protocol

PORT = 15457

ORIGIN_WHITELIST = [
    re.compile("^https?://localhost(:[0-9]{1,5})?$"),
    "https://lgfrbcsgo.github.io",
]

class Protocol(object):
    def __init__(self):
        self._stream = None  # type: Optional[MessageStream]

        self._played_maps_listener = PlayedMapsListener()
        self._played_maps_listener.on_played_map += self._send_played_map

        self._blocked_maps_repository = BlockedMapsRepository()
        self._blocked_maps_repository.on_blocked_maps += self._send_blocked_maps

        self._active_modes_repository = ActiveModesRepository()
        self._active_modes_repository.on_active_modes += self._send_active_modes

    def start(self):
        self._played_maps_listener.start()
        self._blocked_maps_repository.start()
        self._active_modes_repository.start()

    def stop(self):
        self._played_maps_listener.stop()
        self._blocked_maps_repository.stop()
        self._active_modes_repository.stop()

    @async_task
    def on_connect(self, stream):
        try:
            previous, self._stream = self._stream, stream
            if previous:
                yield previous.close(code=4000, reason="ConnectionSuperseded")

            if self._blocked_maps_repository.blocked_maps:
                yield self._send_blocked_maps(self._blocked_maps_repository.blocked_maps)

            if self._active_modes_repository.active_modes:
                yield self._send_active_modes(self._active_modes_repository.active_modes)

            while True:
                # ignore all messages
                yield stream.receive_message()
        finally:
            if stream == self._stream:
                self._stream = None

    @async_task
    def _send_played_map(self, played_map):
        message = {"type": "PlayedMap"}
        message.update(played_map)
        yield self._send_message(message)

    @async_task
    def _send_blocked_maps(self, blocked_maps):
        message = {"type": "BlockedMaps", "maps": blocked_maps}
        yield self._send_message(message)

    @async_task
    def _send_active_modes(self, active_modes):
        message = {"type": "ActiveModes", "modes": active_modes}
        yield self._send_message(message)

    @async_task
    def _send_message(self, message):
        if self._stream:
            yield self._stream.send_message(json.dumps(message))


class MapRotationServer(object):
    def __init__(self):
        self._protocol = Protocol()

        @websocket_protocol(allowed_origins=ORIGIN_WHITELIST)
        @async_task
        def protocol(_server, stream):
            yield self._protocol.on_connect(stream)

        self._server = Server(protocol, PORT)

    @async_task
    def serve(self):
        LOG_NOTE("Listening on port {}".format(PORT))
        self._protocol.start()

        try:
            with self._server as server:
                while not server.closed:
                    server.poll()
                    yield delay(0)
        except CallbackCancelled:
            pass
        finally:
            self._protocol.stop()
            LOG_NOTE("Stopped server")

    def close(self):
        self._server.close()


g_map_rotation_server = MapRotationServer()
