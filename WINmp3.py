import sys, time, json, os, random, subprocess, importlib.util
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
                               QLabel, QPushButton, QSlider, QFileDialog, QGraphicsOpacityEffect,
                               QMenu, QListWidgetItem, QDialog, QInputDialog, QColorDialog, QMessageBox)
from PySide6.QtCore import (QTimer, Qt, QPropertyAnimation, QEasingCurve, QPoint, QPointF, QUrl, QSize, QRectF, QEvent)
from PySide6.QtGui import (QCursor, QColor, QPainter, QFont, QIcon, QPixmap, QPen, QGuiApplication,
                           QLinearGradient, QBrush, QDesktopServices)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

ICONS_DIR = BASE_DIR / "icons"
STYLES_DIR = BASE_DIR / "styles"
DATA_DIR = BASE_DIR / "data"
MODS_DIR = BASE_DIR / "mods"

for d in [ICONS_DIR, STYLES_DIR, DATA_DIR, MODS_DIR]:
    d.mkdir(exist_ok=True)

if not list(ICONS_DIR.glob("*.png")):
    try:
        if getattr(sys, 'frozen', False):
            icon_exe = BASE_DIR / "icon_gen.exe"
            if icon_exe.exists():
                subprocess.run([str(icon_exe)], creationflags=0x08000000, cwd=str(BASE_DIR))
        else:
            icon_py = BASE_DIR / "icon_gen.py"
            if icon_py.exists():
                subprocess.run([sys.executable, str(icon_py)], creationflags=0x08000000)
    except Exception as e:
        print(f"启动时图标生成失败: {e}")

CONFIG_PATH = DATA_DIR / "config.json"
LIST_PATH = DATA_DIR / "list.json"

DEFAULT_CONFIG = {"last_folder": "", "volume": 50, "play_mode": "loop", "last_index": 0, "style": "深色.json"}

def ensure_styles():
    styles = {
        "深色.json": {"name": "深色", "order": 1, "main_bg": "30,30,30,235", "main_border_radius": 10, "menu_bg": "40,40,40,245", "menu_border_radius": 8, "text_color": "#ffffff", "highlight_color": "#00bfff"},
        "浅色.json": {"name": "浅色", "order": 2, "main_bg": "240,240,240,240", "main_border_radius": 12, "menu_bg": "250,250,250,245", "menu_border_radius": 8, "text_color": "#333333", "highlight_color": "#0078d7"},
        "渐变.json": {"name": "渐变", "order": 3, "main_bg": "20,20,40,240 | 80,20,80,220", "main_border_radius": 10, "menu_bg": "40,20,60,245 | 60,40,80,220", "menu_border_radius": 8, "text_color": "#00ffcc", "highlight_color": "#ff00ff"}
    }
    for filename, default_data in styles.items():
        target = STYLES_DIR / filename
        if not target.exists():
            with open(target, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)

ensure_styles()

def load_json(path, default):
    if not path.exists():
        save_json(path, default)
        return default.copy()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default.copy()

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
style_mapping = {"default.json": "深色.json", "clean_light.json": "浅色.json", "cyberpunk.json": "渐变.json"}
if cfg.get("style") in style_mapping:
    cfg["style"] = style_mapping[cfg["style"]]
    save_json(CONFIG_PATH, cfg)

playlists = load_json(LIST_PATH, [])

def get_style():
    p = STYLES_DIR / cfg.get("style", "深色.json")
    return load_json(p, {"main_bg": "30,30,30,235", "text_color": "#ffffff", "highlight_color": "#00bfff", "menu_bg": "40,40,40,245"})

style = get_style()

def parse_color(rgba_str, default=QColor(30, 30, 30, 235)):
    try:
        if isinstance(rgba_str, str):
            parts = rgba_str.split(",")
            if len(parts) == 4: return QColor(int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))
            elif len(parts) == 3: return QColor(int(parts[0]), int(parts[1]), int(parts[2]))
    except: pass
    return default

def get_bg_brush(color_str, rect):
    if isinstance(color_str, str) and "|" in color_str:
        parts = color_str.split("|")
        c1 = parse_color(parts[0].strip())
        c2 = parse_color(parts[1].strip())
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0, c1); grad.setColorAt(1, c2)
        return QBrush(grad)
    return QBrush(parse_color(color_str))

def get_qss_color(rgba_str, default="rgba(40, 40, 40, 0.9)"):
    if "|" in rgba_str: rgba_str = rgba_str.split("|")[0].strip()
    try:
        parts = rgba_str.split(",")
        if len(parts) == 4: return f"rgba({parts[0]}, {parts[1]}, {parts[2]}, {int(parts[3])/255.0})"
        elif len(parts) == 3: return f"rgb({parts[0]}, {parts[1]}, {parts[2]})"
    except: pass
    return default

def get_icon(name):
    is_dark_icon = False
    try:
        color = QColor(style.get('text_color', '#ffffff'))
        if color.lightness() < 128: is_dark_icon = True
    except: pass
    suffix = "_dark" if is_dark_icon else ""
    if name == "record": suffix = ""
    return QIcon(str(ICONS_DIR / f"{name}{suffix}.png"))

class VerticalVolumeSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)
        self.setRange(0, 100)
        self.setFixedWidth(30)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h, track_width = self.width(), self.height(), 6
        track_x = (w - track_width) // 2
        track_rect = QRectF(track_x, 10, track_width, h - 20)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(68, 68, 68))
        painter.drawRoundedRect(track_rect, 3, 3)

        ratio = (self.value() - self.minimum()) / (self.maximum() - self.minimum())
        handle_y = track_rect.bottom() - ratio * track_rect.height()

        if ratio > 0:
            fill_rect = QRectF(track_x, handle_y, track_width, track_rect.bottom() - handle_y)
            painter.setBrush(QColor(style.get('highlight_color', '#00bfff')))
            painter.drawRoundedRect(fill_rect, 3, 3)

        handle_radius = 7
        handle_center = QPointF(w / 2, handle_y)
        painter.setBrush(QColor(255, 255, 255))
        pen = QPen(QColor(style.get('highlight_color', '#00bfff')))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(handle_center, handle_radius, handle_radius)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.update_value_from_pos(event.position())
            self.setSliderDown(True)
        super().mousePressEvent(event)
    def mouseMoveEvent(self, event):
        if self.isSliderDown(): self.update_value_from_pos(event.position())
        super().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton: self.setSliderDown(False)
        super().mouseReleaseEvent(event)
    def update_value_from_pos(self, pos):
        h, track_top, track_bottom = self.height(), 10, self.height() - 10
        y = max(track_top, min(pos.y(), track_bottom))
        ratio = (track_bottom - y) / (track_bottom - track_top)
        self.setValue(self.minimum() + int(ratio * (self.maximum() - self.minimum())))

class ClickMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        menu_bg = get_qss_color(style.get('menu_bg', '40,40,40,245'))
        self.setStyleSheet(f"""
            QMenu {{ background-color: {menu_bg}; color: {style.get('text_color', '#fff')}; border: 1px solid #555; border-radius: 4px; padding: 5px; }}
            QMenu::item {{ padding: 6px 20px; border-radius: 2px; }}
            QMenu::item:selected {{ background-color: {style.get('highlight_color', '#00bfff')}; color: black; }}
        """)

class BasePopup(QDialog):
    def __init__(self, main_win, parent_popup=None, popup_type="lvl2", direction="left"):
        super().__init__(parent_popup if popup_type == "lvl3" else main_win)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.main_win = main_win; self.popup_type = popup_type; self.direction = direction

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(get_bg_brush(style.get("menu_bg", "40,40,40,245"), self.rect()))
        painter.setPen(Qt.NoPen); painter.drawRoundedRect(self.rect(), style.get("menu_border_radius", 8), style.get("menu_border_radius", 8))

    def update_style(self): self.update()

    def calculate_pos(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        main_rect = self.main_win.geometry()
        if self.popup_type == "lvl2":
            x = main_rect.x() if self.direction == "left" else main_rect.x() + main_rect.width() - self.width()
            y = main_rect.y() + main_rect.height() + 5 if self.direction == "left" else main_rect.y() - self.height() - 5
            if y + self.height() > screen.bottom(): y = main_rect.y() - self.height() - 5
            if y < screen.top(): y = main_rect.y() + main_rect.height() + 5
            self.move(x, y)
        elif self.popup_type == "lvl3":
            parent_pop = self.parent()
            x = parent_pop.x() - self.width() - 5 if self.direction == "left" else parent_pop.x() + parent_pop.width() + 5
            y = parent_pop.y()
            if x < screen.left() or x + self.width() > screen.right():
                x = parent_pop.x() if self.direction == "left" else parent_pop.x() + parent_pop.width() - self.width()
                y = parent_pop.y() + parent_pop.height() + 5
            self.move(x, y)
        elif self.popup_type == "toast":
            self.move(main_rect.x() + (main_rect.width() - self.width()) // 2, main_rect.y() + main_rect.height() + 10)

        x, y = self.pos().x(), self.pos().y()
        if x + self.width() > screen.right(): x = screen.right() - self.width() - 5
        if y + self.height() > screen.bottom(): y = screen.bottom() - self.height() - 5
        if x < screen.left() + 5: x = screen.left() + 5
        if y < screen.top() + 5: y = screen.top() + 5
        self.move(x, y)

class ToastWindow(BasePopup):
    _instances = []
    def __init__(self, message, main_win):
        super().__init__(main_win, popup_type="toast")
        self.setFixedSize(200, 40)
        layout = QVBoxLayout(self)
        self.label = QLabel(message, self); self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label); self.update_style()

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect); self.opacity_effect.setOpacity(1.0)
        self.calculate_pos(); self.show()
        self.timer = QTimer(self); self.timer.timeout.connect(self.fade_out); self.timer.start(1000)
        ToastWindow._instances.append(self)

    def update_style(self):
        self.label.setStyleSheet(f"color: {style.get('text_color', '#fff')}; font-size: 12px;")
        super().update_style()

    def fade_out(self):
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity"); self.anim.setDuration(300)
        self.anim.setStartValue(1.0); self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.close); self.anim.start()

    def closeEvent(self, event):
        if self in ToastWindow._instances: ToastWindow._instances.remove(self)

