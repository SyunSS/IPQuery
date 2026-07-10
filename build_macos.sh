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
DMG_NAME="${NAME}"

if [ ! -f "$SCRIPT" ]; then
    echo "[ERROR] $SCRIPT not found. Run from script directory."
    exit 1
fi

# 1. Python check
echo "[1/6] Checking Python..."
python3 --version || { echo "[ERROR] Python3 not found"; exit 1; }

# 2. PyInstaller
echo "[2/6] Checking PyInstaller..."
python3 -c "import PyInstaller" 2>/dev/null || {
    echo "Installing PyInstaller..."
    pip3 install pyinstaller
}
echo "PyInstaller OK"

# 3. Dependencies
echo "[3/6] Installing dependencies..."
pip3 install PyQt6 geoip2 dnspython requests qqwry-py3

# 4. Generate .icns icon
echo "[4/6] Generating icon..."
if [ -f "$GEN_ICON" ]; then
    python3 "$GEN_ICON" "." 2>/dev/null
    echo "Icon: ${ICNS}"
else
    echo "[WARNING] generate_icns.py not found, skipping icon"
    ICNS=""
fi

# 5. Build .app bundle
echo "[5/6] Building .app bundle..."
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

# 6. Create DMG
echo "[6/6] Creating DMG..."
DMG_TMP="dist/.dmg_tmp"
rm -rf "$DMG_TMP" 2>/dev/null || true
mkdir -p "$DMG_TMP"
cp -R "dist/${APP}" "$DMG_TMP/"
ln -s /Applications "$DMG_TMP/Applications"

DMG_FILE="dist/${DMG_NAME}.dmg"
rm -f "$DMG_FILE" 2>/dev/null || true

hdiutil create \
    -volname "$DMG_NAME" \
    -srcfolder "$DMG_TMP" \
    -ov \
    -format UDZO \
    "$DMG_FILE"

rm -rf "$DMG_TMP"

echo ""
echo "=========================================="
echo "  DONE"
echo "=========================================="
echo ""
echo "  dist/${APP}      - macOS app bundle"
echo "  dist/${DMG_NAME}.dmg  - DMG installer"
echo ""
echo "Usage:"
echo "  Open dist/${DMG_NAME}.dmg"
echo "  Drag ${APP} to Applications"
echo "  Databases auto-download on first run to:"
echo "    ~/Library/Application Support/IPQuery/db/"
echo ""
