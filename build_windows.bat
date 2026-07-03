@echo off
chcp 65001 >nul 2>&1
title IPQuery Build
echo.
echo ==========================================
echo   IPQuery Windows Build Script
echo ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)
echo [1/5] Python OK

:: Install PyInstaller
echo [2/5] Check PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)
echo PyInstaller OK

:: Install deps
echo [3/5] Install dependencies...
pip install PyQt6 geoip2 dnspython requests qqwry-py3

:: Generate icon
echo [4/5] Generate icon...
if exist "generate_ico.py" (
    python generate_ico.py .
) else (
    echo [WARNING] generate_ico.py not found, skipping icon
)

:: Build
echo [5/5] Building EXE...
set SCRIPT=ip_lookup_gui.py
set NAME=IPQuery

if not exist "%SCRIPT%" (
    echo [ERROR] %SCRIPT% not found
    pause
    exit /b 1
)

if exist "ipquery.ico" (
    python -m PyInstaller --onefile --windowed --name "%NAME%" --icon="ipquery.ico" --clean "%SCRIPT%"
) else (
    python -m PyInstaller --onefile --windowed --name "%NAME%" --clean "%SCRIPT%"
)

if errorlevel 1 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   DONE: dist\%NAME%.exe
echo ==========================================
echo.
echo Usage:
echo   1. Copy dist\%NAME%.exe to any folder
echo   2. First run: click "Update DB" to download
echo      GeoLite2-Country/City/ASN + qqwry.dat
echo   3. Double-click %NAME%.exe to use
echo.
pause
