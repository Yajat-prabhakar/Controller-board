"""Entry point for Controller Keyboard."""
import ctypes
import logging
import os
import sys
import traceback

from PyQt6.QtWidgets import QApplication

from controller_keyboard.app import ControllerApp
from controller_keyboard.config import APP_DIR, LOG_PATH

_MUTEX_NAME = "Local\\ControllerKeyboardSingletonMutex"


def _acquire_single_instance():
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        return None
    return handle


def main():
    os.makedirs(APP_DIR, exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    mutex = _acquire_single_instance()
    if mutex is None:
        logging.info("Another instance is already running; exiting.")
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName("Controller Keyboard")
    ctrl_app = ControllerApp(app)

    def _excepthook(exc_type, exc_value, exc_tb):
        ctrl_app.engine.release_all()
        logging.error("Unhandled exception:\n%s", "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook
    try:
        return app.exec()
    finally:
        ctrl_app.engine.release_all()


if __name__ == "__main__":
    raise SystemExit(main())
