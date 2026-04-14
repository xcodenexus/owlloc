import asyncio
import subprocess
import sys
import threading
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# Windows: SelectorEventLoop avoids ProactorEventLoop SSL cleanup noise
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def check_prerequisites():
    """Return list of issues found. Empty list = all good."""
    issues = []

    # Apple Mobile Device Service (iTunes drivers)
    try:
        result = subprocess.run(
            ["sc", "query", "Apple Mobile Device Service"],
            capture_output=True, text=True, timeout=5
        )
        if "RUNNING" not in result.stdout:
            issues.append(
                "Apple Mobile Device Service is not running.\n"
                "Install iTunes from apple.com/itunes or Apple Devices from the Microsoft Store."
            )
    except Exception:
        issues.append(
            "Cannot check Apple Mobile Device Service.\n"
            "Install iTunes or Apple Devices (Microsoft Store) to enable USB communication."
        )

    # Check if the Apple NCM USB network driver is working (required for iOS 17+)
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-PnpDevice | Where-Object { $_.FriendlyName -eq 'Apple Mobile Device Ethernet' } "
             "| Select-Object -ExpandProperty Status"],
            capture_output=True, text=True, timeout=8
        )
        status = result.stdout.strip()
        if status == "Unknown" or status == "Error":
            issues.append(
                "Apple USB network driver (NCM) is not installed correctly.\n"
                "This is required for iOS 17+ location spoofing.\n"
                "Fix: Install 'Apple Devices' from the Microsoft Store (search 'Apple Devices' by Apple Inc.).\n"
                "After installing, reconnect your iPhone."
            )
        elif status == "":
            # Adapter not present at all — may be fine if no iOS 17+ device connected
            pass
    except Exception:
        pass

    try:
        import pymobiledevice3  # noqa: F401
    except ImportError:
        issues.append("pymobiledevice3 not installed. Run: pip install pymobiledevice3")

    return issues


