"""Shared colours and stylesheet (Xbox Game Bar inspired dark theme)."""
from PyQt6.QtGui import QColor

ACCENT = QColor("#16C60C")          # Xbox-ish green
ACCENT_DARK = QColor("#107C10")
TEXT = QColor("#F3F3F3")
TEXT_DIM = QColor(255, 255, 255, 140)
PANEL_BG = QColor(28, 28, 30, 238)
CELL_BG = QColor(255, 255, 255, 12)
CELL_BORDER = QColor(255, 255, 255, 22)

FACE_COLORS = {
    "A": QColor("#5DC21E"),
    "B": QColor("#E8453C"),
    "X": QColor("#2D8CEB"),
    "Y": QColor("#F5C211"),
}

FONT_FAMILY = "Segoe UI"

SETTINGS_QSS = """
* { font-family: 'Segoe UI'; color: #F3F3F3; font-size: 13px; }
QFrame#card, QFrame#topbar {
    background: rgba(32, 32, 34, 242);
    border: 1px solid rgba(255, 255, 255, 28);
    border-radius: 10px;
}
QLabel#cardTitle { font-size: 14px; font-weight: 600; }
QLabel#dim { color: rgba(255, 255, 255, 150); }
QLabel#title { font-size: 15px; font-weight: 600; }
QLabel#clock { font-size: 16px; font-weight: 600; }
QPushButton {
    background: rgba(255, 255, 255, 18); border: 1px solid rgba(255, 255, 255, 30);
    border-radius: 6px; padding: 6px 12px;
}
QPushButton:hover { background: rgba(255, 255, 255, 34); }
QPushButton:pressed { background: rgba(255, 255, 255, 50); }
QPushButton:checked { background: #107C10; border-color: #16C60C; }
QPushButton#danger:hover { background: #C42B1C; }
QPushButton#close { padding: 4px 10px; font-size: 14px; }
QSlider::groove:horizontal { height: 4px; background: rgba(255,255,255,40); border-radius: 2px; }
QSlider::sub-page:horizontal { background: #16C60C; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #F3F3F3; width: 14px; height: 14px; margin: -6px 0; border-radius: 7px;
}
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid rgba(255,255,255,90); background: rgba(255,255,255,10);
}
QCheckBox::indicator:checked { background: #16C60C; border-color: #16C60C; }
QComboBox {
    background: rgba(255,255,255,18); border: 1px solid rgba(255,255,255,30);
    border-radius: 6px; padding: 4px 8px;
}
QComboBox QAbstractItemView {
    background: #2B2B2D; selection-background-color: #107C10; border: 1px solid #444;
}
"""