class PlaylistDialog(BasePopup):
    def __init__(self, main_win):
        super().__init__(main_win, popup_type="lvl2", direction="left")
        self.setFixedWidth(200)
        layout = QVBoxLayout(self); layout.setContentsMargins(5, 5, 5, 5)
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.list_widget)
        self.btn_add = QPushButton("➕ 添加新文件夹"); self.btn_add.clicked.connect(self.add_new)
        layout.addWidget(self.btn_add)
        self.refresh_list(); self.update_style(); self.calculate_pos()

    def update_style(self):
        self.list_widget.setStyleSheet(f"QListWidget {{ background: transparent; border: none; color: {style.get('text_color', '#fff')}; }} QListWidget::item {{ padding: 8px; border-radius: 4px; }} QListWidget::item:selected {{ background: {style.get('highlight_color', '#00bfff')}; color: black; }}")
        self.btn_add.setStyleSheet(f"QPushButton {{ background: transparent; color: {style.get('text_color', '#fff')}; padding: 8px; text-align: left; }} QPushButton:hover {{ background: rgba(255,255,255,0.1); border-radius: 4px; }}")
        super().update_style()

    def refresh_list(self):
        self.list_widget.clear()
        for pl in playlists:
            item = QListWidgetItem(pl["name"])
            self.list_widget.addItem(item)

    def on_item_clicked(self, item):
        idx = self.list_widget.row(item)
        if 0 <= idx < len(playlists):
            self.close()
            self.main_win.load_playlist_entry(playlists[idx])

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item: return
        idx = self.list_widget.row(item)
        menu = ClickMenu(self)
        act_rename = menu.addAction("重命名"); act_delete = menu.addAction("删除")
        action = menu.exec(self.list_widget.mapToGlobal(pos))
        if action == act_rename:
            dialog = QInputDialog(self)
            dialog.setWindowTitle("重命名")
            dialog.setLabelText("新名称:")
            dialog.setTextValue(playlists[idx]["name"])
            dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
            if dialog.exec() == QDialog.Accepted:
                new_name = dialog.textValue()
                if new_name.strip():
                    playlists[idx]["name"] = new_name.strip()
                    save_json(LIST_PATH, playlists); self.refresh_list()
        elif action == act_delete:
            playlists.pop(idx); save_json(LIST_PATH, playlists); self.refresh_list()

    def add_new(self):
        self.main_win.is_dialog_open = True
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择音乐文件 (自动导入所在文件夹)", "", 
            "Audio Files (*.mp3 *.wav *.flac *.m4a *.aac *.ogg);;All Files (*)"
        )
        self.main_win.is_dialog_open = False
        
        if not file_path: return
        
        folder = str(Path(file_path).parent)
        
        try:
            self.close()
        except RuntimeError:
            pass
            
        base_name = Path(folder).name or "未命名"
        name = base_name; counter = 1
        while any(pl["name"] == name for pl in playlists):
            name = f"{base_name}{counter}"; counter += 1
            
        playlists.append({"name": name, "path": folder})
        save_json(LIST_PATH, playlists)
        self.main_win.load_folder(folder)

class VolumeDialog(BasePopup):
    def __init__(self, main_win):
        super().__init__(main_win, popup_type="lvl2", direction="right")
        self.setFixedSize(40, 160)
        layout = QVBoxLayout(self); layout.setContentsMargins(5, 10, 5, 10)
        self.slider = VerticalVolumeSlider(self)
        self.slider.setValue(cfg["volume"]); self.slider.valueChanged.connect(self.on_vol_change)
        layout.addWidget(self.slider); self.calculate_pos()

    def on_vol_change(self, val):
        self.main_win.current_vol = val; self.main_win.audio_output.setVolume(min(1.0, val / 100.0))
        cfg["volume"] = val; save_json(CONFIG_PATH, cfg); ToastWindow(f"音量: {val}%", self.main_win)

class MoreDialog(BasePopup):
    def __init__(self, main_win):
        super().__init__(main_win, popup_type="lvl2", direction="left")
        self.setFixedSize(120, 150)
        layout = QVBoxLayout(self); layout.setContentsMargins(5, 5, 5, 5)

        self.btn_style = QPushButton("修改风格"); self.btn_style.clicked.connect(self.main_win.show_style_dialog)
        self.btn_mods = QPushButton("Mods"); self.btn_mods.clicked.connect(self.main_win.show_mods_dialog)
        self.btn_support = QPushButton("支持我"); self.btn_support.clicked.connect(self.open_bili)
        self.btn_exit = QPushButton("退出程序"); self.btn_exit.clicked.connect(lambda: os._exit(0))

        layout.addWidget(self.btn_style)
        layout.addWidget(self.btn_mods)
        layout.addWidget(self.btn_support)
        layout.addWidget(self.btn_exit)
        
        self.update_style(); self.calculate_pos()

    def open_bili(self):
        QDesktopServices.openUrl(QUrl("https://space.bilibili.com/1992976149"))
        self.main_win.close_all_popups()

    def update_style(self):
        s = f"QPushButton {{ background: transparent; color: {style.get('text_color', '#fff')}; padding: 8px; text-align: left; }} QPushButton:hover {{ background: rgba(255,255,255,0.1); border-radius: 4px; }}"
        self.btn_style.setStyleSheet(s)
        self.btn_mods.setStyleSheet(s)
        self.btn_support.setStyleSheet(s)
        self.btn_exit.setStyleSheet(s)
        super().update_style()