class DeviceManager(QObject):
    device_connected = pyqtSignal(dict)      # {"name", "udid", "ios_version", "model"}
    device_disconnected = pyqtSignal()
    location_result = pyqtSignal(bool, str)  # (success, message)
    error = pyqtSignal(str)
    tunneld_needed = pyqtSignal()            # emitted when iOS 17+ tunneld must start

    def __init__(self):
        super().__init__()
        self._lockdown = None
        self._last_udid: Optional[str] = None
        self._ios_major: int = 0
        self._scanning = False

        self._scan_timer = QTimer()
        self._scan_timer.timeout.connect(self._scan)
        self._scan_timer.start(3000)

    # ── Scanning ─────────────────────────────────────────────────────────────

    def _scan(self):
        if self._scanning:
            return
        self._scanning = True
        threading.Thread(target=self._do_scan, daemon=True).start()

    def _do_scan(self):
        try:
            asyncio.run(self._async_scan())
        except Exception as e:
            self._lockdown = None
            self._last_udid = None
            msg = str(e).lower()

            if "password" in msg or "passcode" in msg:
                self.error.emit("Unlock your iPhone and enter your passcode")
            elif "trust" in msg or "pair" in msg:
                self.error.emit("Tap 'Trust' on your iPhone when prompted")
            elif "connectionfailed" in msg.replace(" ", "") or "usbmux" in msg or "mux" in msg:
                self.error.emit("__USBMUX_FAILED__")
            elif "device" in msg and "not found" in msg:
                self.device_disconnected.emit()
            else:
                self.device_disconnected.emit()
        finally:
            self._scanning = False

    async def _async_scan(self):
        from pymobiledevice3.usbmux import list_devices
        from pymobiledevice3.lockdown import create_using_usbmux

        devices = await list_devices()
        if not devices:
            if self._lockdown is not None or self._last_udid is not None:
                self._lockdown = None
                self._last_udid = None
                self._ios_major = 0
                self.device_disconnected.emit()
            return

        serial = devices[0].serial
        if serial == self._last_udid and self._lockdown is not None:
            return

        lockdown = await create_using_usbmux(serial=serial)

        self._lockdown = lockdown
        self._last_udid = serial
        self._ios_major = int(lockdown.product_version.split(".")[0])

        self.device_connected.emit({
            "name": lockdown.display_name or "iPhone",
            "udid": lockdown.udid,
            "ios_version": lockdown.product_version,
            "model": lockdown.product_type,
        })

    # ── Location control ──────────────────────────────────────────────────────

    def set_location(self, lat: float, lng: float):
        if not self._lockdown:
            self.location_result.emit(False, "No device connected")
            return
        threading.Thread(
            target=self._do_set_location, args=(lat, lng), daemon=True
        ).start()

    def _do_set_location(self, lat: float, lng: float):
        if self._ios_major >= 17:
            self._set_location_ios17(lat, lng)
        else:
            self._set_location_legacy(lat, lng)

    # ── iOS < 17: direct DVT over lockdown ────────────────────────────────────

    def _set_location_legacy(self, lat: float, lng: float):
        try:
            asyncio.run(self._async_set_via_lockdown(lat, lng))
            self.location_result.emit(True, f"Location set to {lat:.6f}, {lng:.6f}")
        except Exception as e:
            self._cli_set_location(lat, lng, str(e))

    async def _async_set_via_lockdown(self, lat: float, lng: float):
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

        async with DvtProvider(self._lockdown) as dvt, \
                LocationSimulation(dvt) as loc:
            await loc.set(lat, lng)

    # ── iOS 17+: tunneld → RSD → DVT ─────────────────────────────────────────

    def _set_location_ios17(self, lat: float, lng: float):
        from core import tunneld_manager

        # Start tunneld if not running (blocks until ready or timeout)
        if not tunneld_manager.is_running():
            self.location_result.emit(True, "Starting admin tunnel for iOS 17+…")
            ok = tunneld_manager.start(wait_seconds=20)
            if not ok:
                self.location_result.emit(
                    False,
                    "Could not start tunnel.\n"
                    "Run as admin: python -m pymobiledevice3 remote tunneld"
                )
                return

        try:
            asyncio.run(self._async_set_via_tunneld(lat, lng))
            self.location_result.emit(True, f"Location set to {lat:.6f}, {lng:.6f}")
        except Exception as e:
            self.location_result.emit(False, f"Failed: {e}")

    async def _async_set_via_tunneld(self, lat: float, lng: float):
        from pymobiledevice3.tunneld.api import get_tunneld_device_by_udid
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
        from core.tunneld_manager import TUNNELD_HOST, TUNNELD_PORT

        rsd = await get_tunneld_device_by_udid(
            self._lockdown.udid, (TUNNELD_HOST, TUNNELD_PORT)
        )
        if rsd is None:
            raise RuntimeError("Device not found in tunneld — is iPhone unlocked?")

        async with DvtProvider(rsd) as dvt, LocationSimulation(dvt) as loc:
            await loc.set(lat, lng)

    # ── Clear location ────────────────────────────────────────────────────────

    def clear_location(self):
        threading.Thread(target=self._do_clear_location, daemon=True).start()

    def _do_clear_location(self):
        if self._ios_major >= 17:
            self._clear_location_ios17()
        else:
            self._clear_location_legacy()

    def _clear_location_legacy(self):
        cleared = False
        if self._lockdown:
            try:
                asyncio.run(self._async_clear_via_lockdown())
                cleared = True
            except Exception:
                pass
        if not cleared:
            try:
                result = subprocess.run(
                    ["python", "-m", "pymobiledevice3", "developer", "dvt",
                     "simulate-location", "clear"],
                    capture_output=True, text=True, timeout=15
                )
                cleared = result.returncode == 0
            except Exception:
                pass
        if cleared:
            self.location_result.emit(True, "Location restored to real GPS")
        else:
            self.location_result.emit(False, "Could not restore GPS")

    async def _async_clear_via_lockdown(self):
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

        async with DvtProvider(self._lockdown) as dvt, \
                LocationSimulation(dvt) as loc:
            await loc.clear()

    def _clear_location_ios17(self):
        from core import tunneld_manager

        if not tunneld_manager.is_running():
            self.location_result.emit(False, "Tunnel not running — reconnect device")
            return
        try:
            asyncio.run(self._async_clear_via_tunneld())
            self.location_result.emit(True, "Location restored to real GPS")
        except Exception as e:
            self.location_result.emit(False, f"Failed to clear: {e}")

    async def _async_clear_via_tunneld(self):
        from pymobiledevice3.tunneld.api import get_tunneld_device_by_udid
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
        from core.tunneld_manager import TUNNELD_HOST, TUNNELD_PORT

        rsd = await get_tunneld_device_by_udid(
            self._lockdown.udid, (TUNNELD_HOST, TUNNELD_PORT)
        )
        if rsd is None:
            raise RuntimeError("Device not found in tunneld")

        async with DvtProvider(rsd) as dvt, LocationSimulation(dvt) as loc:
            await loc.clear()

    # ── CLI fallback ──────────────────────────────────────────────────────────

    def _cli_set_location(self, lat: float, lng: float, original_error: str):
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
                    self.location_result.emit(
                        False,
                        "Enable Developer Mode: Settings → Privacy & Security → Developer Mode"
                    )
                else:
                    self.location_result.emit(False, f"Failed: {stderr or original_error}")
        except subprocess.TimeoutExpired:
            self.location_result.emit(False, "Timeout — is iPhone unlocked?")
        except FileNotFoundError:
            self.location_result.emit(False, f"Could not set location: {original_error}")
