from ArenaType import g_geometryCache
from Event import Event
from PlayerEvents import g_playerEvents
from helpers import dependency
from skeletons.gui.lobby_context import ILobbyContext


class BlockedMapsRepository(object):
    lobby_context = dependency.descriptor(ILobbyContext)

    def __init__(self):
        self.blocked_maps = None
        self.on_blocked_maps = Event()

    def start(self):
        g_playerEvents.onClientUpdated += self._on_client_update

    def stop(self):
        g_playerEvents.onClientUpdated -= self._on_client_update

    def _on_client_update(self, diff, _):
        blocked_maps_update = diff.get("preferredMaps", {}).get("blackList")
        if blocked_maps_update is None:
            return

        config = self.lobby_context.getServerSettings().getPreferredMapsConfig()
        cooldown = config["slotCooldown"]

        self.blocked_maps = [
            {"map": g_geometryCache[map_id].geometryName, "blocked_until": blocked_at + cooldown}
            for (map_id, blocked_at) in blocked_maps_update
            if map_id != 0
        ]

        self.on_blocked_maps(self.blocked_maps)