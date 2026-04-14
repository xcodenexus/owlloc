from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame,
)


class SpoofPanel(QWidget):
    set_location_requested = pyqtSignal(float, float)
    stop_requested = pyqtSignal()
    save_requested = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lat: float = 0.0
        self._lng: float = 0.0
        self._spoofing = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        title = QLabel("Spoof Location")
        title.setObjectName("panel-title")
        layout.addWidget(title)

        layout.addWidget(self._make_divider())

        # Coordinates section
        coords_label = QLabel("COORDINATES")
        coords_label.setObjectName("section-label")
        layout.addWidget(coords_label)

        lat_label = QLabel("Latitude")
        lat_label.setObjectName("section-label")
        layout.addWidget(lat_label)

        self.lat_input = QLineEdit()
        self.lat_input.setPlaceholderText("e.g. 40.758896")
        layout.addWidget(self.lat_input)

        lng_label = QLabel("Longitude")
        lng_label.setObjectName("section-label")
        layout.addWidget(lng_label)

        self.lng_input = QLineEdit()
        self.lng_input.setPlaceholderText("e.g. -73.985130")
        layout.addWidget(self.lng_input)

        layout.addSpacing(4)
        layout.addWidget(self._make_divider())
        layout.addSpacing(4)

        # Hint
        self.hint_label = QLabel("Click the map to select a location")
        self.hint_label.setObjectName("section-label")
        self.hint_label.setWordWrap(True)
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hint_label)

        layout.addSpacing(4)

        # Set Location button
        self.btn_set = QPushButton("⚡  Set Location")
        self.btn_set.setObjectName("btn-primary")
        self.btn_set.setMinimumHeight(40)
        self.btn_set.clicked.connect(self._on_set)
        layout.addWidget(self.btn_set)

        # Stop Spoofing button
        self.btn_stop = QPushButton("⏹  Stop Spoofing")
        self.btn_stop.setObjectName("btn-danger")
        self.btn_stop.setMinimumHeight(36)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_requested)
        layout.addWidget(self.btn_stop)

        # Save to Favorites
        self.btn_save = QPushButton("⭐  Save to Favorites")
        self.btn_save.setObjectName("btn-secondary")
        self.btn_save.setMinimumHeight(36)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._on_save)
        layout.addWidget(self.btn_save)

        layout.addStretch()

        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("section-label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

    def _make_divider(self):
        line = QFrame()
        line.setObjectName("divider")
        line.setFrameShape(QFrame.Shape.HLine)
        return line

    # ── Public API ───────────────────────────────────────────────────────────

    def set_coords(self, lat: float, lng: float):
        self._lat = lat
        self._lng = lng
        self.lat_input.setText(f"{lat:.6f}")
        self.lng_input.setText(f"{lng:.6f}")
        self.btn_save.setEnabled(True)
        self.hint_label.setText(f"{lat:.6f}, {lng:.6f}")

    def set_spoofing(self, active: bool):
        self._spoofing = active
        self.btn_stop.setEnabled(active)
        self.btn_set.setEnabled(not active)

    def set_status(self, ok: bool, message: str):
        color = "#34c759" if ok else "#ff3b30"
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def set_device_connected(self, connected: bool):
        self.btn_set.setEnabled(connected and not self._spoofing)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _parse_inputs(self):
        try:
            lat = float(self.lat_input.text().strip())
            lng = float(self.lng_input.text().strip())
            return lat, lng
        except ValueError:
            return None, None

    def _on_set(self):
        lat, lng = self._parse_inputs()
        if lat is None:
            self.set_status(False, "Enter valid coordinates or click the map")
            return
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            self.set_status(False, "Coordinates out of range")
            return
        self._lat, self._lng = lat, lng
        self.set_location_requested.emit(lat, lng)

    def _on_save(self):
        lat, lng = self._parse_inputs()
        if lat is None:
            lat, lng = self._lat, self._lng
        self.save_requested.emit(lat, lng)
