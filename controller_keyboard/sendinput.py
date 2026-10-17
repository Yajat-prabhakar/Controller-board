"""Inject keyboard and mouse input with the Win32 SendInput API (ctypes)."""
import ctypes
from ctypes import wintypes

from .keys import EXTENDED_KEYS, VK_CAPITAL, VK_LSHIFT, VK_LCONTROL, VK_LMENU, VK_RETURN

user32 = ctypes.WinDLL("user32", use_last_error=True)

ULONG_PTR = ctypes.c_size_t

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000

_MOUSE_FLAGS = {
    "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
}


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
user32.MapVirtualKeyW.restype = wintypes.UINT
user32.VkKeyScanW.argtypes = [wintypes.WCHAR]
user32.VkKeyScanW.restype = ctypes.c_short
user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetKeyState.restype = ctypes.c_short


def _key_input(vk=0, scan=0, flags=0):
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.ki = KEYBDINPUT(vk, scan, flags, 0, 0)
    return inp


def _vk_input(vk, up=False):
    flags = KEYEVENTF_KEYUP if up else 0
    if vk in EXTENDED_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY
    return _key_input(vk, user32.MapVirtualKeyW(vk, 0), flags)


def _mouse_input(flags, dx=0, dy=0, data=0):
    inp = INPUT(type=INPUT_MOUSE)
    inp.mi = MOUSEINPUT(dx, dy, data & 0xFFFFFFFF, flags, 0, 0)
    return inp


def _send(inputs):
    if not inputs:
        return
    arr = (INPUT * len(inputs))(*inputs)
    user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))


class SendInputSender:
    """Real output backend. Tracks held keys/buttons so they can never get stuck."""

    def __init__(self):
        self._held_keys = set()
        self._held_buttons = set()

    # -- keyboard -----------------------------------------------------------
    def key_down(self, vk):
        self._held_keys.add(vk)
        _send([_vk_input(vk)])

    def key_up(self, vk):
        self._held_keys.discard(vk)
        _send([_vk_input(vk, up=True)])

    def tap(self, vk):
        _send([_vk_input(vk), _vk_input(vk, up=True)])

    def type_text(self, text):
        """Type arbitrary text as Unicode (layout independent, ignores Caps Lock)."""
        inputs = []
        for ch in text:
            if ch == "\n":
                inputs += [_vk_input(VK_RETURN), _vk_input(VK_RETURN, up=True)]
                continue
            data = ch.encode("utf-16-le")
            for i in range(0, len(data), 2):
                unit = int.from_bytes(data[i:i + 2], "little")
                inputs.append(_key_input(0, unit, KEYEVENTF_UNICODE))
                inputs.append(_key_input(0, unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
        _send(inputs)

    def type_char_vk(self, ch):
        """Type a char as a real key press (needed so Alt/Win + key shortcuts work)."""
        res = user32.VkKeyScanW(ch)
        if res == -1:
            self.type_text(ch)
            return
        vk, shift_state = res & 0xFF, (res >> 8) & 0xFF
        mods = [m for bit, m in ((1, VK_LSHIFT), (2, VK_LCONTROL), (4, VK_LMENU))
                if shift_state & bit and m not in self._held_keys]
        inputs = [_vk_input(m) for m in mods]
        inputs += [_vk_input(vk), _vk_input(vk, up=True)]
        inputs += [_vk_input(m, up=True) for m in reversed(mods)]
        _send(inputs)

    def caps_lock_on(self):
        return bool(user32.GetKeyState(VK_CAPITAL) & 1)

    # -- mouse --------------------------------------------------------------
    def mouse_move(self, dx, dy):
        _send([_mouse_input(MOUSEEVENTF_MOVE, dx, dy)])

    def mouse_button(self, button, down):
        down_flag, up_flag = _MOUSE_FLAGS[button]
        if down:
            self._held_buttons.add(button)
        else:
            self._held_buttons.discard(button)
        _send([_mouse_input(down_flag if down else up_flag)])

    def wheel(self, delta, horizontal=False):
        _send([_mouse_input(MOUSEEVENTF_HWHEEL if horizontal else MOUSEEVENTF_WHEEL, data=int(delta))])

    # -- safety -------------------------------------------------------------
    def release_all(self):
        for vk in list(self._held_keys):
            self.key_up(vk)
        for b in list(self._held_buttons):
            self.mouse_button(b, False)
