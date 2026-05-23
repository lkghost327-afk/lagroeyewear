"""
LagroEyewear Settings Module
=============================

JSON-based settings persistence. Loads user preferences from a JSON file,
merges with sensible defaults, and provides get/set/reset operations
with automatic saving on every change.
"""

import json
import os
from typing import Any, Dict


# ─── Default configuration values ─────────────────────────────────────────
DEFAULTS: Dict[str, Any] = {
    "break_interval": 20,          # minutes between scheduled breaks
    "break_duration": 20,          # seconds per break
    "low_blink_threshold": 12,     # blinks/min below which is "low"
    "notifications_enabled": True, # desktop notifications on/off
    "start_minimized": False,      # start in system tray
    "start_with_system": False,    # launch at OS startup
    "ear_threshold": 0.25,         # EAR below this = eye closed
    "consecutive_frames": 2,       # consecutive low-EAR frames for a blink
}


class Settings:
    """Manages user-configurable application settings.

    Settings are persisted as a JSON file. On load, stored values are
    merged with DEFAULTS so that new keys added in future versions are
    automatically available with sensible fallbacks.

    Attributes:
        settings_path: Absolute path to the JSON settings file.
        data: In-memory settings dictionary.
    """

    def __init__(self, settings_path: str) -> None:
        """Initialise settings from a JSON file (created if missing).

        Args:
            settings_path: Path to the settings JSON file.
        """
        self.settings_path: str = settings_path
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load settings from disk and merge with defaults.

        If the file does not exist or is malformed, defaults are used
        and a fresh file is written.
        """
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    stored: Dict[str, Any] = json.load(f)
            except (json.JSONDecodeError, IOError):
                stored = {}
        else:
            stored = {}

        # Merge: defaults as base, stored values override
        self.data = {**DEFAULTS, **stored}

        # Persist the merged result (adds any new default keys to disk)
        self.save()

    def save(self) -> None:
        """Write the current settings to the JSON file."""
        # Ensure the parent directory exists
        directory = os.path.dirname(self.settings_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, sort_keys=True)
        except IOError as exc:
            print(f"[Settings] Warning: could not save settings — {exc}")

    def get(self, key: str) -> Any:
        """Retrieve a setting value.

        Args:
            key: The setting key to look up.

        Returns:
            The stored value, or the default if the key exists in DEFAULTS,
            or None if the key is completely unknown.
        """
        return self.data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        """Update a setting value and auto-save to disk.

        Args:
            key: The setting key to update.
            value: The new value.
        """
        self.data[key] = value
        self.save()

    def reset(self) -> None:
        """Reset all settings to their default values and save."""
        self.data = {**DEFAULTS}
        self.save()
