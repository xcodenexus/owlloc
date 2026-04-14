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
