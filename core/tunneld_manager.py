"""
Manages the pymobiledevice3 tunneld process for iOS 17+ devices.
tunneld must run as administrator on Windows — this module handles elevation.
"""
import ctypes
import subprocess
import sys
import time
import threading
import os

import requests


TUNNELD_HOST = "127.0.0.1"
TUNNELD_PORT = 49151
TUNNELD_URL = f"http://{TUNNELD_HOST}:{TUNNELD_PORT}"

_tunneld_proc = None          # Popen handle when WE started it (admin path)
_lock = threading.Lock()


def is_running() -> bool:
    """Return True if tunneld is accepting connections on port 49151."""
    try:
        r = requests.get(TUNNELD_URL, timeout=1)
        return r.status_code == 200
    except Exception:
        return False


def is_admin() -> bool:
    """Return True if the current process has admin rights."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def start(wait_seconds: int = 15) -> bool:
    """
    Ensure tunneld is running. Returns True when ready, False on failure.

    - If already running: returns True immediately.
    - If we're admin: starts tunneld directly in background.
    - If not admin: triggers UAC elevation prompt to start it.
    """
    global _tunneld_proc

    with _lock:
        if is_running():
            return True

        if is_admin():
            # We're already admin — start directly
            _tunneld_proc = subprocess.Popen(
                [sys.executable, "-m", "pymobiledevice3", "remote", "tunneld"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            # Trigger UAC elevation — ShellExecuteW with "runas"
            # sys.executable is the file, "-m ..." are the parameters (separate args)
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable,
                "-m pymobiledevice3 remote tunneld",
                None, 1  # SW_SHOWNORMAL — visible console so user can close it later
            )
            if ret <= 32:
                # User denied UAC or error
                return False

        # Poll until tunneld is ready
        deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline:
            time.sleep(0.5)
            if is_running():
                return True

        return False


def stop():
    """Terminate tunneld if we started it."""
    global _tunneld_proc
    with _lock:
        if _tunneld_proc is not None:
            try:
                _tunneld_proc.terminate()
            except Exception:
                pass
            _tunneld_proc = None


def get_rsd_for_udid(udid: str):
    """
    Connect to tunneld and return an RSD for the given device UDID.
    Returns the RemoteServiceDiscoveryService or None.
    """
    import asyncio

    async def _get():
        from pymobiledevice3.tunneld.api import get_tunneld_device_by_udid
        return await get_tunneld_device_by_udid(udid, (TUNNELD_HOST, TUNNELD_PORT))

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(_get())
