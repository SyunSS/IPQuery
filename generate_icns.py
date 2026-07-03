#!/usr/bin/env python3
"""Generate IPQuery icon .icns for macOS"""
import sys, os, subprocess, shutil
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPixmap

app = QApplication(sys.argv)

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "."
ICONSET = os.path.join(OUT_DIR, "IPQuery.iconset")
os.makedirs(ICONSET, exist_ok=True)

SIZES = [16, 32, 64, 128, 256, 512]

def draw_icon(size):
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    m = size * 0.04
    r = size * 0.95
    p.setBrush(QColor("#3498db"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(int(m), int(m), int(r), int(r))
    inner = size * 0.7
    offset = int((size - inner) / 2)
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(offset, offset, int(inner), int(inner))
    font_size = int(size * 0.22)
    p.setFont(QFont("Arial", font_size, QFont.Weight.Bold))
    p.setPen(QColor("#2c3e50"))
    p.drawText(QRectF(0, size * 0.28, size, size * 0.42), Qt.AlignmentFlag.AlignCenter, "IPQ")
    p.end()
    return px

for s in SIZES:
    px = draw_icon(s)
    px.save(os.path.join(ICONSET, f"icon_{s}x{s}.png"), "PNG")
    # @2x retina
    px2 = draw_icon(s * 2)
    px2.save(os.path.join(ICONSET, f"icon_{s}x{s}@2x.png"), "PNG")

subprocess.run(["iconutil", "-c", "icns", ICONSET], check=True)
print(f"Icon generated: {ICONSET[:-8]}.icns")
shutil.rmtree(ICONSET)
