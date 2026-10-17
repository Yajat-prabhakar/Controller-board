"""Main application controller: connects XInput polling, Engine, HUD, Settings, and Tray."""
import os
import time

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QGuiApplication, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from . import winutil
from .config import APP_DIR, USER_WORDS_PATH, Config
from .engine import DESKTOP, KEYBOARD, SETTINGS, Engine
from .predictor import Predictor
from .sendinput import SendInputSender
from .ui import theme
from .ui.hud import KeyboardHUD, Toast
from .ui.settings import SettingsOverlay
from .xinput import XInputReader

WORDS_PATH = os.path.join(os.path.dirname(__file__), "data", "words.txt")


def _make_tray_icon(active=True, connected=True):
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    col = theme.ACCENT if (active and connected) else (
        QColor("#F5C211") if not active else QColor("#888888"))
    p.setPen(QPen(col, 4))
    p.setBrush(QColor(28, 28, 30, 240))
    p.drawRoundedRect(QRectF(6, 12, 52, 40), 14, 14)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(col)
    p.drawEllipse(QPointF(22, 32), 5, 5)
    for dx, dy, c in ((0, -7, "Y"), (-7, 0, "X"), (7, 0, "B"), (0, 7, "A")):
        p.setBrush(theme.FACE_COLORS[c] if active else col)
        p.drawEllipse(QPointF(42 + dx, 32 + dy), 3.2, 3.2)
    p.end()
    return QIcon(pix)


