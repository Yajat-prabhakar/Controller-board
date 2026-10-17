"""Settings persisted to %APPDATA%\\ControllerKeyboard\\config.json."""
import copy
import json
import os

APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ControllerKeyboard")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
USER_WORDS_PATH = os.path.join(APP_DIR, "user_words.json")
LOG_PATH = os.path.join(APP_DIR, "app.log")

DEFAULTS = {
    "mouse": {
        "speed": 1400,          # pixels / second at full tilt
        "curve": 2.0,           # >1 = finer control near the centre
        "deadzone": 0.15,
        "scroll_speed": 14,     # wheel notches / second at full tilt
        "invert_scroll": False,
    },
    "hud": {
        "position": "bottom-center",
        "scale": 0.85,
        "active_opacity": 0.96,
        "idle_opacity": 0.25,
        "idle_seconds": 4.0,
        "stick_threshold": 0.5,
    },
    "typing": {
        "predictions": True,
        "learn": True,
        "auto_capitalize": True,
        "repeat_delay": 0.40,
        "repeat_rate": 22,
    },
    "general": {
        "trigger_threshold": 0.35,
        "haptics": True,
        "auto_pause_fullscreen": False,
    },
    # What buttons do while the keyboard HUD is hidden ("desktop mode").
    # Values are key names from keys.VK_NAMES, or "NONE".
    "desktop_buttons": {
        "A": "ENTER", "B": "ESC", "X": "BACKSPACE", "Y": "SPACE",
        "DPAD_UP": "UP", "DPAD_DOWN": "DOWN", "DPAD_LEFT": "LEFT", "DPAD_RIGHT": "RIGHT",
    },
}


def _merge(base, override):
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(out.get(k), dict) and isinstance(v, dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    def __init__(self, data=None, path=CONFIG_PATH):
        self.path = path
        self.data = _merge(DEFAULTS, data)

    @classmethod
    def load(cls, path=CONFIG_PATH):
        data = None
        if path and os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                data = None
        return cls(data, path)

    def save(self):
        if not self.path:
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
        os.replace(tmp, self.path)

    def get(self, section, key):
        return self.data[section][key]

    def set(self, section, key, value):
        self.data[section][key] = value

    def __getitem__(self, section):
        return self.data[section]
