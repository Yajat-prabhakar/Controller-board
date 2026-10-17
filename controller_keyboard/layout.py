"""The 3x3 clustered keyboard layout.

Left stick picks one of 9 cells (centre = stick released), and Y/X/B/A pick the
key inside that cell (Y = top, X = left, B = right, A = bottom).
"""
import math

ENTER, BKSP, SPACE, LAYER = "{ENTER}", "{BKSP}", "{SPACE}", "{LAYER}"
SPECIAL_KEYS = {ENTER, BKSP, SPACE, LAYER}

# Row-major order, as drawn on screen.
CELLS = ("UL", "U", "UR", "L", "C", "R", "DL", "D", "DR")
FACES = ("Y", "X", "B", "A")

CELL_ARROWS = {"UL": "↖", "U": "↑", "UR": "↗", "L": "←", "C": "●",
               "R": "→", "DL": "↙", "D": "↓", "DR": "↘"}

# Centre cell (stick released) is identical on every layer.
CENTER = {"Y": ENTER, "X": BKSP, "B": SPACE, "A": LAYER}

LETTERS = {
    "UL": {"Y": "a", "X": "b", "B": "c", "A": "d"},
    "U":  {"Y": "e", "X": "f", "B": "g", "A": "h"},
    "UR": {"Y": "i", "X": "j", "B": "k", "A": "l"},
    "L":  {"Y": "m", "X": "n", "B": "o", "A": "p"},
    "C":  CENTER,
    "R":  {"Y": "q", "X": "r", "B": "s", "A": "t"},
    "DL": {"Y": "u", "X": "v", "B": "w", "A": "x"},
    "D":  {"Y": "y", "X": "z", "B": ".", "A": ","},
    "DR": {"Y": "?", "X": "!", "B": "'", "A": "-"},
}

SYMBOLS = {
    "UL": {"Y": "1", "X": "2", "B": "3", "A": "@"},
    "U":  {"Y": "4", "X": "5", "B": "6", "A": "#"},
    "UR": {"Y": "7", "X": "8", "B": "9", "A": "0"},
    "L":  {"Y": "$", "X": "%", "B": "&", "A": "*"},
    "C":  CENTER,
    "R":  {"Y": "(", "X": ")", "B": "[", "A": "]"},
    "DL": {"Y": "+", "X": "=", "B": "_", "A": "/"},
    "D":  {"Y": ":", "X": ";", "B": '"', "A": "\\"},
    "DR": {"Y": "<", "X": ">", "B": "{", "A": "}"},
}

LAYERS = {"letters": LETTERS, "symbols": SYMBOLS}

_SECTORS = ("R", "UR", "U", "UL", "L", "DL", "D", "DR")
_SECTOR_CENTER = {name: i * 45.0 for i, name in enumerate(_SECTORS)}


def key_at(layer, cell, face):
    return LAYERS[layer][cell][face]


def stick_to_cell(x, y, threshold=0.5, previous="C", hysteresis_deg=8.0):
    """Map a stick position (Y up = positive) to a cell name.

    Uses hysteresis on both the radius and the angle so the highlighted cell
    doesn't flicker when the stick sits near a boundary.
    """
    mag = math.hypot(x, y)
    release = threshold * 0.8
    if mag < (release if previous != "C" else threshold):
        return "C"
    angle = math.degrees(math.atan2(y, x)) % 360.0
    if previous in _SECTOR_CENTER:
        diff = abs((angle - _SECTOR_CENTER[previous] + 180.0) % 360.0 - 180.0)
        if diff <= 22.5 + hysteresis_deg:
            return previous
    return _SECTORS[int(((angle + 22.5) % 360.0) // 45.0)]
