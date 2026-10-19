import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QFont, QPainterPath
from PySide6.QtCore import Qt, QRectF

def draw_icon(pix, p, name, color, size=64):
    pen = QPen(QColor(color))
    pen.setWidthF(size * 0.1)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    if name == "play":
        path = QPainterPath()
        path.moveTo(size*0.25, size*0.15)
        path.lineTo(size*0.85, size*0.5)
        path.lineTo(size*0.25, size*0.85)
        path.closeSubpath()
        p.fillPath(path, QColor(color))
    elif name == "pause":
        p.fillRect(QRectF(size*0.2, size*0.15, size*0.2, size*0.7), QColor(color))
        p.fillRect(QRectF(size*0.6, size*0.15, size*0.2, size*0.7), QColor(color))
    elif name == "prev":
        p.fillRect(QRectF(size*0.15, size*0.2, size*0.15, size*0.6), QColor(color))
        path = QPainterPath()
        path.moveTo(size*0.85, size*0.15)
        path.lineTo(size*0.35, size*0.5)
        path.lineTo(size*0.85, size*0.85)
        path.closeSubpath()
        p.fillPath(path, QColor(color))
    elif name == "next":
        p.fillRect(QRectF(size*0.7, size*0.2, size*0.15, size*0.6), QColor(color))
        path = QPainterPath()
        path.moveTo(size*0.15, size*0.15)
        path.lineTo(size*0.65, size*0.5)
        path.lineTo(size*0.15, size*0.85)
        path.closeSubpath()
        p.fillPath(path, QColor(color))
    elif name == "loop":
        p.drawArc(QRectF(size*0.15, size*0.25, size*0.7, size*0.5), 30*16, 300*16)
        p.drawLine(size*0.8, size*0.15, size*0.85, size*0.25)
        p.drawLine(size*0.85, size*0.25, size*0.75, size*0.3)
    elif name == "single":
        p.drawArc(QRectF(size*0.15, size*0.25, size*0.7, size*0.5), 30*16, 300*16)
        p.drawLine(size*0.8, size*0.15, size*0.85, size*0.25)
        p.drawLine(size*0.85, size*0.25, size*0.75, size*0.3)
        font = QFont("Arial", int(size*0.4))
        font.setBold(True)
        p.setFont(font)
        p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, "1")
    elif name == "shuffle":
        p.drawLine(size*0.15, size*0.25, size*0.85, size*0.75)
        p.drawLine(size*0.15, size*0.75, size*0.85, size*0.25)
        p.drawLine(size*0.75, size*0.25, size*0.85, size*0.25)
        p.drawLine(size*0.85, size*0.25, size*0.85, size*0.35)
    elif name == "volume":
        path = QPainterPath()
        path.moveTo(size*0.15, size*0.35)
        path.lineTo(size*0.35, size*0.35)
        path.lineTo(size*0.55, size*0.15)
        path.lineTo(size*0.55, size*0.85)
        path.lineTo(size*0.35, size*0.65)
        path.lineTo(size*0.15, size*0.65)
        path.closeSubpath()
        p.fillPath(path, QColor(color))
        p.drawArc(QRectF(size*0.5, size*0.3, size*0.3, size*0.4), -60*16, 120*16)
    elif name == "shrink":
        p.drawLine(size*0.2, size*0.2, size*0.45, size*0.45)
        p.drawLine(size*0.45, size*0.45, size*0.2, size*0.45)
        p.drawLine(size*0.45, size*0.45, size*0.45, size*0.2)
        p.drawLine(size*0.8, size*0.8, size*0.55, size*0.55)
        p.drawLine(size*0.55, size*0.55, size*0.8, size*0.55)
        p.drawLine(size*0.55, size*0.55, size*0.55, size*0.8)
    elif name == "more":
        p.setFont(QFont("Arial", int(size*0.5)))
        p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, "...")
    elif name == "folder":
        p.setFont(QFont("Segoe UI Emoji", int(size*0.6)))
        p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, "📁")
    elif name == "record":
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(30, 30, 30))
        p.drawEllipse(0, 0, size, size)
        p.setBrush(QColor(255, 192, 203))
        p.drawEllipse(size*0.2, size*0.2, size*0.6, size*0.6)
        p.setPen(QColor(30, 30, 30))
        font = QFont("Arial", int(size*0.18))
        font.setBold(True)
        p.setFont(font)
        p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, "MP3")

def generate_all_icons():
    app = QApplication.instance() or QApplication(sys.argv)
    
    # ================= 核心路径修改 =================
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 exe，定位到 exe 所在目录
        BASE_DIR = Path(sys.executable).parent
    else:
        # 如果是源码运行
        BASE_DIR = Path(__file__).parent
        
    icons_dir = BASE_DIR / "icons"
    # ================================================
    
    icons_dir.mkdir(exist_ok=True)
    
    names = ["play", "pause", "prev", "next", "loop", "single", "shuffle", "volume", "shrink", "more", "folder", "record"]
    for name in names:
        if name == "record":
            # 唱片图标只用一种（深色底+粉色）
            target_file = icons_dir / f"{name}.png"
            if not target_file.exists():
                size = 256
                pix = QPixmap(size, size)
                pix.fill(Qt.transparent)
                p = QPainter(pix)
                p.setRenderHint(QPainter.Antialiasing)
                draw_icon(pix, p, name, "#ffffff", size)
                p.end()
                pix.save(str(target_file))
            continue
            
        # 浅色图标 (白色)
        target_light = icons_dir / f"{name}.png"
        if not target_light.exists():
            size = 64
            pix = QPixmap(size, size)
            pix.fill(Qt.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.Antialiasing)
            draw_icon(pix, p, name, "#ffffff", size)
            p.end()
            pix.save(str(target_light))

        # 深色图标 (深灰)
        target_dark = icons_dir / f"{name}_dark.png"
        if not target_dark.exists():
            size = 64
            pix = QPixmap(size, size)
            pix.fill(Qt.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.Antialiasing)
            draw_icon(pix, p, name, "#333333", size)
            p.end()
            pix.save(str(target_dark))

if __name__ == "__main__":
    generate_all_icons()