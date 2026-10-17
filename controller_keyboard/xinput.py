"""Minimal XInput wrapper (ctypes) for Xbox controllers.

No third-party dependency: talks to xinput1_4.dll / xinput1_3.dll directly.
"""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field

ERROR_SUCCESS = 0

_BUTTON_BITS = {
    0x0001: "DPAD_UP",
    0x0002: "DPAD_DOWN",
    0x0004: "DPAD_LEFT",
    0x0008: "DPAD_RIGHT",
    0x0010: "MENU",   # "Start" on older pads, the ☰ button on Xbox One
    0x0020: "VIEW",   # "Back" on older pads, the ⧉ button on Xbox One
    0x0040: "L3",
    0x0080: "R3",
    0x0100: "LB",
    0x0200: "RB",
    0x1000: "A",
    0x2000: "B",
    0x4000: "X",
    0x8000: "Y",
}


class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [("dwPacketNumber", wintypes.DWORD), ("Gamepad", XINPUT_GAMEPAD)]


class XINPUT_VIBRATION(ctypes.Structure):
    _fields_ = [("wLeftMotorSpeed", wintypes.WORD), ("wRightMotorSpeed", wintypes.WORD)]


class XINPUT_BATTERY_INFORMATION(ctypes.Structure):
    _fields_ = [("BatteryType", ctypes.c_ubyte), ("BatteryLevel", ctypes.c_ubyte)]


@dataclass
class ControllerState:
    """Normalised snapshot: sticks in -1..1 (Y up is positive), triggers 0..1."""
    buttons: frozenset = field(default_factory=frozenset)
    lx: float = 0.0
    ly: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    lt: float = 0.0
    rt: float = 0.0


def _norm_axis(v):
    return max(-1.0, min(1.0, v / 32767.0))


def _load_dll():
    for name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
        try:
            return ctypes.WinDLL(name)
        except OSError:
            continue
    raise OSError("XInput DLL not found - is this Windows?")


class XInputReader:
    """Finds the first connected controller and reads its state."""

    RESCAN_INTERVAL = 1.5  # seconds; probing empty slots is slow, so throttle it

    def __init__(self):
        self._dll = _load_dll()
        self._dll.XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
        self._dll.XInputGetState.restype = wintypes.DWORD
        self._dll.XInputSetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_VIBRATION)]
        self._dll.XInputSetState.restype = wintypes.DWORD
        self._has_battery = hasattr(self._dll, "XInputGetBatteryInformation")
        if self._has_battery:
            self._dll.XInputGetBatteryInformation.argtypes = [
                wintypes.DWORD, ctypes.c_ubyte, ctypes.POINTER(XINPUT_BATTERY_INFORMATION)]
            self._dll.XInputGetBatteryInformation.restype = wintypes.DWORD
        self.slot = None
        self._next_scan = 0.0
        self._state = XINPUT_STATE()

    @property
    def connected(self):
        return self.slot is not None

    def _read_slot(self, slot):
        if self._dll.XInputGetState(slot, ctypes.byref(self._state)) != ERROR_SUCCESS:
            return None
        g = self._state.Gamepad
        buttons = frozenset(name for bit, name in _BUTTON_BITS.items() if g.wButtons & bit)
        return ControllerState(
            buttons=buttons,
            lx=_norm_axis(g.sThumbLX), ly=_norm_axis(g.sThumbLY),
            rx=_norm_axis(g.sThumbRX), ry=_norm_axis(g.sThumbRY),
            lt=g.bLeftTrigger / 255.0, rt=g.bRightTrigger / 255.0,
        )

    def poll(self, now):
        """Return a ControllerState, or None when no controller is connected."""
        if self.slot is not None:
            st = self._read_slot(self.slot)
            if st is not None:
                return st
            self.slot = None
            self._next_scan = 0.0
        if now < self._next_scan:
            return None
        self._next_scan = now + self.RESCAN_INTERVAL
        for slot in range(4):
            st = self._read_slot(slot)
            if st is not None:
                self.slot = slot
                return st
        return None

    def battery(self):
        """Return (type, level) - type: 'wired'|'battery'|'unknown', level 0..3 - or None."""
        if self.slot is None or not self._has_battery:
            return None
        info = XINPUT_BATTERY_INFORMATION()
        if self._dll.XInputGetBatteryInformation(self.slot, 0, ctypes.byref(info)) != ERROR_SUCCESS:
            return None
        kind = {0: None, 1: "wired", 2: "battery", 3: "battery"}.get(info.BatteryType, "unknown")
        if kind is None:
            return None
        return kind, int(info.BatteryLevel)

    def rumble(self, left=0.0, right=0.0):
        if self.slot is None:
            return
        vib = XINPUT_VIBRATION(int(max(0, min(1, left)) * 65535), int(max(0, min(1, right)) * 65535))
        self._dll.XInputSetState(self.slot, ctypes.byref(vib))
