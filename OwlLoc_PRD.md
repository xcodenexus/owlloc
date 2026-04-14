# OwlLoc — iOS Location Spoofer for Windows

## Product Requirements Document (PRD)

**Version:** 2.0
**Platform:** Windows 10/11 Desktop
**Tech Stack:** Python 3.10+, PyQt6, pymobiledevice3, Leaflet.js
**Goal:** Build a 3uTools-style iOS GPS spoofer with a working interactive map and reliable device detection.

---

## 1. Overview

OwlLoc is a Windows desktop application that spoofs GPS location on iOS devices connected via USB. It uses Apple's Developer Disk Image (DDI) protocol — the same mechanism Xcode uses — through the `pymobiledevice3` library.

The app has three core functions:
1. Set a fake GPS coordinate on a connected iPhone
2. Simulate movement along a GPX route
3. Save/manage favorite locations

---

## 2. Architecture

```
owlloc/
├── main.py                  # Entry point, launches app
├── ui/
│   ├── main_window.py       # QMainWindow with sidebar + content
│   ├── map_widget.py        # Map component (see Section 5)
│   ├── spoof_panel.py       # Right panel: coordinates + spoof buttons
│   ├── favorites_panel.py   # Right panel: saved locations list
│   ├── gpx_panel.py         # Right panel: GPX route player
│   └── styles.py            # All QSS stylesheets and color constants
├── core/
│   ├── device_manager.py    # pymobiledevice3 wrapper (see Section 4)
│   ├── favorites.py         # JSON-based favorites storage
│   └── gpx_parser.py        # GPX file parser
├── assets/
│   └── map.html             # Leaflet.js map (loaded into QWebEngineView)
├── requirements.txt
└── run.bat
```

---

## 3. Critical Fix #1 — Map Must Actually Render