class ControllerApp:
    """Runs the 120 Hz controller poll loop and coordinates all overlays."""

    def __init__(self, qt_app: QApplication):
        self.qt_app = qt_app
        self.qt_app.setQuitOnLastWindowClosed(False)
        os.makedirs(APP_DIR, exist_ok=True)

        self.config = Config.load()
        self.sender = SendInputSender()
        self.reader = XInputReader()
        self.predictor = Predictor(
            WORDS_PATH, USER_WORDS_PATH, learn=self.config["typing"]["learn"]
        )
        self.engine = Engine(self.sender, self.predictor, self.config)

        self.hud = KeyboardHUD(self.engine, self.config, self.sender)
        self.toast = Toast()
        self.settings = SettingsOverlay(self)
        self.engine.notify = self._on_engine_event

        self._was_connected = False
        self._last_fg = winutil.foreground_window()
        self._last_poll = time.monotonic()

        self._rumble_stop = QTimer()
        self._rumble_stop.setSingleShot(True)
        self._rumble_stop.timeout.connect(lambda: self.reader.rumble(0.0, 0.0))

        self._setup_tray()

        # 120 Hz controller polling timer (~8 ms)
        self._poll_timer = QTimer()
        self._poll_timer.setInterval(8)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start()

        # Periodic housekeeping (foreground window check + word dictionary save)
        self._housekeeping_timer = QTimer()
        self._housekeeping_timer.setInterval(1000)
        self._housekeeping_timer.timeout.connect(self._housekeeping)
        self._housekeeping_timer.start()

        # Show Keyboard HUD initially so the user immediately sees the app is live
        self.engine.set_mode(KEYBOARD)
        self.toast.show_text("Controller Keyboard active  (⧉ Keyboard · ☰ Settings)", 2600)

    # -------------------------------------------------------------- tray icon
    def _setup_tray(self):
        self.tray = QSystemTrayIcon(_make_tray_icon(True, False), self.qt_app)
        self.tray.setToolTip("Controller Keyboard")
        menu = QMenu()
        self.act_kb = QAction("Show / Hide Keyboard HUD (View ⧉)", menu)
        self.act_kb.triggered.connect(self.engine.toggle_keyboard)
        self.act_settings = QAction("Game Bar Settings (Menu ☰)", menu)
        self.act_settings.triggered.connect(self.engine.toggle_settings)
        self.act_pause = QAction("Pause Controller Mapping (View + Menu)", menu)
        self.act_pause.setCheckable(True)
        self.act_pause.triggered.connect(self.engine.set_paused)
        act_quit = QAction("Quit", menu)
        act_quit.triggered.connect(self.quit)

        menu.addAction(self.act_kb)
        menu.addAction(self.act_settings)
        menu.addSeparator()
        menu.addAction(self.act_pause)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.engine.toggle_settings()

    def _update_tray(self):
        self.act_pause.setChecked(not self.engine.active)
        self.tray.setIcon(_make_tray_icon(self.engine.active, self.reader.connected))
        status = "Active" if self.engine.active else "Paused"
        conn = "Controller connected" if self.reader.connected else "Waiting for controller"
        self.tray.setToolTip(f"Controller Keyboard — {status} ({conn})")

    # ----------------------------------------------------------- engine events
    def _on_engine_event(self, event, kw):
        if event == "mode":
            mode = kw["mode"]
            if mode == KEYBOARD:
                self.settings.hide()
                self.hud.show_hud()
            elif mode == DESKTOP:
                self.settings.hide()
                self.hud.hide_hud()
            elif mode == SETTINGS:
                self.hud.hide_hud()
                self.settings.open()
        elif event == "changed":
            self.hud.update()
            if self.settings.isVisible():
                self.settings.sync()
        elif event == "activity":
            self.hud.wake()
        elif event == "flash":
            self.hud.flash(kw["cell"], kw["face"])
            self._rumble(0.12, 25)
        elif event == "toast":
            self.toast.show_text(kw["text"])
        elif event == "rumble":
            self._rumble(kw.get("strength", 0.3), kw.get("ms", 60))
        elif event == "paused":
            if not self.engine.active:
                self.hud.hide_hud()
            elif self.engine.mode == KEYBOARD:
                self.hud.show_hud()
            if self.settings.isVisible():
                self.settings.sync()
            self._update_tray()

    def _rumble(self, strength, ms):
        if not self.config["general"]["haptics"]:
            return
        self.reader.rumble(strength * 0.5, strength)
        self._rumble_stop.start(int(ms))

    # -------------------------------------------------------------- poll loop
    def _poll(self):
        now = time.monotonic()
        dt = min(0.05, max(0.001, now - self._last_poll))
        self._last_poll = now
        try:
            st = self.reader.poll(now)
            if st is None:
                if self._was_connected:
                    self._was_connected = False
                    self.engine.on_disconnect()
                    self.toast.show_text("Controller disconnected")
                    self._update_tray()
                return
            if not self._was_connected:
                self._was_connected = True
                self.toast.show_text(f"Xbox Controller connected (Slot {self.reader.slot + 1})")
                self._rumble(0.35, 90)
                self._update_tray()
                if self.settings.isVisible():
                    self.settings.sync()
            self.engine.update(st, now, dt)
            if self.settings.isVisible():
                self.settings.refresh_live()
        except Exception:
            self.engine.release_all()
            raise

    def _housekeeping(self):
        fg = winutil.foreground_window()
        if fg and fg != self._last_fg:
            self._last_fg = fg
            self.engine.reset_context()
            if self.config["general"]["auto_pause_fullscreen"]:
                self.engine.set_auto_paused(winutil.is_fullscreen_app(fg))
            else:
                self.engine.set_auto_paused(False)
        self.predictor.save()

    # ---------------------------------------------------------------- helpers
    def battery_text(self):
        info = self.reader.battery()
        if not info:
            return ""
        kind, level = info
        if kind == "wired":
            return "🔌 Wired"
        bars = {0: "Empty", 1: "Low", 2: "Medium", 3: "Full"}.get(level, "")
        return f"🔋 {bars}" if bars else ""

    def config_changed(self):
        self.config.save()
        self.predictor.learn_enabled = self.config["typing"]["learn"]
        self.engine.refresh_suggestions()
        self.hud.apply_config()
        if not self.config["general"]["auto_pause_fullscreen"]:
            self.engine.set_auto_paused(False)
        if self.settings.isVisible():
            self.settings.sync()

    def quit(self):
        self._poll_timer.stop()
        self._housekeeping_timer.stop()
        self.reader.rumble(0.0, 0.0)
        self.engine.release_all()
        self.predictor.save()
        self.config.save()
        self.tray.hide()
        self.qt_app.quit()
