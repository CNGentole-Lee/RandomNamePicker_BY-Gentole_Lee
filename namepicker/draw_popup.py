"""DrawResultPopup — Centered popup with rolling animation, X button, auto-close."""

import random
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF,
)
from PyQt5.QtGui import (
    QPainter, QBrush, QColor, QFont, QPen, QPainterPath,
)
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout,
    QApplication,
)


class DrawResultPopup(QWidget):
    """A centered frameless popup with rolling name animation.

    Shows a rapid cycling of names for ~2s, then settles on the final result.
    Has an X button and auto-closes after 5 seconds.
    """

    POPUP_WIDTH = 380
    POPUP_HEIGHT = 200

    ROLL_DURATION_MS = 1800       # how long names cycle
    ROLL_INTERVAL_MS = 60         # how fast names change during cycling
    AUTO_CLOSE_MS = 5000          # auto-close after reveal

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_names: list[str] = []
        self._result_name = ""
        self._roll_timer: QTimer | None = None
        self._roll_count = 0
        self._auto_close_timer: QTimer | None = None

        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self.setFixedSize(self.POPUP_WIDTH, self.POPUP_HEIGHT)

        # --- Top bar with X button ---
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addStretch()

        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(30, 30)
        self._close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ccc;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #fff;
                background: rgba(255, 80, 80, 180);
                border-radius: 4px;
            }
        """)
        self._close_btn.clicked.connect(self._on_close)
        top_bar.addWidget(self._close_btn)

        # --- Subtitle ---
        self._subtitle = QLabel("🎉 恭喜!")
        self._subtitle.setAlignment(Qt.AlignCenter)
        self._subtitle.setStyleSheet("""
            QLabel {
                color: #FFD700;
                font-family: "Microsoft YaHei";
                font-size: 16px;
                font-weight: bold;
                background: transparent;
            }
        """)

        # --- Name label (the rolling / final display) ---
        self._name_label = QLabel("抽")
        self._name_label.setAlignment(Qt.AlignCenter)
        self._name_label.setMinimumHeight(60)
        self._name_label.setStyleSheet("""
            QLabel {
                color: white;
                font-family: "Microsoft YaHei";
                font-size: 36px;
                font-weight: bold;
                background: transparent;
            }
        """)

        # --- Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 8, 20, 16)
        main_layout.setSpacing(4)
        main_layout.addLayout(top_bar)
        main_layout.addStretch()
        main_layout.addWidget(self._subtitle)
        main_layout.addSpacing(8)
        main_layout.addWidget(self._name_label)
        main_layout.addStretch()

    # --- Public API ---

    def set_name_pool(self, names: list[str]) -> None:
        """Provide the full list of names for the rolling animation."""
        self._all_names = list(names)

    def show_result(self, result_name: str) -> None:
        """Start the rolling animation and reveal result_name at the end."""
        self._result_name = result_name

        # Stop any running timers
        self._stop_timers()

        # Center on screen
        self._center_on_screen()

        # Show with fade-in
        self.setWindowOpacity(0.0)
        self.show()

        fade_in = QPropertyAnimation(self, b"windowOpacity", self)
        fade_in.setDuration(250)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.OutCubic)
        fade_in.start()

        # Start rolling
        self._roll_count = 0
        self._subtitle.setText("🎉 抽签中...")
        self._subtitle.setStyleSheet("""
            QLabel {
                color: #FFD700;
                font-family: "Microsoft YaHei";
                font-size: 16px;
                font-weight: bold;
                background: transparent;
            }
        """)
        self._name_label.setStyleSheet("""
            QLabel {
                color: #87CEEB;
                font-family: "Microsoft YaHei";
                font-size: 36px;
                font-weight: bold;
                background: transparent;
            }
        """)

        self._roll_timer = QTimer(self)
        self._roll_timer.timeout.connect(self._on_roll_tick)
        self._roll_timer.start(self.ROLL_INTERVAL_MS)

    # --- Internal ---

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geom = screen.availableGeometry()
        x = geom.center().x() - self.POPUP_WIDTH // 2
        y = geom.center().y() - self.POPUP_HEIGHT // 2
        self.move(x, y)

    def _on_roll_tick(self) -> None:
        self._roll_count += 1
        elapsed = self._roll_count * self.ROLL_INTERVAL_MS

        if elapsed >= self.ROLL_DURATION_MS:
            # Stop rolling — reveal result
            self._stop_timers()
            self._reveal_result()
            return

        # Pick a random name to display (different from last if possible)
        if self._all_names:
            name = random.choice(self._all_names)
            self._name_label.setText(name)

    def _reveal_result(self) -> None:
        """Show the final drawn name."""
        # Brief pause with last random name, then reveal
        QTimer.singleShot(100, self._show_final)

    def _show_final(self) -> None:
        self._name_label.setText(self._result_name)
        self._name_label.setStyleSheet("""
            QLabel {
                color: white;
                font-family: "Microsoft YaHei";
                font-size: 40px;
                font-weight: bold;
                background: transparent;
            }
        """)
        self._subtitle.setText("🎉 恭喜!")
        self._subtitle.setStyleSheet("""
            QLabel {
                color: #FFD700;
                font-family: "Microsoft YaHei";
                font-size: 16px;
                font-weight: bold;
                background: transparent;
            }
        """)

        # Auto-close after 5 seconds
        self._auto_close_timer = QTimer(self)
        self._auto_close_timer.setSingleShot(True)
        self._auto_close_timer.timeout.connect(self._fade_out)
        self._auto_close_timer.start(self.AUTO_CLOSE_MS)

    def _fade_out(self) -> None:
        """Fade out and close."""
        self._stop_timers()
        fade_out = QPropertyAnimation(self, b"windowOpacity", self)
        fade_out.setDuration(400)
        fade_out.setStartValue(self.windowOpacity())
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.InCubic)
        fade_out.finished.connect(self._on_close)
        fade_out.start()

    def _on_close(self) -> None:
        self._stop_timers()
        self.hide()

    def _stop_timers(self) -> None:
        for t in (self._roll_timer, self._auto_close_timer):
            if t is not None:
                t.stop()
        self._roll_timer = None
        self._auto_close_timer = None

    # --- Painting ---

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        path.addRoundedRect(rect, 18, 18)

        painter.setBrush(QBrush(QColor(25, 25, 35, 235)))
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.drawPath(path)

        painter.end()