### The Problem
QWebEngineView fails to load the map HTML because:
- Loading raw HTML with `setHtml()` blocks network requests (Leaflet CDN tiles won't load)
- CARTO/OpenStreetMap tile servers require proper origin headers
- QWebChannel injection can break if done via string replacement

### The Correct Implementation

**3.1 — Load map.html from a local file URL, NOT setHtml()**

```python
import os
from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

class MapWidget(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Enable required settings
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

        # Load from file URL — this is critical for tile loading
        map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'map.html')
        self.load(QUrl.fromLocalFile(os.path.abspath(map_path)))
```

**3.2 — map.html must include QWebChannel setup inline**

The map.html file must:
- Load Leaflet from CDN (unpkg or cdnjs)
- Load `qwebchannel.js` from Qt's resource system: `qrc:///qtwebchannel/qwebchannel.js`
- Initialize the bridge BEFORE the map click handler tries to use it
- Use CARTO dark tiles: `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
  <style>
    * { margin: 0; padding: 0; }
    body { background: #0a0a0f; }
    #map { width: 100vw; height: 100vh; }
  </style>
</head>
<body>
  <div id="map"></div>

  <!-- Search bar overlay -->
  <div id="search-box" style="position:fixed; top:16px; left:50%; transform:translateX(-50%); z-index:9999;">
    <input id="search-input" type="text" placeholder="Search location or paste coordinates..." />
    <button id="search-btn">GO</button>
  </div>

  <!-- Coordinates display overlay -->
  <div id="coords-overlay" style="position:fixed; bottom:16px; left:50%; transform:translateX(-50%); z-index:9999;">
    <span>LAT: <span id="lat-val">0.000000</span></span>
    <span>LNG: <span id="lng-val">0.000000</span></span>
  </div>

  <script>
    // 1. Initialize map
    const map = L.map('map', { center: [6.5244, 3.3792], zoom: 13, zoomControl: false });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '© OpenStreetMap © CARTO', maxZoom: 19
    }).addTo(map);
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // 2. Bridge — wait for QWebChannel before using
    let bridge = null;
    new QWebChannel(qt.webChannelTransport, function(channel) {
      bridge = channel.objects.bridge;
    });

    // 3. Marker + click handler
    let currentMarker = null;

    map.on('click', function(e) {
      const { lat, lng } = e.latlng;
      setMarker(lat, lng);
      if (bridge) bridge.onLocationSelected(lat, lng);
    });

    function setMarker(lat, lng) {
      if (currentMarker) map.removeLayer(currentMarker);
      currentMarker = L.marker([lat, lng]).addTo(map);
      document.getElementById('lat-val').textContent = lat.toFixed(6);
      document.getElementById('lng-val').textContent = lng.toFixed(6);
    }

    function flyToLocation(lat, lng, zoom) {
      map.flyTo([lat, lng], zoom || 15, { duration: 1.2 });
      setMarker(lat, lng);
    }

    // 4. Search (Nominatim geocoding)
    document.getElementById('search-btn').addEventListener('click', doSearch);
    document.getElementById('search-input').addEventListener('keydown', e => {
      if (e.key === 'Enter') doSearch();
    });

    async function doSearch() {
      const q = document.getElementById('search-input').value.trim();
      if (!q) return;
      // Check if coordinates
      const m = q.match(/^(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)$/);
      if (m) { flyToLocation(parseFloat(m[1]), parseFloat(m[2])); return; }
      // Geocode
      const r = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&limit=1`);
      const data = await r.json();
      if (data.length) flyToLocation(parseFloat(data[0].lat), parseFloat(data[0].lon));
    }

    // 5. Route display + animation (called from Python via runJavaScript)
    let routeMarkers = [], routeLine = null;

    function showRoute(points) {
      clearRoute();
      const ll = points.map(p => [p.lat, p.lng]);
      routeLine = L.polyline(ll, { color: '#ff9500', weight: 3, dashArray: '8,6' }).addTo(map);
      map.fitBounds(routeLine.getBounds(), { padding: [50, 50] });
    }
    function clearRoute() {
      routeMarkers.forEach(m => map.removeLayer(m));
      routeMarkers = [];
      if (routeLine) { map.removeLayer(routeLine); routeLine = null; }
    }
    function animateRouteStep(lat, lng) {
      setMarker(lat, lng);
      map.panTo([lat, lng], { animate: true, duration: 0.3 });
    }

    // Expose API for Python to call
    window.mapAPI = { flyToLocation, setMarker, showRoute, clearRoute, animateRouteStep };
  </script>
</body>
</html>
```

**3.3 — QWebChannel bridge setup in Python**

```python
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt6.QtWebChannel import QWebChannel

class MapBridge(QObject):
    """Bridge between JavaScript map and Python app."""
    location_selected = pyqtSignal(float, float)

    @pyqtSlot(float, float)
    def onLocationSelected(self, lat, lng):
        self.location_selected.emit(lat, lng)

# In your MapWidget or MainWindow:
self.bridge = MapBridge()
self.channel = QWebChannel()
self.channel.registerObject("bridge", self.bridge)
self.map_view.page().setWebChannel(self.channel)

# Connect signal
self.bridge.location_selected.connect(self.on_map_click)
```

**3.4 — Calling JavaScript from Python**

```python
# Fly to a location
self.map_view.page().runJavaScript(f"window.mapAPI.flyToLocation({lat}, {lng}, 15);")

# Show GPX route
import json
points_json = json.dumps(route_points)  # [{"lat": ..., "lng": ...}, ...]
self.map_view.page().runJavaScript(f"window.mapAPI.showRoute({points_json});")

# Animate one step
self.map_view.page().runJavaScript(f"window.mapAPI.animateRouteStep({lat}, {lng});")
```

---

## 4. Critical Fix #2 — Device Detection + Trust Dialog

### The Problem
The device is not detected and the iPhone "Trust This Computer?" dialog is not appearing because:
- iTunes / Apple Mobile Device Support may not be installed
- usbmuxd service is not running
- pymobiledevice3 needs specific pairing flow
- iOS 17+ uses a completely different protocol (RSD over RemoteXPC)

### The Correct Implementation

**4.1 — Prerequisites check on startup**

On app launch, check and guide the user:

```python
import subprocess
import shutil

