# 🦉 OwlLoc — iOS GPS Spoofer for Windows

Spoof your iPhone's GPS location from Windows using a USB cable. No jailbreak required.

## Features

- **Click-to-spoof** — click anywhere on the interactive map to set a fake location
- **Address search** — search by name or paste coordinates directly
- **GPX route playback** — load a `.gpx` file and simulate movement with adjustable speed
- **Favorites** — save and re-spoof locations with one click
- **iOS 17+ support** — uses the RSD tunnel protocol automatically

## Requirements

- Windows 10 or 11
- Python 3.10+
- **iTunes** (from [apple.com/itunes](https://www.apple.com/itunes/)) **or** [Apple Devices](https://apps.microsoft.com/detail/9NP83LWLPZ9N) from the Microsoft Store
- iPhone connected via USB cable with **Developer Mode enabled**

> **Enable Developer Mode (iOS 16+):** Settings → Privacy & Security → Developer Mode → On

## Installation

```bat
git clone https://github.com/xcodenexus/owlloc.git
cd owlloc
pip install -r requirements.txt
```

## Running

```bat
run.bat
```

Or directly:

```bat
python main.py
```

## iOS 17+ Setup

iOS 17 and later requires an admin tunnel for location spoofing. On first use, OwlLoc will prompt for UAC elevation to start it automatically. If that fails, run this in an **admin terminal** and keep it open:

```bat
python -m pymobiledevice3 remote tunneld
```

## Troubleshooting

| Problem | Fix |
|---|---|
| iPhone not detected | Install iTunes or Apple Devices app; reconnect cable |
| "Tap Trust on your iPhone" | Unlock iPhone, trust the computer, enter passcode |
| Location won't set | Enable Developer Mode: Settings → Privacy & Security → Developer Mode |
| iOS 17+ driver missing | Install [Apple Devices](https://apps.microsoft.com/detail/9NP83LWLPZ9N) from Microsoft Store |
| Map tiles not loading | Check internet connection |

## License

MIT — see [LICENSE](LICENSE)
