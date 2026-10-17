import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from controller_keyboard.app import ControllerApp
from controller_keyboard.engine import DESKTOP, KEYBOARD, SETTINGS
from controller_keyboard.xinput import ControllerState


from tests.test_engine import FakeSender


class UISmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_app_overlays_render_and_switch_modes(self):
        app = ControllerApp(self.qt_app)
        app.sender = app.engine.sender = app.hud.sender = FakeSender()
        try:
            self.assertEqual(app.engine.mode, KEYBOARD)
            self.assertTrue(app.hud.isVisible())

            # Simulate tilting stick up-left and pressing Y ('a')
            app.engine.update(ControllerState(frozenset({"Y"}), lx=-0.8, ly=0.8), 1.0, 0.008)
            self.assertEqual(app.sender.text, "a")
            app.hud.grab()  # Force full QPainter render of KeyboardHUD

            # Switch to Settings overlay (Game Bar mode)
            app.engine.set_mode(SETTINGS)
            self.assertTrue(app.settings.isVisible())
            app.settings.refresh_live()
            app.settings.grab()  # Force full QPainter render of SettingsOverlay & InputVisualizer

            # Switch to Desktop mode
            app.engine.set_mode(DESKTOP)
            self.assertFalse(app.settings.isVisible())
        finally:
            app._poll_timer.stop()
            app._housekeeping_timer.stop()
            app.tray.hide()
            app.hud.hide()
            app.settings.hide()
            app.toast.hide()


if __name__ == "__main__":
    unittest.main()
