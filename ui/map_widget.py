import os

from PyQt6.QtCore import QObject, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView


class MapBridge(QObject):
    """JavaScript → Python bridge: receives map click events."""
    location_selected = pyqtSignal(float, float)

    @pyqtSlot(float, float)
    def onLocationSelected(self, lat: float, lng: float):
        self.location_selected.emit(lat, lng)


class MapWidget(QWebEngineView):
    location_selected = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Required settings — LocalContentCanAccessRemoteUrls is critical for tiles
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

        # Bridge setup
        self.bridge = MapBridge()
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        self.page().setWebChannel(self.channel)

        self.bridge.location_selected.connect(self.location_selected)

        # Load from file URL — NEVER use setHtml() (breaks tile loading)
        map_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "assets", "map.html")
        )
        self.load(QUrl.fromLocalFile(map_path))

    # ── Python → JavaScript API ──────────────────────────────────────────────

    def fly_to(self, lat: float, lng: float, zoom: int = 15):
        self.page().runJavaScript(f"window.mapAPI.flyToLocation({lat}, {lng}, {zoom});")

    def set_marker(self, lat: float, lng: float):
        self.page().runJavaScript(f"window.mapAPI.setMarker({lat}, {lng});")

    def show_route(self, points: list):
        import json
        self.page().runJavaScript(f"window.mapAPI.showRoute({json.dumps(points)});")

    def clear_route(self):
        self.page().runJavaScript("window.mapAPI.clearRoute();")

    def animate_step(self, lat: float, lng: float):
        self.page().runJavaScript(f"window.mapAPI.animateRouteStep({lat}, {lng});")
