from Event import Event
from account_helpers.settings_core.settings_constants import GAME
from constants import ARENA_GAMEPLAY_NAMES
from helpers import dependency
from mod_hooking import safe_callback
from skeletons.account_helpers.settings_core import ISettingsCache, ISettingsCore

CTF, DOMINATION, ASSAULT = ARENA_GAMEPLAY_NAMES[:3]


class ActiveModesRepository(object):
    settings_cache = dependency.descriptor(ISettingsCache)
    settings_core = dependency.descriptor(ISettingsCore)

    def __init__(self):
        self.active_modes = None
        self.on_active_modes = Event()

    def start(self):
        self.settings_cache.onSyncCompleted += self._on_sync_completed

    def stop(self):
        self.settings_cache.onSyncCompleted -= self._on_sync_completed

    @safe_callback
    def _on_sync_completed(self):
        modes = {
            CTF: self.settings_core.getSetting(GAME.GAMEPLAY_CTF),
            DOMINATION: self.settings_core.getSetting(GAME.GAMEPLAY_DOMINATION),
            ASSAULT: self.settings_core.getSetting(GAME.GAMEPLAY_ASSAULT),
        }

        active_modes = {mode for mode, active in modes.items() if active}

        if active_modes != self.active_modes:
            self.active_modes = active_modes
            self.on_active_modes(self.active_modes)
