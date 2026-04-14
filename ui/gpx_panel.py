from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QProgressBar, QFrame,
    QFileDialog,
)

from core import gpx_parser


class GpxPanel(QWidget):
    route_loaded = pyqtSignal(list)           # list of {lat, lng}
    route_cleared = pyqtSignal()
    step_requested = pyqtSignal(float, float)  # move device to this point
    status_message = pyqtSignal(str, bool)     # (message, is_ok)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: list = []
        self._current_index = 0
        self._paused = False
        self._timer = QTimer()
        self._timer.timeout.connect(self._advance)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("GPX Route")
        title.setObjectName("panel-title")
        layout.addWidget(title)

        layout.addWidget(self._make_divider())

        # Load file button
        self.btn_load = QPushButton("📂  Load GPX File")
        self.btn_load.setObjectName("btn-secondary")
        self.btn_load.setMinimumHeight(38)
        self.btn_load.clicked.connect(self._load_file)
        layout.addWidget(self.btn_load)

        # File info
        self.file_label = QLabel("No file loaded")
        self.file_label.setObjectName("section-label")
        self.file_label.setWordWrap(True)
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.file_label)

        layout.addWidget(self._make_divider())

        # Speed control
        speed_row = QHBoxLayout()
        speed_lbl = QLabel("Speed:")
        speed_lbl.setObjectName("section-label")
        self.speed_value_lbl = QLabel("1.0x")
        self.speed_value_lbl.setObjectName("section-label")
        self.speed_value_lbl.setFixedWidth(36)
        speed_row.addWidget(speed_lbl)
        speed_row.addWidget(self.speed_value_lbl)
        layout.addLayout(speed_row)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 50)
        self.speed_slider.setValue(10)  # 1.0x default
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        layout.addWidget(self.speed_slider)

        speed_hints = QHBoxLayout()
        lbl_slow = QLabel("0.1x walk")
        lbl_slow.setObjectName("section-label")
        lbl_fast = QLabel("5.0x drive")
        lbl_fast.setObjectName("section-label")
        lbl_fast.setAlignment(Qt.AlignmentFlag.AlignRight)
        speed_hints.addWidget(lbl_slow)
        speed_hints.addWidget(lbl_fast)
        layout.addLayout(speed_hints)

        layout.addWidget(self._make_divider())

        # Progress
        self.progress_label = QLabel("Point — / —")
        self.progress_label.setObjectName("section-label")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)

        layout.addSpacing(4)

        # Control buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_start = QPushButton("▶  Start")
        self.btn_start.setObjectName("btn-primary")
        self.btn_start.setMinimumHeight(38)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self._start)
        btn_row.addWidget(self.btn_start)

        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setObjectName("btn-secondary")
        self.btn_pause.setMinimumHeight(38)
        self.btn_pause.setFixedWidth(44)
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._pause)
        btn_row.addWidget(self.btn_pause)

        layout.addLayout(btn_row)

        self.btn_stop_route = QPushButton("⏹  Stop Route")
        self.btn_stop_route.setObjectName("btn-danger")
        self.btn_stop_route.setMinimumHeight(36)
        self.btn_stop_route.setEnabled(False)
        self.btn_stop_route.clicked.connect(self._stop_route)
        layout.addWidget(self.btn_stop_route)

        layout.addStretch()

        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("section-label")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setWordWrap(True)
        layout.addWidget(self.status_lbl)

    def _make_divider(self):
        line = QFrame()
        line.setObjectName("divider")
        line.setFrameShape(QFrame.Shape.HLine)
        return line

    # ── Speed ─────────────────────────────────────────────────────────────────

    def _on_speed_changed(self, value: int):
        speed = value / 10.0
        self.speed_value_lbl.setText(f"{speed:.1f}x")
        if self._timer.isActive():
            self._timer.setInterval(self._interval_ms())

    def _interval_ms(self) -> int:
        speed = self.speed_slider.value() / 10.0
        return max(200, int(1000 / speed))

    # ── File loading ─────────────────────────────────────────────────────────

    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open GPX File", "", "GPX Files (*.gpx);;All Files (*)"
        )
        if not path:
            return
        try:
            self._points = gpx_parser.parse(path)
            fname = path.split("/")[-1].split("\\")[-1]
            self.file_label.setText(f"{fname}  ({len(self._points)} points)")
            self.btn_start.setEnabled(True)
            self._reset_progress()
            self.route_loaded.emit(self._points)
            self._show_status(f"Route loaded: {len(self._points)} points", True)
        except ValueError as e:
            self._show_status(str(e), False)
            self.file_label.setText("Could not read GPX file")

    # ── Playback ──────────────────────────────────────────────────────────────

    def _start(self):
        if not self._points:
            return
        self._current_index = 0
        self._paused = False
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop_route.setEnabled(True)
        self.btn_load.setEnabled(False)
        self._timer.start(self._interval_ms())

    def _pause(self):
        if self._paused:
            self._paused = False
            self.btn_pause.setText("⏸")
            self._timer.start(self._interval_ms())
        else:
            self._paused = True
            self.btn_pause.setText("▶")
            self._timer.stop()

    def _stop_route(self):
        self._timer.stop()
        self._paused = False
        self._current_index = 0
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("⏸")
        self.btn_stop_route.setEnabled(False)
        self.btn_load.setEnabled(True)
        self._reset_progress()
        self.route_cleared.emit()

    def _advance(self):
        if self._current_index >= len(self._points):
            self._timer.stop()
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_stop_route.setEnabled(False)
            self.btn_load.setEnabled(True)
            self.progress_label.setText(f"Route complete! ({len(self._points)} points)")
            self.progress_bar.setValue(100)
            self._show_status("Route complete!", True)
            return

        pt = self._points[self._current_index]
        total = len(self._points)
        idx = self._current_index + 1

        self.progress_label.setText(f"Point {idx} / {total}")
        self.progress_bar.setValue(int(idx / total * 100))

        self.step_requested.emit(pt["lat"], pt["lng"])
        self._current_index += 1

    def _reset_progress(self):
        self.progress_label.setText("Point — / —")
        self.progress_bar.setValue(0)

    def _show_status(self, msg: str, ok: bool):
        color = "#34c759" if ok else "#ff3b30"
        self.status_lbl.setText(msg)
        self.status_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
