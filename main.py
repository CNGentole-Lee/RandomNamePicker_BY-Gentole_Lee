"""Random Name Picker — Entry point.

A PyQt5-based random name picker for teachers.
Features:
  - Floating ball on the right side of the screen (doesn't block PPT)
  - Per-name 10-min cooldown (other names can still be drawn)
  - Rolling animation before revealing the drawn name
  - Centered result popup with X button, auto-closes in 5s
"""

import sys
import os

from PyQt5.QtCore import Qt, QSettings, QTimer
from PyQt5.QtWidgets import QApplication

from namepicker.name_engine import NameEngine
from namepicker.floating_ball import FloatingBall
from namepicker.draw_popup import DrawResultPopup
from namepicker.main_window import MainWindow
from namepicker.single_instance import SingleInstance


def _get_bundled_path(relative_path: str) -> str:
    """Get the absolute path to a resource, works for both source and PyInstaller bundle."""
    if getattr(sys, 'frozen', False):
        # Running as bundled EXE
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("RandomNamePicker")
    app.setApplicationDisplayName("随机点名器")
    app.setOrganizationName("NamePicker")

    # --- Single-instance guard ---
    single = SingleInstance()
    if not single.try_acquire():
        # Another instance is already running — wake it and exit
        single.notify_existing()
        sys.exit(0)

    app.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            border: 1px solid #ccc;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
        }
        QPushButton {
            padding: 6px 16px;
            border: 1px solid #aaa;
            border-radius: 4px;
            background: #f5f5f5;
        }
        QPushButton:hover {
            background: #e0e0e0;
        }
        QPushButton:pressed {
            background: #d0d0d0;
        }
        QListWidget, QTableWidget {
            border: 1px solid #ccc;
            border-radius: 4px;
        }
    """)

    # --- Core ---
    engine = NameEngine()

    # --- UI ---
    ball = FloatingBall()
    popup = DrawResultPopup()
    # For PyInstaller bundle: sys.executable is the EXE path
    # For source: use __file__
    if getattr(sys, 'frozen', False):
        app_path = sys.executable
    else:
        app_path = os.path.abspath(__file__)
    main_win = MainWindow(engine, app_path=app_path)
    main_win.set_ball(ball)

    # --- Signal wiring ---

    # Single-instance: wake-up → show main window
    single.wake_up_requested.connect(main_win.showNormal)
    single.wake_up_requested.connect(main_win.activateWindow)

    # Ball double-click → draw
    ball.ball_clicked.connect(engine.draw_name)

    # Ball right-click → open management panel
    ball.open_panel_requested.connect(main_win.showNormal)
    ball.open_panel_requested.connect(main_win.activateWindow)

    # Rolling start → show popup with rolling animation
    def on_rolling_start(name: str):
        popup.set_name_pool(engine.get_names())
        popup.show_result(name)

    engine.rolling_start.connect(on_rolling_start)

    # Name drawn → ball flash + main window update
    def on_name_drawn(name: str):
        ball.flash_drawing()
        main_win.on_name_drawn(name)

    engine.name_drawn.connect(on_name_drawn)

    # Per-name cooldowns updated
    engine.cooldowns_updated.connect(main_win.on_cooldowns_updated)

    # Names loaded → main window + update popup pool
    def on_names_loaded(count: int):
        main_win.on_names_loaded(count)
        popup.set_name_pool(engine.get_names())

    engine.names_loaded.connect(on_names_loaded)

    # Errors
    engine.error_occurred.connect(main_win.on_error)

    # Pool refilled
    engine.pool_refilled.connect(main_win.on_pool_refilled)

    # History cleared
    engine.history_cleared.connect(main_win.on_history_cleared)

    # --- Show ---
    ball.show()
    main_win.show()

    # --- Auto-load last file (or default to 1-99 on first run) ---
    settings = QSettings("NamePicker", "Config")
    last_file = settings.value("last_file", "")
    if last_file and os.path.isfile(last_file):
        engine.load_names_from_file(last_file)
        popup.set_name_pool(engine.get_names())
    elif not engine.get_names():
        # First run with no saved file: default to numbers 1-99
        engine.generate_number_list(1, 99)
        popup.set_name_pool(engine.get_names())

    # --- Run ---
    exit_code = app.exec_()
    main_win.save_settings()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
