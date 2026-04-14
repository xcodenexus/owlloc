import threading

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget,
    QMessageBox, QSizePolicy,
)

from core.device_manager import DeviceManager
from ui.map_widget import MapWidget
from ui.spoof_panel import SpoofPanel
from ui.favorites_panel import FavoritesPanel
from ui.gpx_panel import GpxPanel
from ui.styles import COLORS as C


class SidebarNavBtn(QPushButton):
    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(f"  {icon}  {text}", parent)
        self.setObjectName("nav-btn")
        self.setCheckable(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._active = False

    def set_active(self, active: bool):
        self._active = active
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OwlLoc — iOS Location Spoofer")
        self.setMinimumSize(1100, 680)
        self.resize(1280, 760)

        self._spoofing = False
        self._device_connected = False

        self._build_ui()
        self._connect_signals()

        self.device_manager = DeviceManager()
        self._connect_device_signals()

    # ── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Map (stretch) — build early so MapWidget exists
        self.map_widget = MapWidget()

        # 2. Right panel (stacked) — build before sidebar so panel_stack exists
        self.right_panel = QWidget()
        self.right_panel.setObjectName("right-panel")
        self.right_panel.setFixedWidth(300)
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.panel_stack = QStackedWidget()
        self.spoof_panel = SpoofPanel()
        self.favorites_panel = FavoritesPanel()
        self.gpx_panel = GpxPanel()
        self.panel_stack.addWidget(self.spoof_panel)      # index 0
        self.panel_stack.addWidget(self.favorites_panel)  # index 1
        self.panel_stack.addWidget(self.gpx_panel)        # index 2
        right_layout.addWidget(self.panel_stack)

        # 3. Sidebar — built last so it can call _switch_panel safely
        self.sidebar = self._build_sidebar()

        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(self.map_widget, stretch=1)
        root_layout.addWidget(self.right_panel)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(260)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(4)

        # Logo
        logo_row = QHBoxLayout()
        logo_lbl = QLabel("🦉  OwlLoc")
        logo_lbl.setObjectName("logo-label")
        ver_lbl = QLabel("v1.0")
        ver_lbl.setObjectName("version-label")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        logo_row.addWidget(logo_lbl)
        logo_row.addWidget(ver_lbl)
        layout.addLayout(logo_row)

        layout.addSpacing(12)
        layout.addWidget(self._make_divider())
        layout.addSpacing(8)

        # Device card
        self.device_card = QWidget()
        self.device_card.setObjectName("device-card")
        card_layout = QVBoxLayout(self.device_card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(4)

        dev_header = QHBoxLayout()
        self.device_dot = QLabel("●")
        self.device_dot.setObjectName("status-dot")
        self.device_dot.setStyleSheet(f"color: {C['error']}; font-size: 10px;")
        self.device_name_lbl = QLabel("No device connected")
        self.device_name_lbl.setObjectName("device-name")
        dev_header.addWidget(self.device_dot)
        dev_header.addWidget(self.device_name_lbl, stretch=1)
        card_layout.addLayout(dev_header)

        self.device_detail_lbl = QLabel("Connect iPhone via USB")
        self.device_detail_lbl.setObjectName("device-detail")
        self.device_detail_lbl.setWordWrap(True)
        card_layout.addWidget(self.device_detail_lbl)

        self.device_status_lbl = QLabel("")
        self.device_status_lbl.setObjectName("status-text")
        self.device_status_lbl.setWordWrap(True)
        card_layout.addWidget(self.device_status_lbl)

        layout.addWidget(self.device_card)
        layout.addSpacing(12)
        layout.addWidget(self._make_divider())
        layout.addSpacing(8)

        # Navigation
        nav_label = QLabel("NAVIGATION")
        nav_label.setObjectName("section-label")
        layout.addWidget(nav_label)
        layout.addSpacing(4)

        self.nav_spoof = SidebarNavBtn("📍", "Spoof Location")
        self.nav_favorites = SidebarNavBtn("⭐", "Favorites")
        self.nav_routes = SidebarNavBtn("🗺️", "GPX Routes")

        self.nav_spoof.clicked.connect(lambda: self._switch_panel(0))
        self.nav_favorites.clicked.connect(lambda: self._switch_panel(1))
        self.nav_routes.clicked.connect(lambda: self._switch_panel(2))

        layout.addWidget(self.nav_spoof)
        layout.addWidget(self.nav_favorites)
        layout.addWidget(self.nav_routes)

        layout.addStretch()

        # Bottom hint
        hint = QLabel("Tip: Click the map to drop a pin")
        hint.setObjectName("section-label")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self._switch_panel(0)
        return sidebar

    def _make_divider(self):
        line = QFrame()
        line.setObjectName("divider")
        line.setFrameShape(QFrame.Shape.HLine)
        return line

    def _switch_panel(self, index: int):
        self.panel_stack.setCurrentIndex(index)
        for i, btn in enumerate([self.nav_spoof, self.nav_favorites, self.nav_routes]):
            btn.set_active(i == index)
        if index == 1:
            self.favorites_panel.refresh()

    # ── Signal wiring ────────────────────────────────────────────────────────

    def _connect_signals(self):
        # Map → spoof panel
        self.map_widget.location_selected.connect(self._on_map_click)

        # Spoof panel
        self.spoof_panel.set_location_requested.connect(self._on_set_location)
        self.spoof_panel.stop_requested.connect(self._on_stop_spoofing)
        self.spoof_panel.save_requested.connect(self._on_save_favorite)

        # Favorites panel
        self.favorites_panel.fly_requested.connect(self._fly_to)
        self.favorites_panel.spoof_requested.connect(self._on_set_location)

        # GPX panel
        self.gpx_panel.route_loaded.connect(self.map_widget.show_route)
        self.gpx_panel.route_cleared.connect(self.map_widget.clear_route)
        self.gpx_panel.step_requested.connect(self._on_gpx_step)

    def _connect_device_signals(self):
        dm = self.device_manager
        dm.device_connected.connect(self._on_device_connected)
        dm.device_disconnected.connect(self._on_device_disconnected)
        dm.location_result.connect(self._on_location_result)
        dm.error.connect(self._on_device_error)
        dm.tunneld_needed.connect(self._on_tunneld_needed)

    # ── Map interactions ─────────────────────────────────────────────────────

    @pyqtSlot(float, float)
    def _on_map_click(self, lat: float, lng: float):
        self.spoof_panel.set_coords(lat, lng)
        # Auto-switch to spoof panel when user clicks map
        self._switch_panel(0)

    @pyqtSlot(float, float)
    def _fly_to(self, lat: float, lng: float):
        self.map_widget.fly_to(lat, lng)
        self.spoof_panel.set_coords(lat, lng)

    # ── Spoofing ─────────────────────────────────────────────────────────────

    @pyqtSlot(float, float)
    def _on_set_location(self, lat: float, lng: float):
        if not self._device_connected:
            self.spoof_panel.set_status(False, "Connect iPhone via USB")
            return
        self._spoofing = True
        self.spoof_panel.set_spoofing(True)
        self.spoof_panel.set_status(True, "Setting location…")
        self.device_manager.set_location(lat, lng)
        self.map_widget.fly_to(lat, lng)
        self._update_device_card_spoofing(True)

    @pyqtSlot()
    def _on_stop_spoofing(self):
        self._spoofing = False
        self.spoof_panel.set_spoofing(False)
        self.device_manager.clear_location()
        self._update_device_card_spoofing(False)

    @pyqtSlot(float, float)
    def _on_gpx_step(self, lat: float, lng: float):
        self.map_widget.animate_step(lat, lng)
        if self._device_connected:
            self.device_manager.set_location(lat, lng)

    # ── Favorites ─────────────────────────────────────────────────────────────

    @pyqtSlot(float, float)
    def _on_save_favorite(self, lat: float, lng: float):
        self.favorites_panel.add_favorite(lat, lng)

    # ── Device events ─────────────────────────────────────────────────────────

    @pyqtSlot(dict)
    def _on_device_connected(self, info: dict):
        self._device_connected = True
        ios_ver = info.get("ios_version", "")
        ios_major = int(ios_ver.split(".")[0]) if ios_ver else 0

        self.device_dot.setStyleSheet(f"color: {C['success']}; font-size: 10px;")
        self.device_name_lbl.setText(info.get("name", "iPhone"))
        self.device_detail_lbl.setText(
            f"{info.get('model', '')}  ·  iOS {ios_ver}"
        )

        if ios_major >= 17:
            from core import tunneld_manager
            if not tunneld_manager.is_running():
                self._check_ncm_driver_async()
            else:
                self.device_status_lbl.setText("● Connected")
                self.device_status_lbl.setStyleSheet(f"color: {C['success']}; font-size: 11px;")
        else:
            self.device_status_lbl.setText("● Connected")
            self.device_status_lbl.setStyleSheet(f"color: {C['success']}; font-size: 11px;")

        self.spoof_panel.set_device_connected(True)

    def _check_ncm_driver_async(self):
        import threading
        threading.Thread(target=self._check_ncm_driver, daemon=True).start()

    def _check_ncm_driver(self):
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-PnpDevice | Where-Object { $_.FriendlyName -eq 'Apple Mobile Device Ethernet' } "
             "| Select-Object -ExpandProperty Status"],
            capture_output=True, text=True, timeout=8
        )
        status = result.stdout.strip()
        if status in ("Unknown", "Error", ""):
            self._show_ncm_warning()
        else:
            self.device_status_lbl.setText("● Connected")
            self.device_status_lbl.setStyleSheet(f"color: {C['success']}; font-size: 11px;")

    def _show_ncm_warning(self):
        from PyQt6.QtCore import QMetaObject, Qt
        # Must update UI on main thread
        QMetaObject.invokeMethod(self, "_ncm_warning_on_main", Qt.ConnectionType.QueuedConnection)

    @pyqtSlot()
    def _ncm_warning_on_main(self):
        self.device_dot.setStyleSheet(f"color: {C['warning']}; font-size: 10px;")
        self.device_status_lbl.setText("⚠ Driver missing")
        self.device_status_lbl.setStyleSheet(f"color: {C['warning']}; font-size: 11px;")
        self.spoof_panel.set_status(False,
            "iOS 17+ driver missing.\nInstall 'Apple Devices' from Microsoft Store."
        )

        from PyQt6.QtWidgets import QMessageBox
        import subprocess
        msg = QMessageBox(self)
        msg.setWindowTitle("Driver Required — iOS 17+")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(
            "Your iPhone (iOS 17+) needs the Apple USB NCM network driver.\n\n"
            "This driver comes with the Apple Devices app from the Microsoft Store.\n\n"
            "Click 'Install' to open the Microsoft Store now."
        )
        msg.addButton("Install Apple Devices", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Later", QMessageBox.ButtonRole.RejectRole)
        if msg.exec() == 0:  # AcceptRole
            subprocess.Popen(
                ["powershell", "-Command",
                 "Start-Process 'ms-windows-store://pdp/?productid=9NP83LWLPZ9N'"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )

    @pyqtSlot()
    def _on_device_disconnected(self):
        self._device_connected = False
        self._spoofing = False
        self.device_dot.setStyleSheet(f"color: {C['error']}; font-size: 10px;")
        self.device_name_lbl.setText("No device connected")
        self.device_detail_lbl.setText("Connect iPhone via USB")
        self.device_status_lbl.setText("")
        self.spoof_panel.set_device_connected(False)
        self.spoof_panel.set_spoofing(False)

    @pyqtSlot(str)
    def _on_device_error(self, message: str):
        if message == "__USBMUX_FAILED__":
            self._on_usbmux_failed()
            return
        self.device_dot.setStyleSheet(f"color: {C['warning']}; font-size: 10px;")
        self.device_name_lbl.setText("iPhone detected")
        self.device_detail_lbl.setText(message)
        self.device_status_lbl.setText("⚠ Needs attention")
        self.device_status_lbl.setStyleSheet(f"color: {C['warning']}; font-size: 11px;")

    def _on_usbmux_failed(self):
        import threading
        # Only show once
        if getattr(self, "_usbmux_dialog_shown", False):
            return
        self._usbmux_dialog_shown = True
        threading.Thread(target=self._show_usbmux_fix_dialog, daemon=True).start()

    def _show_usbmux_fix_dialog(self):
        from PyQt6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(self, "_usbmux_fix_on_main", Qt.ConnectionType.QueuedConnection)

    @pyqtSlot()
    def _usbmux_fix_on_main(self):
        import os, subprocess
        from PyQt6.QtWidgets import QMessageBox

        self.device_dot.setStyleSheet(f"color: {C['error']}; font-size: 10px;")
        self.device_name_lbl.setText("Driver error")
        self.device_detail_lbl.setText("Apple device service not running")
        self.device_status_lbl.setText("⚠ Fix required")
        self.device_status_lbl.setStyleSheet(f"color: {C['error']}; font-size: 11px;")

        msg = QMessageBox(self)
        msg.setWindowTitle("Setup Required")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(
            "The Apple device service (usbmuxd) is not running.\n\n"
            "This is usually caused by one of:\n"
            "  • Apple Devices app not fully initialized\n"
            "  • iTunes not installed\n"
            "  • NCM USB driver not applied\n\n"
            "Click 'Run Fix (Admin)' to automatically fix this.\n"
            "A UAC prompt will appear — click Yes."
        )
        fix_btn = msg.addButton("Run Fix (Admin)", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Later", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() == fix_btn:
            script = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "setup_drivers.ps1")
            )
            # Launch PowerShell as admin with the setup script
            import ctypes
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "powershell.exe",
                f'-ExecutionPolicy Bypass -File "{script}"',
                None, 1
            )
            # Reset dialog flag so it can re-check after fix
            self._usbmux_dialog_shown = False

    @pyqtSlot(bool, str)
    def _on_location_result(self, success: bool, message: str):
        self.spoof_panel.set_status(success, message)
        if not success:
            self._spoofing = False
            self.spoof_panel.set_spoofing(False)
            self._update_device_card_spoofing(False)

    def _update_device_card_spoofing(self, active: bool):
        if active:
            self.device_status_lbl.setText("📍 Spoofing active")
            self.device_status_lbl.setStyleSheet(f"color: {C['accent']}; font-size: 11px;")
        elif self._device_connected:
            self.device_status_lbl.setText("● Connected")
            self.device_status_lbl.setStyleSheet(f"color: {C['success']}; font-size: 11px;")

    @pyqtSlot()
    def _on_tunneld_needed(self):
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("Admin Required — iOS 17+ Tunnel")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(
            "Your iPhone requires an admin tunnel to spoof location.\n\n"
            "Click OK — a UAC prompt will appear asking for admin rights.\n"
            "Accept it to start the tunnel."
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        if msg.exec() == QMessageBox.StandardButton.Cancel:
            self.spoof_panel.set_status(False, "Tunnel cancelled — location not set")
            self.spoof_panel.set_spoofing(False)
            self._spoofing = False
