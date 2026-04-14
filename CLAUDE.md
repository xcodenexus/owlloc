# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**OwlLoc** — a Windows desktop app that spoofs GPS location on iOS devices connected via USB, using Apple's DDI/RSD protocol via `pymobiledevice3`.

## Running the App

```bash
# Using the venv (preferred)
.venv/Scripts/python main.py

# Or via the batch launcher (auto-installs deps)
run.bat
```

## Installing Dependencies

```bash
.venv/Scripts/pip install -r requirements.txt
```

Dependencies: `PyQt6>=6.6.0`, `PyQt6-WebEngine>=6.6.0`, `PyQt6-sip>=13.6.0`, `pymobiledevice3>=4.0.0`.  
Windows system requirement: iTunes (for Apple Mobile Device Service / usbmuxd USB drivers).

## Architecture

3-column layout: **Sidebar** (device status + nav) | **Map** (Leaflet.js in QWebEngineView) | **Right Panel** (swaps between spoof/favorites/gpx based on nav).

```
main.py                    # QApplication entry point
ui/main_window.py          # QMainWindow: wires sidebar, map, right panels together
ui/map_widget.py           # QWebEngineView + QWebChannel bridge (MapWidget, MapBridge)
ui/spoof_panel.py          # SpoofPanel: coords input, set/stop/save buttons
ui/favorites_panel.py      # FavoritesPanel + FavoriteItemWidget
ui/gpx_panel.py            # GpxPanel: file picker, speed slider, QTimer playback
ui/styles.py               # COLORS dict + get_stylesheet() QSS string
core/device_manager.py     # DeviceManager: pymobiledevice3 wrapper, QTimer polling
core/favorites.py          # JSON read/write at ~/.owlloc/favorites.json
core/gpx_parser.py         # ET-based GPX parser (trkpt > rtept > wpt priority)
assets/map.html            # Leaflet map with inline QWebChannel + window.mapAPI
```

> `main.py`, `ui/main_window.py`, and `core/device_manager.py` are specified in the PRD but not yet implemented.

## Critical Implementation Rules

### Map loading — NEVER use `setHtml()`
Always load `assets/map.html` via file URL. `setHtml()` creates a null origin that blocks CDN tile requests:
```python
self.load(QUrl.fromLocalFile(os.path.abspath(map_path)))
```
Required `QWebEngineSettings` attributes: `LocalContentCanAccessRemoteUrls` (critical for tiles), `JavascriptEnabled`, `LocalContentCanAccessFileUrls`.

### JavaScript ↔ Python bridge
- Python registers a `MapBridge` (QObject) as `"bridge"` on a `QWebChannel`, set on the page.
- JS calls `bridge.onLocationSelected(lat, lng)` → Python receives via `@pyqtSlot`.
- Python calls JS via `page().runJavaScript(f"window.mapAPI.someMethod(...);")`.
- `window.mapAPI` exposes: `flyToLocation`, `setMarker`, `showRoute`, `clearRoute`, `animateRouteStep`.
- The bridge is only available after `new QWebChannel(qt.webChannelTransport, cb)` resolves in JS — always guard with `if (bridge)`.

### Threading — all pymobiledevice3 calls must be off the main thread
Device operations take 5–30 seconds. Use `threading.Thread(target=..., daemon=True)` and emit Qt signals back to the UI. `DeviceManager` polls via `QTimer` every 3 seconds.

### iOS version handling
- iOS 12–16: `DvtSecureSocketProxyService` + `LocationSimulation`
- iOS 17+: RSD/tunnel-based; user may need `sudo python -m pymobiledevice3 remote start-tunnel` and Developer Mode enabled
- Fallback: `subprocess.run(["python", "-m", "pymobiledevice3", "developer", "dvt", "simulate-location", "set", "--", lat, lng])`

## UI Conventions

**Button object names** (set via `setObjectName`): `btn-primary` (orange fill), `btn-secondary` (transparent + border), `btn-danger` (transparent + red border). The QSS in `ui/styles.py` selects on these IDs.

**Color constants**: use `ui/styles.py::COLORS` (or shorthand `C`). Never hardcode hex values — all design tokens are defined there.

**GPX speed slider**: range 1–50, divide by 10 for display (0.1x–5.0x). Timer interval: `max(200, int(1000 / speed))` ms.

**Device status states**: No device (red dot) → Detected/untrusted (yellow, show Trust instructions) → Connected (green) → iOS 17 no dev mode (warning) → Spoofing active (green + "Spoofing").

## Data Storage

Favorites: `~/.owlloc/favorites.json` — list of `{name, lat, lng, created}` objects. `core/favorites.py` provides `load()`, `add()`, `remove(index)`, `save_all()`.
