#!/bin/bash
set -e

echo ""
echo "=========================================="
echo "  IPQuery macOS Build Script"
echo "=========================================="
echo ""

SCRIPT="ip_lookup_gui.py"
GEN_ICON="generate_icns.py"
NAME="IPQuery"
APP="${NAME}.app"
ICNS="${NAME}.icns"

if [ ! -f "$SCRIPT" ]; then
    echo "[ERROR] $SCRIPT not found. Run from script directory."
    exit 1
fi

# 1. Python check
echo "[1/5] Checking Python..."
python3 --version || { echo "[ERROR] Python3 not found"; exit 1; }

# 2. PyInstaller
echo "[2/5] Checking PyInstaller..."
python3 -c "import PyInstaller" 2>/dev/null || {
    echo "Installing PyInstaller..."
    pip3 install pyinstaller
}
echo "PyInstaller OK"

# 3. Dependencies
echo "[3/5] Installing dependencies..."
pip3 install PyQt6 geoip2 dnspython requests qqwry-py3

# 4. Generate .icns icon
echo "[4/5] Generating icon..."
if [ -f "$GEN_ICON" ]; then
    python3 "$GEN_ICON" "." 2>/dev/null
    echo "Icon: ${ICNS}"
else
    echo "[WARNING] generate_icns.py not found, skipping icon"
    ICNS=""
fi

# 5. Build .app bundle (onedir = proper macOS app, no dock duplication)
echo "[5/5] Building .app bundle..."
ICON_ARG=""
if [ -n "$ICNS" ] && [ -f "$ICNS" ]; then
    ICON_ARG="--icon=${ICNS}"
fi

python3 -m PyInstaller \
    --onedir \
    --windowed \
    --name "$NAME" \
    --osx-bundle-identifier "com.ipquery.app" \
    $ICON_ARG \
    --clean \
    "$SCRIPT"

echo ""
echo "=========================================="
echo "  DONE: dist/${APP}"
echo "=========================================="
echo ""
echo "Output:"
echo "  dist/${APP}                     - macOS app bundle"
echo ""
echo "File locations when running as .app:"
echo "  Database (default):"
echo "    ~/Library/Application Support/IPQuery/db/"
echo "  Or put db files next to .app (same parent dir)"
echo ""
echo "Usage:"
echo "  1. Copy dist/${APP} to /Applications"
echo "  2. Click 'Update DB' to download databases"
echo "  3. Double-click ${APP} to launch"
echo ""
