from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap
from PyQt6.QtCore import Qt, QRectF
import sys
from PyQt6.QtWidgets import QApplication

def generate_icon():
    app = QApplication(sys.argv)
    size = 512
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Colors (Catppuccin Mocha)
    base = QColor("#1e1e2e")
    blue = QColor("#89b4fa")
    red = QColor("#f38ba8")
    
    # Draw background rounded square
    painter.setBrush(QBrush(base))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(20, 20, size-40, size-40), 100, 100)
    
    # Draw outer glow/border
    pen = QPen(blue)
    pen.setWidth(15)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(QRectF(20, 20, size-40, size-40), 100, 100)
    
    # Draw crosshair
    pen_red = QPen(red)
    pen_red.setWidth(20)
    pen_red.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen_red)
    
    center = size / 2
    length = 120
    gap = 40
    
    # Vertical lines
    painter.drawLine(int(center), int(center - length), int(center), int(center - gap))
    painter.drawLine(int(center), int(center + gap), int(center), int(center + length))
    
    # Horizontal lines
    painter.drawLine(int(center - length), int(center), int(center - gap), int(center))
    painter.drawLine(int(center + gap), int(center), int(center + length), int(center))
    
    # Center dot
    painter.setBrush(QBrush(red))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(int(center - 25), int(center - 25), 50, 50)
    
    painter.end()
    pixmap.save("icon.png")
    print("Icon generated as icon.png")

if __name__ == "__main__":
    generate_icon()
