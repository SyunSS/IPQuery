#!/usr/bin/env python3
"""Generate IPQuery icon .ico for Windows"""
import sys, os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPixmap

app = QApplication(sys.argv)

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "."

px = QPixmap(256, 256)
px.fill(Qt.GlobalColor.transparent)
p = QPainter(px)
p.setRenderHint(QPainter.RenderHint.Antialiasing)
p.setBrush(QColor("#3498db"))
p.setPen(Qt.PenStyle.NoPen)
p.drawEllipse(10, 10, 236, 236)
p.setBrush(QColor("#ffffff"))
p.drawEllipse(50, 50, 156, 156)
p.setFont(QFont("Arial", 56, QFont.Weight.Bold))
p.setPen(QColor("#2c3e50"))
p.drawText(QRectF(0, 70, 256, 100), Qt.AlignmentFlag.AlignCenter, "IPQ")
p.end()

path = os.path.join(OUT_DIR, "ipquery.ico")
px.save(path, "ICO")
print(f"Icon generated: {path}")
