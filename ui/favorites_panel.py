from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QFrame, QInputDialog, QMessageBox,
)

from core import favorites as fav_store


class FavoriteItemWidget(QWidget):
    fly_requested = pyqtSignal(float, float)
    spoof_requested = pyqtSignal(float, float)
    delete_requested = pyqtSignal()

    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.entry = entry
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Icon + text
        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(entry["name"])
        name_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #f0f0f0;")
        coords_lbl = QLabel(f"{entry['lat']:.6f}, {entry['lng']:.6f}")
        coords_lbl.setStyleSheet("font-size: 11px; color: #888899; font-family: Consolas;")
        info.addWidget(name_lbl)
        info.addWidget(coords_lbl)

        btn_go = QPushButton("Go")
        btn_go.setObjectName("btn-secondary")
        btn_go.setFixedWidth(40)
        btn_go.setFixedHeight(28)
        btn_go.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        btn_go.clicked.connect(lambda: self.fly_requested.emit(entry["lat"], entry["lng"]))

        btn_spoof = QPushButton("⚡")
        btn_spoof.setObjectName("btn-primary")
        btn_spoof.setFixedWidth(32)
        btn_spoof.setFixedHeight(28)
        btn_spoof.setStyleSheet("font-size: 11px; padding: 2px;")
        btn_spoof.setToolTip("Fly to and spoof immediately")
        btn_spoof.clicked.connect(lambda: self.spoof_requested.emit(entry["lat"], entry["lng"]))

        btn_del = QPushButton("✕")
        btn_del.setObjectName("btn-danger")
        btn_del.setFixedWidth(28)
        btn_del.setFixedHeight(28)
        btn_del.setStyleSheet("font-size: 11px; padding: 2px;")
        btn_del.clicked.connect(self.delete_requested)

        layout.addLayout(info, stretch=1)
        layout.addWidget(btn_go)
        layout.addWidget(btn_spoof)
        layout.addWidget(btn_del)

        # Card style
        self.setStyleSheet("""
            FavoriteItemWidget {
                background-color: #16161f;
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.06);
            }
            FavoriteItemWidget:hover {
                background-color: #1e1e2a;
            }
        """)


class FavoritesPanel(QWidget):
    fly_requested = pyqtSignal(float, float)
    spoof_requested = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Favorites")
        title.setObjectName("panel-title")
        layout.addWidget(title)

        layout.addWidget(self._make_divider())

        self.empty_label = QLabel("No saved locations yet.\nClick ⭐ on the Spoof tab to save one.")
        self.empty_label.setObjectName("section-label")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        layout.addWidget(self.empty_label)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        layout.addWidget(self.list_widget, stretch=1)

    def _make_divider(self):
        line = QFrame()
        line.setObjectName("divider")
        line.setFrameShape(QFrame.Shape.HLine)
        return line

    def refresh(self):
        self.list_widget.clear()
        entries = fav_store.load()
        self.empty_label.setVisible(len(entries) == 0)
        self.list_widget.setVisible(len(entries) > 0)

        for i, entry in enumerate(entries):
            item = QListWidgetItem(self.list_widget)
            widget = FavoriteItemWidget(entry)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

            # Capture index in lambda
            widget.fly_requested.connect(self.fly_requested)
            widget.spoof_requested.connect(self.spoof_requested)
            widget.delete_requested.connect(lambda idx=i: self._delete(idx))

    def _delete(self, index: int):
        entries = fav_store.load()
        if 0 <= index < len(entries):
            name = entries[index]["name"]
            reply = QMessageBox.question(
                self, "Delete Favorite",
                f'Remove "{name}" from favorites?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                fav_store.remove(index)
                self.refresh()

    def add_favorite(self, lat: float, lng: float):
        name, ok = QInputDialog.getText(self, "Save Location", "Name for this location:")
        if ok and name.strip():
            fav_store.add(name.strip(), lat, lng)
            self.refresh()