class StyleDialog(BasePopup):
    PROTECTED_STYLES = ["深色.json", "浅色.json", "渐变.json"]

    def __init__(self, main_win, parent_popup):
        super().__init__(main_win, parent_popup, popup_type="lvl3", direction=parent_popup.direction)
        self.setFixedSize(250, 300)
        layout = QVBoxLayout(self); layout.setContentsMargins(10, 10, 10, 10)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.apply_style)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.list_widget)
        self.refresh_list(); self.update_style(); self.calculate_pos()

    def update_style(self):
        self.list_widget.setStyleSheet(f"QListWidget {{ background: transparent; border: none; color: {style.get('text_color', '#fff')}; }} QListWidget::item {{ padding: 10px; border-radius: 4px; }} QListWidget::item:selected {{ background: {style.get('highlight_color', '#00bfff')}; color: black; }}")
        super().update_style()

    def refresh_list(self):
        self.list_widget.clear()
        style_items = []
        for f in STYLES_DIR.glob("*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    d = json.load(file); name = d.get("name", f.stem); order = d.get("order", 99)
                    item = QListWidgetItem(name); item.setData(Qt.UserRole, f.name)
                    style_items.append((order, item))
            except: pass
        style_items.sort(key=lambda x: x[0])
        for _, item in style_items: self.list_widget.addItem(item)

    def apply_style(self, item):
        style_file = item.data(Qt.UserRole)
        cfg["style"] = style_file; save_json(CONFIG_PATH, cfg)
        self.main_win.reload_style(); self.main_win.close_all_popups()
        ToastWindow("风格已热重载", self.main_win)

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item: return

        style_file = item.data(Qt.UserRole)
        is_protected = style_file in self.PROTECTED_STYLES

        menu = ClickMenu(self)
        act_delete = menu.addAction("删除风格")
        if is_protected: act_delete.setEnabled(False)

        action = menu.exec(self.list_widget.mapToGlobal(pos))

        if action == act_delete:
            if is_protected:
                ToastWindow("自带的风格不能删除哦", self.main_win)
                return

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("确认删除")
            msg_box.setText(f"真的要删除风格【{item.text()}】吗？")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.No)
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)

            if msg_box.exec() == QMessageBox.Yes:
                try:
                    if cfg.get("style") == style_file:
                        cfg["style"] = "深色.json"; save_json(CONFIG_PATH, cfg); self.main_win.reload_style()
                    file_path = STYLES_DIR / style_file
                    if file_path.exists(): file_path.unlink()
                    ToastWindow("风格已删除", self.main_win)
                    self.refresh_list()
                except Exception as e:
                    ToastWindow(f"删除失败: {e}", self.main_win)

class ModAPI:
    def __init__(self, main_win):
        self.main_win = main_win

    def toast(self, msg):
        ToastWindow(msg, self.main_win)

    def add_playlist(self, name, path, provider=None):
        entry = {"name": name, "path": path}
        if provider:
            entry["provider"] = provider
        if not any(p["name"] == name for p in playlists):
            playlists.append(entry)
            save_json(LIST_PATH, playlists)
            self.toast(f"已添加歌单: {name}")

    def refresh_style(self):
        self.main_win.reload_style()
        self.toast("已刷新界面风格")

    def play_network_tracks(self, tracks, name=None):
        self.main_win.load_network_tracks(tracks)
        if name:
            self.toast(f"已加载网络歌单: {name}")

    def add_style(self, name, style_dict):
        max_order = 0
        for f in STYLES_DIR.glob("*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    o = json.load(file).get("order", 0)
                    if o > max_order: max_order = o
            except: pass

        style_dict["name"] = name
        style_dict["order"] = max_order + 1
        file_path = STYLES_DIR / f"{name}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(style_dict, f, indent=2, ensure_ascii=False)
        self.toast(f"已生成新风格: {name}")

class ModsDialog(BasePopup):
    def __init__(self, main_win, parent_popup, loaded_mods):
        super().__init__(main_win, parent_popup, popup_type="lvl3", direction=parent_popup.direction)
        self.setFixedSize(250, 300)
        self.loaded_mods = loaded_mods

        layout = QVBoxLayout(self); layout.setContentsMargins(10, 10, 10, 10)
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.run_mod)
        layout.addWidget(self.list_widget)

        self.update_style(); self.calculate_pos(); self.refresh_list()

    def update_style(self):
        self.list_widget.setStyleSheet(f"QListWidget {{ background: transparent; border: none; color: {style.get('text_color', '#fff')}; }} QListWidget::item {{ padding: 10px; border-radius: 4px; }} QListWidget::item:selected {{ background: {style.get('highlight_color', '#00bfff')}; color: black; }}")
        super().update_style()

    def refresh_list(self):
        self.list_widget.clear()
        errors = getattr(self.main_win, 'mod_errors', [])
        if not self.loaded_mods and not errors:
            item = QListWidgetItem("无 Mod 加载"); item.setFlags(Qt.NoItemFlags)
            self.list_widget.addItem(item); return

        for mod_info in self.loaded_mods:
            item = QListWidgetItem(mod_info["name"])
            item.setToolTip(mod_info.get("desc", "无描述"))
            item.setData(Qt.UserRole, mod_info)
            self.list_widget.addItem(item)

        for err in errors:
            item = QListWidgetItem(f"⚠ {err}")
            item.setFlags(Qt.NoItemFlags)
            self.list_widget.addItem(item)

    def run_mod(self, item):
        mod_info = item.data(Qt.UserRole)
        if mod_info:
            self.main_win.close_all_popups()
            try:
                mod_info["run"](self.main_win.mod_api)
            except Exception as e:
                ToastWindow(f"Mod 运行出错: {e}", self.main_win)

class MusicPlayerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.is_minimized = False
        self.normal_w, self.normal_h, self.mini_size = 600, 90, 64

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.normal_w, self.normal_h)

        screen = QGuiApplication.primaryScreen().size()
        self.target_x, self.target_y = (screen.width() - self.normal_w) // 2, 15
        self.hidden_y = -self.normal_h - 10
        self.setGeometry(self.target_x, self.hidden_y, self.normal_w, self.normal_h)

        self.is_showing, self.is_animating, self.start_time = False, False, 0
        self.edge_state, self.drag_offset = "none", None
        self.lvl2_popup, self.lvl3_popup = None, None
        self.is_dialog_open = False

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.current_vol = cfg["volume"]
        self.audio_output.setVolume(min(1.0, self.current_vol / 100.0))
        self.player.setAudioOutput(self.audio_output)

        self.playlist, self.current_index = [], -1
        self.network_titles = {}
        self.mod_errors = []
        self.is_dragging_progress = False

        self.setWindowIcon(get_icon("record"))

        self.main_widget = QWidget(self)
        self.main_widget.setGeometry(0, 0, self.normal_w, self.normal_h)
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(15, 10, 15, 10)
        self.main_layout.setSpacing(5)

        self.init_ui()
        self.init_animations()
        self.init_signals()

        self.mod_api = ModAPI(self)
        self.loaded_mods = self.scan_and_load_mods()
        for err in self.mod_errors:
            print(f"Mod 加载失败: {err}")

        self.hover_timer = QTimer(self); self.hover_timer.timeout.connect(self.check_hover_state); self.hover_timer.start(100)
        self.hide_timer = QTimer(self); self.hide_timer.setSingleShot(True); self.hide_timer.timeout.connect(self.trigger_hide)
        self.auto_hide_timer = QTimer(self); self.auto_hide_timer.setSingleShot(True); self.auto_hide_timer.timeout.connect(self.trigger_hide)

        QApplication.instance().installEventFilter(self)

        QTimer.singleShot(100, self.startup_intro)
        self.restore_last_session()
        self.reload_style()

    def scan_and_load_mods(self):
        loaded = []
        self.mod_errors = []
        for mod_file in MODS_DIR.glob("*.py"):
            if mod_file.name.startswith("__"): continue
            try:
                module_name = mod_file.stem
                spec = importlib.util.spec_from_file_location(module_name, mod_file)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)

                if hasattr(mod, "NAME") and hasattr(mod, "run"):
                    loaded.append({
                        "name": getattr(mod, "NAME"),
                        "desc": getattr(mod, "DESCRIPTION", ""),
                        "run": getattr(mod, "run"),
                        "resolve_playlist": getattr(mod, "resolve_playlist", None),
                        "file": mod_file.name
                    })
                else:
                    self.mod_errors.append(f"{mod_file.name}: 缺少 NAME 或 run")
            except Exception as e:
                self.mod_errors.append(f"{mod_file.name}: {e}")
        return loaded

    def init_ui(self):
        self.top_layout = QHBoxLayout()
        self.btn_playlist = QPushButton(); self.btn_playlist.setFixedSize(28, 28); self.btn_playlist.clicked.connect(self.show_playlist)
        self.lbl_song = QLabel("请选择歌单"); self.lbl_song.setAlignment(Qt.AlignCenter)
        self.btn_shrink = QPushButton(); self.btn_shrink.setFixedSize(28, 28); self.btn_shrink.clicked.connect(self.toggle_minimize)

        self.top_layout.addWidget(self.btn_playlist); self.top_layout.addSpacing(10)
        self.top_layout.addWidget(self.lbl_song, 1); self.top_layout.addSpacing(10)
        self.top_layout.addWidget(self.btn_shrink)

        self.bottom_layout = QHBoxLayout()
        self.lbl_time = QLabel("00:00 / 00:00")
        self.slider_progress = QSlider(Qt.Horizontal); self.slider_progress.setRange(0, 1000)
        self.slider_progress.sliderPressed.connect(self.on_slider_press); self.slider_progress.sliderReleased.connect(self.on_slider_release)
        self.slider_progress.sliderMoved.connect(self.on_slider_move); self.slider_progress.wheelEvent = lambda e: e.ignore()

        self.btn_mode = QPushButton(); self.btn_mode.setFixedSize(28, 28); self.btn_mode.clicked.connect(self.toggle_mode)
        self.btn_prev = QPushButton(); self.btn_prev.setFixedSize(28, 28); self.btn_prev.clicked.connect(self.play_prev)
        self.btn_play = QPushButton(); self.btn_play.setFixedSize(28, 28); self.btn_play.clicked.connect(self.toggle_play)
        self.btn_next = QPushButton(); self.btn_next.setFixedSize(28, 28); self.btn_next.clicked.connect(self.play_next)
        self.btn_volume = QPushButton(); self.btn_volume.setFixedSize(28, 28); self.btn_volume.clicked.connect(self.show_volume_slider)
        self.btn_more = QPushButton(); self.btn_more.setFixedSize(28, 28); self.btn_more.clicked.connect(self.show_more_dialog)

        self.bottom_layout.addWidget(self.btn_more); self.bottom_layout.addWidget(self.lbl_time)
        self.bottom_layout.addWidget(self.slider_progress, 1); self.bottom_layout.addSpacing(10)
        self.bottom_layout.addWidget(self.btn_mode); self.bottom_layout.addWidget(self.btn_prev)
        self.bottom_layout.addWidget(self.btn_play); self.bottom_layout.addWidget(self.btn_next)
        self.bottom_layout.addWidget(self.btn_volume)

        self.main_layout.addLayout(self.top_layout); self.main_layout.addLayout(self.bottom_layout)

    def reload_style(self):
        global style
        style = get_style()
        btn_style = "QPushButton { background: transparent; border: none; } QPushButton:hover { background: rgba(255,255,255,0.15); border-radius: 4px; }"
        for btn in [self.btn_playlist, self.btn_shrink, self.btn_mode, self.btn_prev, self.btn_play, self.btn_next, self.btn_volume, self.btn_more]:
            btn.setStyleSheet(btn_style)

        self.lbl_song.setStyleSheet(f"color: {style.get('highlight_color', '#00bfff')}; font-size: 13px; font-weight: bold;")
        self.lbl_time.setStyleSheet(f"color: {style.get('text_color', '#aaaaaa')}; font-size: 11px;")
        self.slider_progress.setStyleSheet(f"QSlider::groove:horizontal {{ height: 4px; background: #444; border-radius: 2px; }} QSlider::handle:horizontal {{ background: {style.get('highlight_color', '#00bfff')}; width: 10px; margin: -3px 0; border-radius: 5px; }} QSlider::sub-page:horizontal {{ background: {style.get('highlight_color', '#00bfff')}; border-radius: 2px; }}")

        self.btn_playlist.setIcon(get_icon("folder")); self.btn_shrink.setIcon(get_icon("shrink"))
        self.btn_prev.setIcon(get_icon("prev")); self.btn_next.setIcon(get_icon("next"))
        self.btn_volume.setIcon(get_icon("volume")); self.btn_more.setIcon(get_icon("more"))
        self.update_mode_icon()

        self.btn_play.setIcon(get_icon("pause" if self.player.playbackState() == QMediaPlayer.PlayingState else "play"))
        for w in QApplication.topLevelWidgets():
            if isinstance(w, BasePopup): w.update_style()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing); painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.is_minimized:
            icon_path = ICONS_DIR / "record.png"
            if icon_path.exists():
                pix = QPixmap(str(icon_path)); painter.drawPixmap(0, 0, self.width(), self.height(), pix)
        else:
            painter.setBrush(get_bg_brush(style.get("main_bg", "30,30,30,235"), self.rect()))
            painter.setPen(Qt.NoPen); r = style.get("main_border_radius", 10); painter.drawRoundedRect(self.rect(), r, r)

    def toggle_minimize(self):
        if self.is_minimized:
            self.is_minimized = False; self.setFixedSize(self.normal_w, self.normal_h)
            self.main_widget.setGeometry(0, 0, self.normal_w, self.normal_h); self.main_widget.show(); self.edge_state = "none"
            screen = QGuiApplication.primaryScreen().size(); self.target_x = (screen.width() - self.normal_w) // 2
            self.setGeometry(self.target_x, self.target_y, self.normal_w, self.normal_h)
            self.setWindowOpacity(1.0); self.is_showing = True; self.is_animating = False
            self.hide_timer.stop(); self.auto_hide_timer.stop(); self.start_time = time.time()
        else:
            self.is_minimized = True; self.setFixedSize(self.mini_size, self.mini_size); self.main_widget.hide()
            screen = QGuiApplication.primaryScreen().size(); self.target_x = (screen.width() - self.mini_size) // 2
            self.setGeometry(self.target_x, self.target_y, self.mini_size, self.mini_size)
        self.update()

    def mousePressEvent(self, e):
        if self.is_minimized and e.button() == Qt.LeftButton:
            if self.is_animating:
                self.anim_in.stop(); self.anim_out.stop(); self.is_animating = False; self.setWindowOpacity(1.0); self.is_showing = True
            self.drag_offset = e.pos()

    def mouseMoveEvent(self, e):
        if self.is_minimized and self.drag_offset and e.buttons() == Qt.LeftButton:
            self.move(e.globalPos() - self.drag_offset); self.target_x = self.x()

    def mouseReleaseEvent(self, e):
        if self.is_minimized and self.drag_offset:
            self.drag_offset = None
            screen = QGuiApplication.primaryScreen().size()
            if self.x() <= 10: self.edge_state = "left"; self.trigger_hide()
            elif self.x() + self.width() >= screen.width() - 10: self.edge_state = "right"; self.trigger_hide()
            elif self.y() <= 10: self.edge_state = "top"; self.trigger_hide()
            elif self.y() + self.height() >= screen.height() - 10: self.edge_state = "bottom"; self.trigger_hide()
            else: self.edge_state = "none"

    def mouseDoubleClickEvent(self, e):
        if self.is_minimized: self.toggle_minimize()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.ApplicationDeactivate and not self.is_dialog_open:
            self.close_all_popups()
        elif event.type() == QEvent.MouseButtonPress:
            if self.lvl2_popup or self.lvl3_popup:
                pos = event.globalPosition().toPoint()
                in_lvl2 = self.lvl2_popup and self.lvl2_popup.isVisible() and self.lvl2_popup.geometry().contains(pos)
                in_lvl3 = self.lvl3_popup and self.lvl3_popup.isVisible() and self.lvl3_popup.geometry().contains(pos)
                if not (in_lvl2 or in_lvl3): self.close_all_popups()
        return super().eventFilter(obj, event)

    def close_all_popups(self):
        if self.lvl3_popup: self.lvl3_popup.close(); self.lvl3_popup = None
        if self.lvl2_popup: self.lvl2_popup.close(); self.lvl2_popup = None

    def show_playlist(self):
        self.hover_timer.stop(); self.close_all_popups()
        self.lvl2_popup = PlaylistDialog(self); self.lvl2_popup.show(); self.hover_timer.start(100)

    def show_volume_slider(self):
        self.hover_timer.stop(); self.close_all_popups()
        self.lvl2_popup = VolumeDialog(self); self.lvl2_popup.show(); self.hover_timer.start(100)

    def show_more_dialog(self):
        self.hover_timer.stop(); self.close_all_popups()
        self.lvl2_popup = MoreDialog(self); self.lvl2_popup.show(); self.hover_timer.start(100)

    def show_style_dialog(self):
        if self.lvl3_popup: self.lvl3_popup.close()
        if not self.lvl2_popup: return
        self.lvl3_popup = StyleDialog(self, self.lvl2_popup); self.lvl3_popup.show()

    def show_mods_dialog(self):
        if self.lvl3_popup: self.lvl3_popup.close()
        if not self.lvl2_popup: return
        self.lvl3_popup = ModsDialog(self, self.lvl2_popup, self.loaded_mods); self.lvl3_popup.show()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Left: self.player.setPosition(max(0, self.player.position() - 5000)); self.start_time = time.time()
        elif e.key() == Qt.Key_Right: self.player.setPosition(min(self.player.duration(), self.player.position() + 5000)); self.start_time = time.time()
        else: super().keyPressEvent(e)

    def load_folder(self, folder):
        valid_exts = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg'}
        try: self.playlist = [os.path.join(folder, f) for f in os.listdir(folder) if Path(f).suffix.lower() in valid_exts]
        except: self.playlist = []
        if not self.playlist: ToastWindow("该文件夹没有音乐", self); return
        cfg["last_folder"] = folder; save_json(CONFIG_PATH, cfg); self.current_index = 0; self.play_current()

    def load_network_tracks(self, tracks):
        if not tracks:
            ToastWindow("歌单为空", self); return
        self.playlist = [t["url"] for t in tracks]
        self.network_titles = {i: t.get("title", f"Track {i+1}") for i, t in enumerate(tracks)}
        self.current_index = 0
        self.play_current()

    def load_playlist_entry(self, entry):
        provider = entry.get("provider")
        if provider:
            mod = next((m for m in self.loaded_mods if m["name"] == provider), None)
            if mod and mod.get("resolve_playlist"):
                try:
                    mod["resolve_playlist"](entry["path"], self.mod_api)
                except Exception as e:
                    ToastWindow(f"Mod [{provider}] 解析出错: {e}", self)
            else:
                ToastWindow(f"Mod [{provider}] 未加载或未实现 resolve_playlist", self)
        else:
            self.load_folder(entry["path"])

    def play_current(self):
        if not self.playlist: return
        src = self.playlist[self.current_index]
        if isinstance(src, str) and src.startswith(("http://", "https://")):
            self.player.setSource(QUrl(src))
            title = self.network_titles.get(self.current_index, f"Track {self.current_index + 1}")
        else:
            self.player.setSource(QUrl.fromLocalFile(src))
            title = Path(src).stem
        self.player.play()
        self.lbl_song.setText(title)

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState: self.player.pause()
        else: self.player.play()

    def play_prev(self):
        if not self.playlist: return
        self.current_index = (self.current_index - 1) % len(self.playlist); self.play_current()

    def play_next(self):
        if not self.playlist: return
        if cfg["play_mode"] == "shuffle": self.current_index = random.randint(0, len(self.playlist) - 1)
        else: self.current_index = (self.current_index + 1) % len(self.playlist)
        self.play_current()

    def toggle_mode(self):
        modes = ["loop", "single", "shuffle"]
        idx = modes.index(cfg["play_mode"]); cfg["play_mode"] = modes[(idx + 1) % 3]
        save_json(CONFIG_PATH, cfg); self.update_mode_icon()

    def update_mode_icon(self):
        mode = cfg["play_mode"]; self.btn_mode.setIcon(get_icon("loop" if mode == "loop" else "single" if mode == "single" else "shuffle"))

    def init_signals(self):
        self.player.positionChanged.connect(self.on_pos); self.player.durationChanged.connect(self.on_dur)
        self.player.playbackStateChanged.connect(self.on_state); self.player.mediaStatusChanged.connect(self.on_media_status)

    def wheelEvent(self, e):
        delta = e.angleDelta().y()
        self.current_vol = min(100, self.current_vol + 5) if delta > 0 else max(0, self.current_vol - 5)
        self.audio_output.setVolume(min(1.0, self.current_vol / 100.0)); cfg["volume"] = self.current_vol
        save_json(CONFIG_PATH, cfg); ToastWindow(f"音量: {self.current_vol}%", self)
        if self.lvl2_popup and isinstance(self.lvl2_popup, VolumeDialog):
            self.lvl2_popup.slider.blockSignals(True); self.lvl2_popup.slider.setValue(self.current_vol); self.lvl2_popup.slider.blockSignals(False)

    def on_media_status(self, s):
        if s == QMediaPlayer.EndOfMedia:
            if cfg["play_mode"] == "single": self.player.setPosition(0); self.player.play()
            else: self.play_next()

    def on_state(self, s): self.btn_play.setIcon(get_icon("pause" if s == QMediaPlayer.PlayingState else "play"))
    def on_dur(self, d): self.upd_time(self.player.position(), d)

    def on_pos(self, p):
        if not self.is_dragging_progress:
            self.upd_time(p, self.player.duration())
            if self.player.duration() > 0: self.slider_progress.setValue(int(p / self.player.duration() * 1000))

    def on_slider_press(self): self.is_dragging_progress = True
    def on_slider_release(self): self.is_dragging_progress = False; self.player.setPosition(int(self.slider_progress.value() / 1000 * self.player.duration())); self.start_time = time.time()

    def on_slider_move(self, v):
        if self.player.duration() > 0: self.upd_time(int(v / 1000 * self.player.duration()), self.player.duration())

    def upd_time(self, p, d):
        f = lambda ms: f"{ms//60000:02d}:{ms//1000%60:02d}"
        self.lbl_time.setText(f"{f(p)} / {f(d)}")

    def restore_last_session(self):
        self.update_mode_icon()
        folder = cfg["last_folder"]
        if folder and os.path.exists(folder):
            self.load_folder(folder); self.player.pause()

    def init_animations(self):
        self.anim_in = QPropertyAnimation(self, b"pos"); self.anim_in.setDuration(300); self.anim_in.setEasingCurve(QEasingCurve.OutSine)
        self.anim_in_op = QPropertyAnimation(self, b"windowOpacity"); self.anim_in_op.setDuration(300)
        self.anim_out = QPropertyAnimation(self, b"pos"); self.anim_out.setDuration(300); self.anim_out.setEasingCurve(QEasingCurve.InSine)
        self.anim_out_op = QPropertyAnimation(self, b"windowOpacity"); self.anim_out_op.setDuration(300)
        self.anim_in.finished.connect(lambda: setattr(self, 'is_animating', False))
        self.anim_out.finished.connect(lambda: setattr(self, 'is_animating', False))

    def startup_intro(self): self.trigger_show(); self.auto_hide_timer.start(3000)

    def check_hover_state(self):
        if self.is_animating: return
        if self.lvl2_popup and self.lvl2_popup.isVisible(): return
        pos = QCursor.pos(); screen = QGuiApplication.primaryScreen().size()

        if self.is_minimized and self.edge_state != "none" and not self.is_showing:
            if self.geometry().contains(pos): self.trigger_show(); return

        in_hotzone = (pos.y() <= 5 and 0.4 <= pos.x()/screen.width() <= 0.6) if not self.is_minimized else False
        in_window = self.geometry().contains(pos)

        if in_hotzone and not self.is_showing: self.auto_hide_timer.stop(); self.trigger_show()
        elif in_window: self.auto_hide_timer.stop(); self.hide_timer.stop()
        else:
            if self.is_showing and not self.hide_timer.isActive() and not self.auto_hide_timer.isActive():
                if self.is_minimized and self.edge_state == "none": return
                in_gap = False
                if not self.is_minimized: in_gap = (pos.y() < 25) and (self.target_x <= pos.x() <= self.target_x + self.width())
                else:
                    if self.edge_state == "left": in_gap = pos.x() <= 10 + self.width()
                    elif self.edge_state == "right": in_gap = pos.x() >= screen.width() - 10 - self.width()
                    elif self.edge_state == "top": in_gap = pos.y() <= 10 + self.height()
                    elif self.edge_state == "bottom": in_gap = pos.y() >= screen.height() - 10 - self.height()
                if in_gap: return
                elapsed = time.time() - self.start_time
                delay = 0 if elapsed < 0.8 else (elapsed if elapsed <= 2.0 else 2.0)
                if delay == 0: self.trigger_hide()
                else: self.hide_timer.start(int(delay * 1000))

    def trigger_show(self):
        if self.is_showing or self.is_animating: return
        self.hide_timer.stop(); self.is_showing = True; self.is_animating = True; self.start_time = time.time()
        screen = QGuiApplication.primaryScreen().size(); start_pos = QPoint(0, 0); end_pos = QPoint(0, 0)
        if self.is_minimized:
            self.anim_in_op.setStartValue(0.5); self.anim_in_op.setEndValue(1.0)
            if self.edge_state == "left": start_pos = QPoint(-self.width() * 2 // 3, self.target_y); end_pos = QPoint(10, self.target_y)
            elif self.edge_state == "right": start_pos = QPoint(screen.width() - self.width() // 3, self.target_y); end_pos = QPoint(screen.width() - self.width() - 10, self.target_y)
            elif self.edge_state == "top": start_pos = QPoint(self.target_x, -self.height() * 2 // 3); end_pos = QPoint(self.target_x, 10)
            elif self.edge_state == "bottom": start_pos = QPoint(self.target_x, screen.height() - self.height() // 3); end_pos = QPoint(self.target_x, screen.height() - self.height() - 10)
            else: start_pos = self.pos(); end_pos = self.pos(); self.setWindowOpacity(1.0)
        else:
            self.setWindowOpacity(0.0); self.anim_in_op.setStartValue(0.0); self.anim_in_op.setEndValue(1.0)
            self.target_x = (screen.width() - self.width()) // 2; start_pos = QPoint(self.target_x, self.hidden_y); end_pos = QPoint(self.target_x, self.target_y)
        self.anim_in.setStartValue(start_pos); self.anim_in.setEndValue(end_pos); self.anim_in.start(); self.anim_in_op.start()

    def trigger_hide(self):
        if not self.is_showing or self.is_animating: return
        self.is_showing = False; self.is_animating = True
        screen = QGuiApplication.primaryScreen().size(); start_pos = self.pos(); end_pos = QPoint(0, 0)
        if self.is_minimized and self.edge_state != "none":
            self.anim_out_op.setStartValue(1.0); self.anim_out_op.setEndValue(0.5)
            if self.edge_state == "left": end_pos = QPoint(-self.width() * 2 // 3, self.target_y)
            elif self.edge_state == "right": end_pos = QPoint(screen.width() - self.width() // 3, self.target_y)
            elif self.edge_state == "top": end_pos = QPoint(self.target_x, -self.height() * 2 // 3)
            elif self.edge_state == "bottom": end_pos = QPoint(self.target_x, screen.height() - self.height() // 3)
        elif self.is_minimized and self.edge_state == "none":
            self.is_animating = False; self.is_showing = True; return
        else:
            self.anim_out_op.setStartValue(1.0); self.anim_out_op.setEndValue(0.0); end_pos = QPoint(self.target_x, self.hidden_y)
        self.anim_out.setStartValue(start_pos); self.anim_out.setEndValue(end_pos); self.anim_out.start(); self.anim_out_op.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    win = MusicPlayerWindow()
    win.show()
    sys.exit(app.exec())
