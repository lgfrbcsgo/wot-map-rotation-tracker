from Event import Event
from constants import ARENA_GAMEPLAY_IDS
from helpers import dependency
from skeletons.account_helpers.settings_core import ISettingsCore


class ActiveModesRepository(object):
    settings_core = dependency.descriptor(ISettingsCore)

    def __init__(self):
        self.active_modes = None
        self.on_active_modes = Event()

    def start(self):
        self.settings_core.onSettingsChanged += self._on_settings_changed

    def stop(self):
        self.settings_core.onSettingsChanged -= self._on_settings_changed

    def _on_settings_changed(self, diff):
        gameplay_mask_update = diff.get("gameplayMask")
        if gameplay_mask_update is None:
            return

        self.active_modes = [
            mode
            for mode, gameplay_id in ARENA_GAMEPLAY_IDS.items()
            if (gameplay_mask_update & 1 << gameplay_id) != 0
        ]

        self.on_active_modes(self.active_modes)