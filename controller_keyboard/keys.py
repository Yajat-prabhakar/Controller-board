"""Windows virtual-key codes and friendly names (pure Python, no ctypes)."""

VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_CAPITAL = 0x14
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_PRIOR = 0x21
VK_NEXT = 0x22
VK_END = 0x23
VK_HOME = 0x24
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_INSERT = 0x2D
VK_DELETE = 0x2E
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_APPS = 0x5D
VK_LSHIFT = 0xA0
VK_LCONTROL = 0xA2
VK_LMENU = 0xA4  # Left Alt
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT = 0xB0
VK_MEDIA_PREV = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3

# Keys that must be sent with KEYEVENTF_EXTENDEDKEY.
EXTENDED_KEYS = {
    VK_PRIOR, VK_NEXT, VK_END, VK_HOME, VK_LEFT, VK_UP, VK_RIGHT, VK_DOWN,
    VK_INSERT, VK_DELETE, VK_LWIN, VK_RWIN, VK_APPS, 0xA3, 0xA5, 0x6F, 0x90,
}

# Friendly names usable in config.json.
VK_NAMES = {
    "ENTER": VK_RETURN, "ESC": VK_ESCAPE, "BACKSPACE": VK_BACK, "TAB": VK_TAB,
    "SPACE": VK_SPACE, "LEFT": VK_LEFT, "RIGHT": VK_RIGHT, "UP": VK_UP,
    "DOWN": VK_DOWN, "HOME": VK_HOME, "END": VK_END, "PGUP": VK_PRIOR,
    "PGDN": VK_NEXT, "DELETE": VK_DELETE, "INSERT": VK_INSERT,
    "ALT": VK_LMENU, "CTRL": VK_LCONTROL, "SHIFT": VK_LSHIFT, "WIN": VK_LWIN,
    "CAPSLOCK": VK_CAPITAL, "APPS": VK_APPS,
    "VOLUP": VK_VOLUME_UP, "VOLDOWN": VK_VOLUME_DOWN, "MUTE": VK_VOLUME_MUTE,
    "PLAYPAUSE": VK_MEDIA_PLAY_PAUSE, "NEXTTRACK": VK_MEDIA_NEXT,
    "PREVTRACK": VK_MEDIA_PREV,
}
VK_NAMES.update({f"F{i}": 0x6F + i for i in range(1, 13)})


def vk_from_name(name):
    """Return the VK code for a friendly name, or None (e.g. for "NONE")."""
    if not name:
        return None
    return VK_NAMES.get(str(name).upper())
