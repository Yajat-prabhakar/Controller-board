"""Xbox Game Bar style settings overlay (opened with the Menu ☰ button)."""
import os
import time

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QPushButton, QSlider, QVBoxLayout, QWidget)

from .. import winutil
from ..config import APP_DIR
from ..engine import KEYBOARD
from . import theme

CARD_WIDTH = 330


class Card(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setObjectName("card")
        self.setFixedWidth(CARD_WIDTH)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(16, 14, 16, 16)
        self.lay.setSpacing(10)
        t = QLabel(title)
        t.setObjectName("cardTitle")
        self.lay.addWidget(t)

    def mousePressEvent(self, event):
        event.accept()  # clicks inside a card must not close the overlay


class InputVisualizer(QWidget):
    """Live view of sticks, triggers and buttons."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(CARD_WIDTH - 32, 150)
        self.state = None

    def set_state(self, st):
        self.state = st
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        st = self.state
        btn = st.buttons if st else frozenset()
        w = self.width()
        dim, lit = QColor(255, 255, 255, 30), theme.ACCENT

        def bar(x, val, label):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(dim)
            p.drawRoundedRect(QRectF(x, 6, 80, 8), 4, 4)
            p.setBrush(lit)
            p.drawRoundedRect(QRectF(x, 6, 80 * val, 8), 4, 4)
            p.setPen(theme.TEXT_DIM)
            p.drawText(QRectF(x, 14, 80, 16), Qt.AlignmentFlag.AlignCenter, label)

        def pill(x, name):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(lit if name in btn else dim)
            p.drawRoundedRect(QRectF(x, 32, 80, 14), 7, 7)

        def stick(cx, sx, sy, pressed):
            p.setPen(QPen(lit if pressed else QColor(255, 255, 255, 60), 2))
            p.setBrush(QColor(255, 255, 255, 10))
            p.drawEllipse(QPointF(cx, 100), 32, 32)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(theme.TEXT)
            p.drawEllipse(QPointF(cx + sx * 26, 100 - sy * 26), 7, 7)

        def dot(x, y, name, color, r=8):
            p.setPen(QPen(color, 1.5))
            p.setBrush(color if name in btn else QColor(255, 255, 255, 8))
            p.drawEllipse(QPointF(x, y), r, r)

        bar(10, st.lt if st else 0, "LT")
        bar(w - 90, st.rt if st else 0, "RT")
        pill(10, "LB")
        pill(w - 90, "RB")
        stick(50, st.lx if st else 0, st.ly if st else 0, "L3" in btn)
        stick(w - 50, st.rx if st else 0, st.ry if st else 0, "R3" in btn)
        cx = w / 2
        dot(cx, 62, "Y", theme.FACE_COLORS["Y"])
        dot(cx - 18, 80, "X", theme.FACE_COLORS["X"])
        dot(cx + 18, 80, "B", theme.FACE_COLORS["B"])
        dot(cx, 98, "A", theme.FACE_COLORS["A"])
        dot(cx - 22, 34, "VIEW", theme.TEXT_DIM, 5)
        dot(cx + 22, 34, "MENU", theme.TEXT_DIM, 5)
        for name, (dx, dy) in {"DPAD_UP": (0, -10), "DPAD_DOWN": (0, 10),
                               "DPAD_LEFT": (-10, 0), "DPAD_RIGHT": (10, 0)}.items():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(lit if name in btn else dim)
            p.drawRoundedRect(QRectF(cx + dx - 5, 130 + dy - 5, 10, 10), 2, 2)
        p.end()


class SettingsOverlay(QWidget):
    def __init__(self, app):
        super().__init__(None, Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.app = app
        self.cfg = app.config
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(theme.SETTINGS_QSS)
        self._build()
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

    # ------------------------------------------------------------------ build
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 28, 40, 28)
        root.setSpacing(18)
        root.addWidget(self._top_bar(), 0, Qt.AlignmentFlag.AlignHCenter)

        cards = [self._controller_card(), self._mouse_card(), self._hud_card(),
                 self._typing_card(), self._general_card(), self._map_card()]
        grid_host = QWidget()
        grid_host.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(16)
        avail = QGuiApplication.primaryScreen().availableGeometry().width()
        cols = 3 if avail >= 3 * CARD_WIDTH + 2 * 16 + 80 else 2
        for i, c in enumerate(cards):
            grid.addWidget(c, i // cols, i % cols, Qt.AlignmentFlag.AlignTop)
        root.addWidget(grid_host, 0, Qt.AlignmentFlag.AlignHCenter)
        root.addStretch(1)

    def _top_bar(self):
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.mousePressEvent = lambda e: e.accept()
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 10, 10, 10)
        h.setSpacing(12)
        title = QLabel("🎮  Controller Keyboard")
        title.setObjectName("title")
        self.status_lbl = QLabel()
        self.battery_lbl = QLabel()
        self.battery_lbl.setObjectName("dim")
        self.clock_lbl = QLabel()
        self.clock_lbl.setObjectName("clock")
        self.kb_btn = QPushButton("⌨  Keyboard")
        self.kb_btn.clicked.connect(lambda: self.app.engine.toggle_keyboard())
        self.pause_btn = QPushButton("⏸  Pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.clicked.connect(lambda c: self.app.engine.set_paused(c))
        close = QPushButton("✕")
        close.setObjectName("close")
        close.clicked.connect(self.request_close)
        for w in (title, self.status_lbl):
            h.addWidget(w)
        h.addSpacing(40)
        for w in (self.battery_lbl, self.clock_lbl, self.kb_btn, self.pause_btn, close):
            h.addWidget(w)
        return bar

    # -- helpers ---------------------------------------------------------------
    def _changed(self, section, key, value):
        self.cfg.set(section, key, value)
        self.app.config_changed()

    def _slider(self, card, label, lo, hi, value, fmt, on_change):
        host = QWidget()
        g = QGridLayout(host)
        g.setContentsMargins(0, 0, 0, 0)
        g.setVerticalSpacing(4)
        val = QLabel(fmt(value))
        val.setObjectName("dim")
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(int(value))

        def changed(v):
            val.setText(fmt(v))
            on_change(v)
        s.valueChanged.connect(changed)
        g.addWidget(QLabel(label), 0, 0)
        g.addWidget(val, 0, 1, Qt.AlignmentFlag.AlignRight)
        g.addWidget(s, 1, 0, 1, 2)
        card.lay.addWidget(host)
        return s

    def _check(self, card, label, checked, on_toggle):
        cb = QCheckBox(label)
        cb.setChecked(bool(checked))
        cb.toggled.connect(on_toggle)
        card.lay.addWidget(cb)
        return cb

    # -- cards -------------------------------------------------------------------
    def _controller_card(self):
        c = Card("🎮  Controller")
        self.conn_lbl = QLabel()
        self.conn_lbl.setObjectName("dim")
        c.lay.addWidget(self.conn_lbl)
        self.visualizer = InputVisualizer()
        c.lay.addWidget(self.visualizer, 0, Qt.AlignmentFlag.AlignHCenter)
        hint = QLabel("View ⧉ = keyboard   Menu ☰ = settings\nView + Menu = pause / resume (e.g. for games)")
        hint.setObjectName("dim")
        c.lay.addWidget(hint)
        return c

    def _mouse_card(self):
        c = Card("🖱  Mouse (right stick)")
        m = self.cfg["mouse"]
        self._slider(c, "Pointer speed", 200, 4000, m["speed"], lambda v: f"{v} px/s",
                     lambda v: self._changed("mouse", "speed", v))
        self._slider(c, "Precision curve", 10, 40, m["curve"] * 10, lambda v: f"{v / 10:.1f}",
                     lambda v: self._changed("mouse", "curve", v / 10))
        self._slider(c, "Stick deadzone", 5, 40, m["deadzone"] * 100, lambda v: f"{v}%",
                     lambda v: self._changed("mouse", "deadzone", v / 100))
        self._slider(c, "Scroll speed (left stick)", 2, 40, m["scroll_speed"], lambda v: f"{v}",
                     lambda v: self._changed("mouse", "scroll_speed", v))
        self._check(c, "Invert scroll direction", m["invert_scroll"],
                    lambda v: self._changed("mouse", "invert_scroll", v))
        return c

    def _hud_card(self):
        c = Card("⌨  Keyboard overlay")
        hud = self.cfg["hud"]
        c.lay.addWidget(QLabel("Position"))
        row = QHBoxLayout()
        group = QButtonGroup(c)
        for key, text in (("bottom-left", "↙"), ("bottom-center", "↓"),
                          ("bottom-right", "↘"), ("top-center", "↑")):
            b = QPushButton(text)
            b.setCheckable(True)
            b.setChecked(hud["position"] == key)
            b.clicked.connect(lambda _=False, k=key: self._changed("hud", "position", k))
            group.addButton(b)
            row.addWidget(b)
        c.lay.addLayout(row)
        self._slider(c, "Size", 60, 140, hud["scale"] * 100, lambda v: f"{v}%",
                     lambda v: self._changed("hud", "scale", v / 100))
        self._slider(c, "Opacity when idle", 0, 100, hud["idle_opacity"] * 100, lambda v: f"{v}%",
                     lambda v: self._changed("hud", "idle_opacity", v / 100))
        self._slider(c, "Fade after", 1, 20, hud["idle_seconds"], lambda v: f"{v} s",
                     lambda v: self._changed("hud", "idle_seconds", float(v)))
        self._slider(c, "Stick push to select a cell", 30, 80, hud["stick_threshold"] * 100,
                     lambda v: f"{v}%", lambda v: self._changed("hud", "stick_threshold", v / 100))
        return c

    def _typing_card(self):
        c = Card("✨  Typing & prediction")
        t = self.cfg["typing"]
        self._check(c, "Word predictions on the D-Pad", t["predictions"],
                    lambda v: self._changed("typing", "predictions", v))
        self._check(c, "Learn from what I type", t["learn"],
                    lambda v: self._changed("typing", "learn", v))
        self._check(c, "Auto-capitalise new sentences", t["auto_capitalize"],
                    lambda v: self._changed("typing", "auto_capitalize", v))
        self._slider(c, "Key repeat delay", 15, 100, t["repeat_delay"] * 100,
                     lambda v: f"{v * 10} ms", lambda v: self._changed("typing", "repeat_delay", v / 100))
        row = QHBoxLayout()
        self.learned_lbl = QLabel()
        self.learned_lbl.setObjectName("dim")
        clear = QPushButton("Clear learned words")
        clear.setObjectName("danger")
        clear.clicked.connect(self._clear_learned)
        row.addWidget(self.learned_lbl)
        row.addStretch(1)
        row.addWidget(clear)
        c.lay.addLayout(row)
        return c

    def _general_card(self):
        c = Card("⚙  General")
        g = self.cfg["general"]
        self._check(c, "Auto-pause when a fullscreen game is focused", g["auto_pause_fullscreen"],
                    lambda v: self._changed("general", "auto_pause_fullscreen", v))
        self._check(c, "Vibration feedback", g["haptics"],
                    lambda v: self._changed("general", "haptics", v))
        self._check(c, "Start with Windows", winutil.is_startup_enabled(), winutil.set_startup)
        self._slider(c, "Trigger press point", 10, 80, g["trigger_threshold"] * 100, lambda v: f"{v}%",
                     lambda v: self._changed("general", "trigger_threshold", v / 100))
        row = QHBoxLayout()
        folder = QPushButton("Open config folder")
        folder.clicked.connect(lambda: os.startfile(APP_DIR))
        quit_btn = QPushButton("Quit app")
        quit_btn.setObjectName("danger")
        quit_btn.clicked.connect(self.app.quit)
        row.addWidget(folder)
        row.addStretch(1)
        row.addWidget(quit_btn)
        c.lay.addLayout(row)
        return c

    def _map_card(self):
        c = Card("🗺  Button map")
        rows = [
            ("LT (hold)", "Alt"), ("RT", "Tab   (LT + RT = Alt+Tab)"),
            ("LB", "Caps Lock"), ("RB (hold)", "Windows key"),
            ("Right stick", "Mouse pointer"), ("R3 / L3", "Left / right click"),
            ("Left stick", "Keyboard: pick cell · Desktop: scroll"),
            ("Y X B A", "Keyboard: type · Desktop: Space Bksp Esc Enter"),
            ("D-Pad", "Keyboard: predictions · Desktop: arrows"),
            ("Stick centre", "Y ↵ Enter · X ⌫ · B ␣ Space · A 123"),
        ]
        html = "<table cellspacing='0' cellpadding='3'>" + "".join(
            f"<tr><td style='color:#16C60C; font-weight:600; padding-right:10px'>{a}</td>"
            f"<td>{b}</td></tr>" for a, b in rows) + "</table>"
        lbl = QLabel(html)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setWordWrap(True)
        c.lay.addWidget(lbl)
        return c

    # ------------------------------------------------------------- behaviour
    def _clear_learned(self):
        self.app.predictor.clear_learned()
        self.sync()

    def _update_clock(self):
        if self.isVisible():
            self.clock_lbl.setText(time.strftime("%I:%M %p").lstrip("0"))

    def open(self):
        self.setGeometry(QGuiApplication.primaryScreen().geometry())
        self.sync()
        self._update_clock()
        self.show()
        self.raise_()
        self.activateWindow()

    def sync(self):
        e = self.app.engine
        active = e.active
        self.status_lbl.setText("●  Active" if active else "●  Paused")
        self.status_lbl.setStyleSheet(f"color: {'#16C60C' if active else '#F5C211'}; font-weight: 600;")
        self.pause_btn.setChecked(e.paused)
        self.battery_lbl.setText(self.app.battery_text())
        self.conn_lbl.setText("Connected" if self.app.reader.connected else
                              "No controller found - plug in or pair via Bluetooth")
        self.learned_lbl.setText(f"{self.app.predictor.learned_count} learned words")
        self.kb_btn.setText("⌨  Hide keyboard" if e.mode == KEYBOARD else "⌨  Keyboard")

    def refresh_live(self):
        self.visualizer.set_state(self.app.engine.last_state)

    def request_close(self):
        self.app.engine.close_settings()

    # -- events -------------------------------------------------------------------
    def paintEvent(self, _event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 110))
        p.end()

    def mousePressEvent(self, event):
        self.request_close()  # click on the dimmed background closes, like Game Bar

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.request_close()
        else:
            super().keyPressEvent(event)
