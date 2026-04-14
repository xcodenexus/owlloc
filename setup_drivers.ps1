# OwlLoc Driver Setup — Run as Administrator
# Installs Apple NCM driver for iOS 17+ tunnel support

Write-Host ""
Write-Host "  OwlLoc Driver Setup" -ForegroundColor Cyan
Write-Host "  ===================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "  [ERROR] Must run as Administrator." -ForegroundColor Red
    Write-Host "  Right-click this script -> Run as administrator" -ForegroundColor Yellow
    pause
    exit 1
}

# 1. Find Apple Mobile Device Ethernet device
Write-Host "  [1/4] Detecting Apple Mobile Device Ethernet..." -ForegroundColor White
$device = Get-PnpDevice -ErrorAction SilentlyContinue | Where-Object { $_.FriendlyName -eq "Apple Mobile Device Ethernet" }
if (-not $device) {
    Write-Host "        Not found — plug in your iPhone first." -ForegroundColor Yellow
} else {
    Write-Host ("        Found: " + $device.FriendlyName + " | Status: " + $device.Status) -ForegroundColor Green
}

# 2. Find the driver INF in DriverStore
Write-Host "  [2/4] Locating netaapl64 driver..." -ForegroundColor White
$driverPath = Get-ChildItem "C:\Windows\System32\DriverStore\FileRepository" -Recurse -Filter "netaapl64.Inf" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName

if (-not $driverPath) {
    Write-Host "        Driver not found in DriverStore." -ForegroundColor Red
    Write-Host "        Open Apple Devices app and let it complete setup, then rerun this script." -ForegroundColor Yellow
} else {
    Write-Host ("        Found: " + $driverPath) -ForegroundColor Green

    # 3. Install/stage the driver
    Write-Host "  [3/4] Installing driver..." -ForegroundColor White
    $result = pnputil /add-driver $driverPath /install 2>&1
    Write-Host ("        " + ($result -join " | ")) -ForegroundColor Gray

    # 4. Apply to device if found
    if ($device) {
        Write-Host "  [4/4] Applying driver to device..." -ForegroundColor White
        try {
            # Disable and re-enable to force driver reload
            Disable-PnpDevice -InstanceId $device.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
            Enable-PnpDevice -InstanceId $device.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2

            $updated = Get-PnpDevice -InstanceId $device.InstanceId -ErrorAction SilentlyContinue
            Write-Host ("        Status: " + $updated.Status) -ForegroundColor $(if ($updated.Status -eq "OK") { "Green" } else { "Yellow" })
        } catch {
            Write-Host ("        " + $_.Exception.Message) -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [4/4] Skipped — reconnect iPhone and rerun to apply." -ForegroundColor Yellow
    }
}

Write-Host ""

# 5. Start tunneld
Write-Host "  [5/5] Starting iOS tunnel service..." -ForegroundColor White
$tunneldJob = Start-Job -ScriptBlock {
    & python -m pymobiledevice3 remote tunneld 2>&1
}
Start-Sleep -Seconds 6

# Check if tunneld is up
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:49151" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "        Tunnel running!" -ForegroundColor Green
} catch {
    Write-Host "        Tunnel not ready yet — may need NCM driver first." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Setup complete. You can now launch OwlLoc:" -ForegroundColor Cyan
Write-Host "  python main.py" -ForegroundColor White
Write-Host ""
Write-Host "  Keep this window open — the tunnel must stay running." -ForegroundColor Yellow
Write-Host ""

# Keep tunneld running in foreground
Write-Host "  Running tunnel (Ctrl+C to stop)..." -ForegroundColor Gray
& python -m pymobiledevice3 remote tunneld