def check_prerequisites():
    issues = []

    # 1. Check if iTunes drivers are available (usbmuxd / Apple Mobile Device Service)
    try:
        result = subprocess.run(
            ['sc', 'query', 'Apple Mobile Device Service'],
            capture_output=True, text=True
        )
        if 'RUNNING' not in result.stdout:
            issues.append("Apple Mobile Device Service is not running. Install iTunes from apple.com/itunes")
    except:
        issues.append("Cannot check Apple Mobile Device Service. Install iTunes from apple.com/itunes")

    # 2. Check pymobiledevice3
    try:
        import pymobiledevice3
    except ImportError:
        issues.append("pymobiledevice3 not installed. Run: pip install pymobiledevice3")

    return issues
```

**4.2 — Device scanning with proper error handling**

```python
import threading
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

class DeviceManager(QObject):
    device_connected = pyqtSignal(dict)      # {name, udid, ios_version, model}
    device_disconnected = pyqtSignal()
    location_result = pyqtSignal(bool, str)  # (success, message)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._lockdown = None
        self._scan_timer = QTimer()
        self._scan_timer.timeout.connect(self._scan)
        self._scan_timer.start(3000)  # scan every 3 seconds

    def _scan(self):
        threading.Thread(target=self._do_scan, daemon=True).start()

    def _do_scan(self):
        try:
            from pymobiledevice3.usbmux import list_devices
            from pymobiledevice3.lockdown import create_using_usbmux

            devices = list_devices()
            if not devices:
                self._lockdown = None
                self.device_disconnected.emit()
                return

            # create_using_usbmux triggers the Trust dialog on the iPhone
            # if the device hasn't been paired yet.
            # The user MUST tap "Trust" and enter their passcode on the iPhone.
            lockdown = create_using_usbmux(serial=devices[0].serial)

            self._lockdown = lockdown
            self.device_connected.emit({
                "name": lockdown.display_name,
                "udid": lockdown.udid,
                "ios_version": lockdown.product_version,
                "model": lockdown.product_type,
            })

        except Exception as e:
            error_msg = str(e).lower()

            if "password" in error_msg or "passcode" in error_msg:
                self.error.emit("Unlock your iPhone and enter your passcode")
            elif "trust" in error_msg or "pair" in error_msg:
                self.error.emit("Tap 'Trust' on your iPhone when prompted")
            elif "usbmux" in error_msg or "mux" in error_msg:
                self.error.emit("Install iTunes to enable USB communication")
            elif "device" in error_msg and "not found" in error_msg:
                self.device_disconnected.emit()
            else:
                self.error.emit(f"Device error: {e}")

    def set_location(self, lat: float, lng: float):
        """Set fake GPS on connected device. Run in a thread."""
        if not self._lockdown:
            self.location_result.emit(False, "No device connected")
            return

        ios_version = self._lockdown.product_version
        major = int(ios_version.split('.')[0])

        try:
            if major >= 17:
                self._set_location_ios17(lat, lng)
            else:
                self._set_location_legacy(lat, lng)
        except Exception as e:
            self._set_location_cli_fallback(lat, lng, str(e))

    def _set_location_legacy(self, lat, lng):
        """iOS 12-16: Mount DeveloperDiskImage, use DVT simulate-location."""
        try:
            from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
            from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

            # This automatically mounts the Developer Disk Image if needed
            with DvtSecureSocketProxyService(lockdown=self._lockdown) as dvt:
                LocationSimulation(dvt).set(lat, lng)
            self.location_result.emit(True, f"Location set to {lat:.6f}, {lng:.6f}")
        except Exception as e:
            raise e

    def _set_location_ios17(self, lat, lng):
        """iOS 17+: Uses new RSD-based tunnel protocol."""
        try:
            # pymobiledevice3 >= 2.0 handles iOS 17 via tunneld
            # The user may need to run `sudo python -m pymobiledevice3 remote start-tunnel` first
            from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
            from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
            from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

            with DvtSecureSocketProxyService(lockdown=self._lockdown) as dvt:
                LocationSimulation(dvt).set(lat, lng)
            self.location_result.emit(True, f"Location set to {lat:.6f}, {lng:.6f}")
        except Exception as e:
            raise e

    def _set_location_cli_fallback(self, lat, lng, original_error):
        """Fallback: use pymobiledevice3 CLI subprocess."""
        try:
            result = subprocess.run(
                ["python", "-m", "pymobiledevice3", "developer", "dvt",
                 "simulate-location", "set", "--", str(lat), str(lng)],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                self.location_result.emit(True, f"Location set to {lat:.6f}, {lng:.6f}")
            else:
                stderr = result.stderr.strip()
                if "developer" in stderr.lower() or "image" in stderr.lower():
                    self.location_result.emit(False, "Enable Developer Mode on iPhone: Settings → Privacy & Security → Developer Mode")
                else:
                    self.location_result.emit(False, f"Failed: {stderr}")
        except subprocess.TimeoutExpired:
            self.location_result.emit(False, "Timeout — is iPhone unlocked?")
        except FileNotFoundError:
            self.location_result.emit(False, f"CLI fallback failed. Original error: {original_error}")

    def clear_location(self):
        """Stop spoofing — restore real GPS."""
        if not self._lockdown:
            return
        try:
            from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
            from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

            with DvtSecureSocketProxyService(lockdown=self._lockdown) as dvt:
                LocationSimulation(dvt).clear()
            self.location_result.emit(True, "Location restored to real GPS")
        except:
            try:
                subprocess.run(
                    ["python", "-m", "pymobiledevice3", "developer", "dvt",
                     "simulate-location", "clear"],
                    capture_output=True, text=True, timeout=15
                )
                self.location_result.emit(True, "Location restored to real GPS")
            except Exception as e:
                self.location_result.emit(False, str(e))
```

**4.3 — What to show in the UI for device states**

| State | Sidebar shows | Action |
|-------|--------------|--------|
| No device | "No device connected" + red dot | Show: "Connect iPhone via USB cable" |
| Device found but not trusted | "iPhone detected — tap Trust" + yellow dot | Show instruction overlay |
| Device connected + paired | Device name + iOS version + green dot | Enable spoof buttons |
| iOS 17+ without Developer Mode | Device name + warning | Show: "Enable Developer Mode in Settings" |
| Spoofing active | Device name + "Spoofing 📍" | Show stop button |

---

## 5. UI Design Specification

### 5.1 — Layout (3-column)

```
┌──────────────┬───────────────────────────────────┬────────────────┐
│   SIDEBAR    │           MAP (Leaflet)            │  RIGHT PANEL   │
│   260px      │         (fills remaining)          │    300px       │
│              │                                    │                │
│  🦉 OwlLoc  │    ┌─────────────────────────┐     │  📍 Spoof      │
│  v1.0        │    │  Search bar (overlay)   │     │  Location      │
│              │    └─────────────────────────┘     │                │
│  ────────    │                                    │  Lat: [______] │
│  📱 Device   │         Interactive Map            │  Lng: [______] │
│  iPhone 15   │        (click to place pin)        │                │
│  iOS 17.4    │                                    │  [⚡ Set Loc]  │
│  ● Connected │                                    │  [⏹ Stop]     │
│              │                                    │  [⭐ Save]     │
│  ────────    │    ┌─────────────────────────┐     │                │
│  📍 Spoof    │    │ LAT: 6.524 │ LNG: 3.379│     │                │
│  ⭐ Favorites│    └─────────────────────────┘     │                │
│  🗺️ Routes   │                                    │                │
└──────────────┴───────────────────────────────────┴────────────────┘
```

### 5.2 — Color Palette

```python
COLORS = {
    "bg_primary":    "#0a0a0f",      # Main background
    "bg_secondary":  "#111118",      # Sidebar / right panel
    "bg_card":       "#16161f",      # Cards / panels
    "bg_hover":      "#1e1e2a",      # Hover states
    "accent":        "#ff9500",      # Orange — primary action color
    "accent_dim":    "#cc7700",      # Pressed state
    "text_primary":  "#f0f0f0",      # Main text
    "text_secondary":"#888899",      # Subtitles / labels
    "text_muted":    "#555566",      # Hints / disabled
    "border":        "rgba(255,255,255,0.06)",
    "border_accent": "rgba(255,149,0,0.25)",
    "success":       "#34c759",      # Connected / success
    "error":         "#ff3b30",      # Disconnected / error
    "warning":       "#ffcc00",      # Needs attention
}
```

### 5.3 — Typography
- Font: `Segoe UI` (Windows native)
- Monospace (coordinates): `Consolas` or `JetBrains Mono`
- Logo: 22px bold, accent color
- Section headers: 14px semibold
- Body: 13px regular
- Labels: 12px, text_secondary color

### 5.4 — Button Styles

| Type | Look | Used for |
|------|------|----------|
| Primary | Orange gradient fill, black text, bold | "Set Location", "Start Route" |
| Secondary | Transparent, white text, subtle border | "Go to Coords", "Save to Favorites" |
| Danger | Transparent, red text, red border | "Stop Spoofing", "Delete" |
| Nav | Transparent, left-aligned, checkable | Sidebar navigation items |

### 5.5 — Map Styling
- Dark CARTO basemap tiles
- Orange marker for selected location (custom div icon with gradient)
- Orange dashed polyline for GPX routes
- Coordinate overlay bar at bottom center (dark glass background)
- Search bar at top center (dark glass background)

---

## 6. Feature Specifications

### 6.1 — Spoof Location (Primary Feature)

**Flow:**
1. User clicks map → marker placed, coordinates fill in right panel
2. User can also type coordinates manually or search an address
3. User clicks "Set Location" → pymobiledevice3 sets GPS on iPhone
4. Status updates to "Spoofing active" with green indicator
5. User clicks "Stop Spoofing" → real GPS restored

**Edge cases:**
- No device: show error toast "Connect iPhone via USB"
- No location selected: show error toast "Click the map to select a location"
- iOS 17 without developer mode: show specific instructions
- Spoof fails: show error with helpful message, re-enable button

### 6.2 — Favorites

**Storage:** `~/.owlloc/favorites.json`

```json
[
  { "name": "Home", "lat": 6.5244, "lng": 3.3792, "created": "2025-01-01T00:00:00" },
  { "name": "Times Square", "lat": 40.758, "lng": -73.9855, "created": "2025-01-02T00:00:00" }
]
```

**Interactions:**
- Single click → fly to location on map
- Double click → fly to location AND immediately spoof
- Delete button → remove from list (with confirm)
- Save button on spoof panel → prompt for name, add to list

### 6.3 — GPX Route Playback

**Flow:**
1. User loads a `.gpx` file via file picker
2. Route displayed on map as orange dashed line
3. User adjusts speed slider (0.1x walk to 5.0x drive)
4. User clicks "Start Route" → app moves through each point:
   - Sets location on device via pymobiledevice3
   - Animates marker on map
   - Shows progress "Point 42 / 156"
5. User can pause/resume
6. Route completes → show "Route complete!" message

**Speed calculation:**
- Slider range: 1–50 (divide by 10 for display: 0.1x to 5.0x)
- Timer interval: `max(200, int(1000 / speed))` ms between points
- At 1.0x speed: 1 point per second
- At 5.0x speed: 5 points per second

**GPX parsing:** Support `<trkpt>`, `<rtept>`, `<wpt>` elements with and without XML namespaces.

### 6.4 — Search

**Built into map.html via Nominatim:**
- User types address or place name → geocodes via `nominatim.openstreetmap.org`
- User types "lat, lng" → parses directly
- Result: fly to location and place marker

---

## 7. Important Technical Notes

### 7.1 — Threading
ALL pymobiledevice3 calls MUST run in background threads. They can take 5–30 seconds and will freeze the UI if on the main thread. Use `threading.Thread(target=..., daemon=True)` and emit Qt signals for results.

### 7.2 — iOS 17+ Special Handling
iOS 17 changed developer services from DDI-based to RSD (RemoteServiceDiscovery) over a tunnel:
- pymobiledevice3 v2+ handles this automatically
- User may need to enable Developer Mode: Settings → Privacy & Security → Developer Mode
- First connection may require running a tunnel daemon
- If the Python API fails, fall back to the CLI: `python -m pymobiledevice3 developer dvt simulate-location set -- LAT LNG`

### 7.3 — Trust Dialog
The "Trust This Computer?" dialog on the iPhone is triggered by `create_using_usbmux()` during the pairing process. Requirements:
- iTunes MUST be installed (provides Apple Mobile Device Support / usbmuxd drivers)
- iPhone must be UNLOCKED when you plug it in
- User must tap "Trust" and enter their passcode
- If trust was denied, user must go to Settings → General → Transfer or Reset → Reset Location & Privacy

### 7.4 — Dependencies

```
PyQt6>=6.6.0
PyQt6-WebEngine>=6.6.0
pymobiledevice3>=4.0.0
```

Install: `pip install PyQt6 PyQt6-WebEngine pymobiledevice3`

On Windows, also needed:
- iTunes (for Apple Mobile Device Service USB drivers)
- OR: Apple Devices app from Microsoft Store (Windows 11)

### 7.5 — QWebEngineView Critical Settings

```python
from PyQt6.QtWebEngineCore import QWebEngineSettings

settings = web_view.settings()
settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)  # REQUIRED for map tiles
settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
```

And load via file URL:
```python
web_view.load(QUrl.fromLocalFile(os.path.abspath("assets/map.html")))
```

NEVER use `setHtml()` — it creates a null origin that blocks all network requests including CDN tile fetches.

---

## 8. Error Handling Matrix

| Error | Detection | User-Facing Message | Action |
|-------|-----------|---------------------|--------|
| No iTunes | Service check fails | "Install iTunes to connect to iPhone" | Show download link |
| No device | `list_devices()` returns empty | "No device detected. Connect via USB" | Keep scanning |
| Not trusted | Pairing exception | "Unlock iPhone and tap 'Trust'" | Show instruction |
| Trust denied | Pairing fails repeatedly | "Reset trust: Settings → General → Transfer or Reset → Reset Location & Privacy" | Show steps |
| iOS 17 no dev mode | DDI mount fails | "Enable Developer Mode: Settings → Privacy → Developer Mode" | Show steps |
| Spoof timeout | subprocess timeout | "Make sure iPhone is unlocked" | Re-enable button |
| GPX parse fail | No points found | "Could not read GPX file" | Show file picker again |
| Map tiles fail | No tiles rendered | Check internet connection | Show offline notice |

---

## 9. File: requirements.txt

```
PyQt6>=6.6.0
PyQt6-WebEngine>=6.6.0
PyQt6-sip>=13.6.0
pymobiledevice3>=4.0.0
```

---

## 10. File: run.bat

```batch
@echo off
title OwlLoc - iOS Location Spoofer
echo.
echo  ================================
echo   OwlLoc v1.0 - iOS GPS Spoofer
echo  ================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Download from python.org
    pause
    exit /b
)

pip show PyQt6 >nul 2>&1 || pip install -r requirements.txt

echo Starting OwlLoc...
python main.py
pause
```

---

## 11. Acceptance Criteria

- [ ] Map renders with dark CARTO tiles on launch
- [ ] Clicking the map places a marker and updates coordinate display
- [ ] Search bar finds locations via Nominatim and moves map
- [ ] Pasting coordinates (e.g. "40.758, -73.985") works in search
- [ ] Connected iPhone is detected and shown in sidebar with name + iOS version
- [ ] Trust dialog is triggered on iPhone for first connection
- [ ] Clicking "Set Location" changes GPS on iPhone (verify in Apple Maps)
- [ ] Clicking "Stop Spoofing" restores real GPS
- [ ] Favorites can be saved, listed, clicked-to-fly, and deleted
- [ ] GPX files load, display route on map, and play back with speed control
- [ ] All device operations run in background threads (no UI freezing)
- [ ] Helpful error messages for every failure state
- [ ] App works on Windows 10 and 11
