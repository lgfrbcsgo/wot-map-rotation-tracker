import BigWorld

from Event import Event
from PlayerEvents import g_playerEvents
from constants import ARENA_BONUS_TYPE
from helpers import dependency
from mod_async import async_task, await_event
from mod_map_rotation_tracker.util import safe_callback
from skeletons.connection_mgr import IConnectionManager


class PlayedMapsListener(object):
    connection_manager = dependency.descriptor(IConnectionManager)

    def __init__(self):
        self.on_played_map = Event()

    def start(self):
        g_playerEvents.onAvatarBecomePlayer += self._on_avatar_become_player

    def stop(self):
        g_playerEvents.onAvatarBecomePlayer -= self._on_avatar_become_player

    @safe_callback
    @async_task
    def _on_avatar_become_player(self):
        arena = BigWorld.player().arena

        if arena.bonusType != ARENA_BONUS_TYPE.REGULAR:
            return

        yield await_event(arena.onNewVehicleListReceived)

        tiers = {
            vehicle_info["vehicleType"].level
            for vehicle_info in arena.vehicles.values()
        }

        self.on_played_map({
            "server": self.connection_manager.serverUserNameShort,
            "map": arena.arenaType.geometryName,
            "mode": arena.arenaType.gameplayName,
            "bottom_tier": min(tiers),
            "top_tier": max(tiers),
        })