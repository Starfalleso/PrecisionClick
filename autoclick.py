import os
import sys
import ctypes

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# 1. Force DPI Awareness to "Per Monitor V2" before ANY other library imports.
# This is the most proactive way to avoid conflicts between Qt and PyAutoGUI.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # 2 = PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware() # Fallback for older Windows
    except Exception:
        pass

# 2. Suppress the "Access is denied" warning and configure via qt.conf
os.environ["QT_CONF_PATH"] = resource_path("qt.conf")
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

import time
import pyautogui
import keyboard
import random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QDoubleSpinBox, QSpinBox, QPushButton, QCheckBox, QFrame,
    QComboBox, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFileDialog, QMessageBox, QStackedWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QFont, QPainter, QColor, QIcon

# Set Windows App ID for Taskbar Icon consistency
if sys.platform == "win32":
    import ctypes
    myappid = 'mycompany.myproduct.subproduct.version' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# Disable pyautogui's default 0.1s delay to allow user-defined intervals
pyautogui.PAUSE = 0

class ClickIndicator(QWidget):
    """Semi-transparent overlay to show click target locations."""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(24, 24)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw outer circle (semi-transparent)
        painter.setBrush(QColor(243, 139, 168, 80)) # Red with low alpha
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 24, 24)
        
        # Draw inner dot (solid)
        painter.setBrush(QColor(243, 139, 168)) # Solid red
        painter.drawEllipse(8, 8, 8, 8)
        
        # Draw crosshair lines
        painter.setPen(QColor(243, 139, 168, 150))
        painter.drawLine(12, 0, 12, 24)
        painter.drawLine(0, 12, 24, 12)

class ClickWorker(QThread):
    """Worker thread for the clicking loop to keep UI responsive."""
    clicked = pyqtSignal(int)
    finished = pyqtSignal()
    status_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.running = False
        self.mode = 'simple'
        self.interval = 0.1
        self.random_variance = 0.0
        self.limit = None
        self.count = 0
        self._stop_requested = False
        self.button = 'left'
        self.fixed_location = False
        self.x = 0
        self.y = 0
        self.sequence = [] # List of {'x', 'y', 'button', 'interval', 'variance'}

    def stop(self):
        self._stop_requested = True
        self.running = False

    def run(self):
        self._stop_requested = False
        while not self._stop_requested:
            if self.running:
                if self.mode == 'simple':
                    self.execute_simple_click()
                else:
                    self.execute_sequence_cycle()
                
                if self.limit and self.count >= self.limit:
                    self.running = False
                    self.status_changed.emit(False)
                    break
            else:
                time.sleep(0.05)

    def execute_simple_click(self):
        # Perform Click
        btn = self.button.lower()
        if "double" in btn:
            real_btn = btn.replace("double ", "")
            if self.fixed_location:
                pyautogui.doubleClick(x=self.x, y=self.y, button=real_btn)
            else:
                pyautogui.doubleClick(button=real_btn)
        else:
            if self.fixed_location:
                pyautogui.click(x=self.x, y=self.y, button=btn)
            else:
                pyautogui.click(button=btn)
        
        self.count += 1
        self.clicked.emit(self.count)
        
        # Calculate next interval with variance
        current_delay = self.interval
        if self.random_variance > 0:
            current_delay += random.uniform(-self.random_variance, self.random_variance)
            current_delay = max(0.001, current_delay)

        # Sleep
        self.interruptible_sleep(current_delay)

    def execute_sequence_cycle(self):
        if not self.sequence:
            time.sleep(0.1)
            return

        for step in self.sequence:
            if not self.running or self._stop_requested:
                break
                
            # Wait specific interval for this step
            delay = step['interval']
            if step['variance'] > 0:
                delay += random.uniform(-step['variance'], step['variance'])
                delay = max(0.001, delay)
            
            self.interruptible_sleep(delay)
            
            if not self.running or self._stop_requested:
                break

            # Perform Click
            btn = step['button'].lower()
            if "double" in btn:
                real_btn = btn.replace("double ", "")
                pyautogui.doubleClick(x=step['x'], y=step['y'], button=real_btn)
            else:
                pyautogui.click(x=step['x'], y=step['y'], button=btn)
            
            # Count total clicks
            self.count += 1
            self.clicked.emit(self.count)

    def interruptible_sleep(self, duration):
        start_sleep = time.time()
        while time.time() - start_sleep < duration:
            if not self.running or self._stop_requested:
                break
            time.sleep(0.005)

class AutoClickerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PrecisionClick")
        icon_path = resource_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(850, 560)
        
        # State
        self.start_key = '['
        self.stop_key = ']'
        self.capture_key = 'p'
        self.recording_start = False
        self.recording_stop = False
        self.recording_capture = False
        self.indicators = []
        self.current_mode = 'simple'
        self.last_mouse_state = False
        self.recording_active = False
        
        # Worker Thread
        self.worker = ClickWorker()
        self.worker.clicked.connect(self.update_count)
        self.worker.status_changed.connect(self.set_running_state)
        self.worker.start()
        
        # UI Setup
        self.init_ui()
        self.setup_hotkeys()
        self.apply_styles()
        
        # Timer for capturing mouse position
        self.mouse_timer = QTimer()
        self.mouse_timer.timeout.connect(self.capture_mouse_pos)
        self.mouse_timer.start(50)

    def update_indicators(self):
        # Clear existing indicators
        for ind in self.indicators:
            ind.hide()
            ind.deleteLater()
        self.indicators.clear()

        if not self.show_reticles_checkbox.isChecked():
            return

        if self.current_mode == 'simple':
            if self.fixed_loc_checkbox.isChecked():
                self.create_indicator(self.x_spin.value(), self.y_spin.value())
        else: # Sequence Mode
            for i in range(self.table.rowCount()):
                try:
                    x = int(self.table.item(i, 0).text())
                    y = int(self.table.item(i, 1).text())
                    self.create_indicator(x, y)
                except (ValueError, AttributeError):
                    continue

    def create_indicator(self, x, y):
        ind = ClickIndicator()
        ind.move(x - 12, y - 12) # Center it on coords
        ind.show()
        self.indicators.append(ind)

    def apply_styles(self, accent_color="#89b4fa", hover_color="#b4befe", text_color="#11111b"):
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: #181825;
            }}
            QWidget {{
                color: #cdd6f4;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
                font-size: 13px;
            }}
            #Sidebar {{
                background-color: #11111b;
                border-right: 1px solid #313244;
            }}
            #SidebarLogo {{
                color: {accent_color};
                font-size: 20px;
                font-weight: 800;
                padding: 10px 5px;
                margin-bottom: 15px;
            }}
            #NavBtn {{
                background-color: transparent;
                color: #a6adc8;
                border-radius: 8px;
                padding: 12px 15px;
                text-align: left;
                font-weight: 600;
                border: none;
            }}
            #NavBtn:hover {{
                background-color: #313244;
                color: #cdd6f4;
            }}
            #NavBtn[active="true"] {{
                background-color: {accent_color};
                color: {text_color};
            }}
            #Card {{
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 12px;
            }}
            #CardHeader {{
                color: {accent_color};
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 5px;
            }}
            QDoubleSpinBox, QSpinBox {{
                background-color: #11111b;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 6px 24px 6px 10px;
            }}
            QComboBox {{
                background-color: #11111b;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 6px 28px 6px 10px;
            }}
            QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{
                border: 1px solid {accent_color};
            }}
            
            /* Custom SpinBox Arrow Buttons */
            QDoubleSpinBox::up-button, QSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                background-color: #313244;
                border-left: 1px solid #45475a;
                border-top-right-radius: 8px;
            }}
            QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover {{
                background-color: #45475a;
            }}
            QDoubleSpinBox::down-button, QSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                background-color: #313244;
                border-left: 1px solid #45475a;
                border-bottom-right-radius: 8px;
            }}
            QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {{
                background-color: #45475a;
            }}
            QDoubleSpinBox::up-arrow, QSpinBox::up-arrow {{
                image: none;
                border: 4px solid transparent;
                border-bottom: 5px solid #cdd6f4;
                width: 0;
                height: 0;
            }}
            QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {{
                image: none;
                border: 4px solid transparent;
                border-top: 5px solid #cdd6f4;
                width: 0;
                height: 0;
            }}

            /* Custom ComboBox Drop-down */
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid #313244;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                background-color: #313244;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: 4px solid transparent;
                border-top: 5px solid #cdd6f4;
                width: 0;
                height: 0;
            }}
            QComboBox::drop-down:hover {{
                background-color: #45475a;
            }}
            QComboBox QAbstractItemView {{
                background-color: #1e1e2e;
                border: 1px solid #313244;
                selection-background-color: #313244;
                selection-color: #cdd6f4;
            }}
            QPushButton {{
                background-color: #313244;
                color: #cdd6f4;
                border-radius: 8px;
                padding: 8px 14px;
                border: 1px solid #45475a;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #45475a;
                border-color: #585b70;
            }}
            QPushButton:pressed {{
                background-color: #585b70;
            }}
            QPushButton:disabled {{
                background-color: #181825;
                color: #585b70;
                border-color: #1e1e2e;
            }}
            #StartBtn {{
                background-color: #1e1e2e;
                color: #a6e3a1;
                border: 1px solid #4f7e57;
                border-radius: 10px;
                font-size: 13px;
                font-weight: bold;
            }}
            #StartBtn:hover {{
                background-color: #233b2a;
                border-color: #a6e3a1;
                color: #a6e3a1;
            }}
            #StartBtn:pressed {{
                background-color: #1a2f20;
            }}
            #StartBtn:disabled {{
                background-color: #11111b;
                color: #585b70;
                border: 1px solid #313244;
            }}
            #StopBtn {{
                background-color: #1e1e2e;
                color: #f38ba8;
                border: 1px solid #7c4456;
                border-radius: 10px;
                font-size: 13px;
                font-weight: bold;
            }}
            #StopBtn:hover {{
                background-color: #4a2731;
                border-color: #f38ba8;
                color: #f38ba8;
            }}
            #StopBtn:pressed {{
                background-color: #3b1c25;
            }}
            #StopBtn:disabled {{
                background-color: #11111b;
                color: #585b70;
                border: 1px solid #313244;
            }}
            #StatusIdle {{
                color: #fab387;
                font-weight: bold;
                font-size: 15px;
            }}
            #StatusActive {{
                color: #a6e3a1;
                font-weight: bold;
                font-size: 15px;
            }}
            QCheckBox {{
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                background-color: #11111b;
                border: 1px solid #313244;
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent_color};
            }}
            QTableWidget {{
                background-color: #11111b;
                alternate-background-color: #1e1e2e;
                gridline-color: #313244;
                border-radius: 8px;
                border: 1px solid #313244;
            }}
            QHeaderView::section {{
                background-color: #313244;
                color: {accent_color};
                padding: 6px;
                border: none;
                font-weight: bold;
            }}
            QScrollBar:vertical {{
                border: none;
                background: #11111b;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #313244;
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #45475a;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

    def setup_hotkeys(self):
        try:
            keyboard.unhook_all()
        except:
            pass
        keyboard.add_hotkey(self.start_key, self.start_clicking)
        keyboard.add_hotkey(self.stop_key, self.stop_clicking)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout is horizontal: Sidebar on Left, Content on Right
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ================= SIDEBAR (LEFT) =================
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 25, 20, 25)
        sidebar_layout.setSpacing(15)
        
        # Logo / Title
        logo = QLabel("PrecisionClick")
        logo.setObjectName("SidebarLogo")
        logo.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(logo)
        
        # Nav Group Label
        nav_group_label = QLabel("NAVIGATION")
        nav_group_label.setStyleSheet("color: #585b70; font-size: 11px; font-weight: bold; margin-top: 10px;")
        sidebar_layout.addWidget(nav_group_label)
        
        # Navigation Buttons
        self.nav_simple_btn = QPushButton("  🎛️  Simple Clicker")
        self.nav_simple_btn.setObjectName("NavBtn")
        self.nav_simple_btn.clicked.connect(lambda: self.switch_page(0))
        sidebar_layout.addWidget(self.nav_simple_btn)
        
        self.nav_sequence_btn = QPushButton("  📜  Macro Sequence")
        self.nav_sequence_btn.setObjectName("NavBtn")
        self.nav_sequence_btn.clicked.connect(lambda: self.switch_page(1))
        sidebar_layout.addWidget(self.nav_sequence_btn)
        
        self.nav_settings_btn = QPushButton("  ⚙️  Hotkeys & Settings")
        self.nav_settings_btn.setObjectName("NavBtn")
        self.nav_settings_btn.clicked.connect(lambda: self.switch_page(2))
        sidebar_layout.addWidget(self.nav_settings_btn)
        
        # Push stats card & buttons to bottom
        sidebar_layout.addStretch()
        
        # Stats & Status Panel
        status_panel = QFrame()
        status_panel.setObjectName("Card")
        status_panel_layout = QVBoxLayout(status_panel)
        status_panel_layout.setContentsMargins(15, 15, 15, 15)
        status_panel_layout.setSpacing(8)
        
        self.status_label = QLabel("STATUS: IDLE")
        self.status_label.setObjectName("StatusIdle")
        self.status_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_panel_layout.addWidget(self.status_label)
        
        self.count_label = QLabel("Clicks: 0")
        self.count_label.setFont(QFont("Segoe UI", 12))
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setStyleSheet("color: #a6adc8;")
        status_panel_layout.addWidget(self.count_label)
        
        sidebar_layout.addWidget(status_panel)
        
        # Action Buttons (Start/Stop)
        self.start_btn = QPushButton("START EXECUTION")
        self.start_btn.setObjectName("StartBtn")
        self.start_btn.setFixedHeight(50)
        self.start_btn.clicked.connect(self.start_clicking)
        sidebar_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("STOP EXECUTION")
        self.stop_btn.setObjectName("StopBtn")
        self.stop_btn.setFixedHeight(50)
        self.stop_btn.clicked.connect(self.stop_clicking)
        self.stop_btn.setEnabled(False)
        sidebar_layout.addWidget(self.stop_btn)
        
        # Signature
        signature = QLabel("Made by Vagner L.")
        signature.setAlignment(Qt.AlignmentFlag.AlignCenter)
        signature.setStyleSheet("color: #585b70; font-size: 11px; font-weight: bold; margin-top: 15px;")
        sidebar_layout.addWidget(signature)
        
        main_layout.addWidget(self.sidebar)
        
        # ================= CONTENT AREA (RIGHT) =================
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: #181825;")
        
        # ---- PAGE 0: SIMPLE CLICKER ----
        page_simple = QWidget()
        page_simple_layout = QVBoxLayout(page_simple)
        page_simple_layout.setContentsMargins(25, 25, 25, 25)
        page_simple_layout.setSpacing(20)
        
        # Header title
        simple_title = QLabel("Simple Repeating Clicker")
        simple_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        simple_title.setStyleSheet("color: #89b4fa;")
        page_simple_layout.addWidget(simple_title)
        
        # Settings Card
        self.settings_card = QFrame()
        self.settings_card.setObjectName("Card")
        settings_layout = QVBoxLayout(self.settings_card)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        
        settings_header = QLabel("CONFIGURATION")
        settings_header.setObjectName("CardHeader")
        settings_layout.addWidget(settings_header)
        
        grid = QGridLayout()
        grid.setSpacing(15)
        
        grid.addWidget(QLabel("Interval (seconds):"), 0, 0)
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.001, 3600.0)
        self.interval_spin.setValue(0.1)
        self.interval_spin.setSingleStep(0.01)
        self.interval_spin.valueChanged.connect(self.update_settings)
        grid.addWidget(self.interval_spin, 0, 1)
        
        grid.addWidget(QLabel("Variance (+/- seconds):"), 0, 2)
        self.variance_spin = QDoubleSpinBox()
        self.variance_spin.setRange(0.0, 10.0)
        self.variance_spin.setValue(0.0)
        self.variance_spin.setSingleStep(0.01)
        self.variance_spin.valueChanged.connect(self.update_settings)
        grid.addWidget(self.variance_spin, 0, 3)
        
        grid.addWidget(QLabel("Click Type:"), 1, 0)
        self.button_combo = QComboBox()
        self.button_combo.addItems(["Left", "Double Left", "Right", "Double Right", "Middle"])
        self.button_combo.currentIndexChanged.connect(self.update_settings)
        grid.addWidget(self.button_combo, 1, 1)
        
        self.limit_checkbox = QCheckBox("Infinite Clicks")
        self.limit_checkbox.setChecked(True)
        self.limit_checkbox.toggled.connect(self.toggle_limit)
        grid.addWidget(self.limit_checkbox, 1, 2)
        
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 10000000)
        self.limit_spin.setValue(100)
        self.limit_spin.setEnabled(False)
        self.limit_spin.valueChanged.connect(self.update_settings)
        grid.addWidget(self.limit_spin, 1, 3)
        
        settings_layout.addLayout(grid)
        page_simple_layout.addWidget(self.settings_card)
        
        # Location Card
        self.location_card = QFrame()
        self.location_card.setObjectName("Card")
        loc_layout = QVBoxLayout(self.location_card)
        loc_layout.setContentsMargins(20, 20, 20, 20)
        
        loc_header = QLabel("TARGET LOCATION")
        loc_header.setObjectName("CardHeader")
        loc_layout.addWidget(loc_header)
        
        loc_grid = QGridLayout()
        loc_grid.setSpacing(15)
        self.fixed_loc_checkbox = QCheckBox("Fixed Coordinates")
        self.fixed_loc_checkbox.toggled.connect(self.toggle_location)
        loc_grid.addWidget(self.fixed_loc_checkbox, 0, 0, 1, 2)
        
        loc_grid.addWidget(QLabel("X Coordinate:"), 1, 0)
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 10000)
        self.x_spin.setEnabled(False)
        self.x_spin.valueChanged.connect(self.update_settings)
        self.x_spin.valueChanged.connect(self.update_indicators)
        loc_grid.addWidget(self.x_spin, 1, 1)
        
        loc_grid.addWidget(QLabel("Y Coordinate:"), 1, 2)
        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 10000)
        self.y_spin.setEnabled(False)
        self.y_spin.valueChanged.connect(self.update_settings)
        self.y_spin.valueChanged.connect(self.update_indicators)
        loc_grid.addWidget(self.y_spin, 1, 3)
        
        self.pick_btn = QPushButton("Capture (P)")
        self.pick_btn.setEnabled(False)
        self.pick_btn.setToolTip("Press 'P' while hovering to capture coordinates")
        loc_grid.addWidget(self.pick_btn, 1, 4)
        
        loc_layout.addLayout(loc_grid)
        page_simple_layout.addWidget(self.location_card)
        page_simple_layout.addStretch()
        
        self.stacked_widget.addWidget(page_simple)
        
        # ---- PAGE 1: MACRO SEQUENCE ----
        page_sequence = QWidget()
        page_sequence_layout = QVBoxLayout(page_sequence)
        page_sequence_layout.setContentsMargins(25, 25, 25, 25)
        page_sequence_layout.setSpacing(20)
        
        seq_title = QLabel("Macro Click Sequence")
        seq_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        seq_title.setStyleSheet("color: #89b4fa;")
        page_sequence_layout.addWidget(seq_title)
        
        self.sequence_card = QFrame()
        self.sequence_card.setObjectName("Card")
        seq_layout = QVBoxLayout(self.sequence_card)
        seq_layout.setContentsMargins(20, 20, 20, 20)
        seq_layout.setSpacing(15)
        
        seq_header = QLabel("MACRO SEQUENCE STEPS")
        seq_header.setObjectName("CardHeader")
        seq_layout.addWidget(seq_header)
        
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["X", "Y", "Btn", "Delay (s)", "Var (s)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setFixedHeight(240)
        self.table.itemChanged.connect(self.update_indicators)
        seq_layout.addWidget(self.table)
        
        seq_btn_layout = QVBoxLayout()
        row1_layout = QHBoxLayout()
        row2_layout = QHBoxLayout()
        row1_layout.setSpacing(10)
        row2_layout.setSpacing(10)
        
        self.record_seq_btn = QPushButton("🎙️  Record Clicks")
        self.record_seq_btn.clicked.connect(self.start_interactive_recording)
        self.record_seq_btn.setToolTip("Minimize app and record mouse clicks. Press ESC to stop.")
        
        self.add_step_btn = QPushButton("➕  Add Step")
        self.add_step_btn.clicked.connect(lambda: self.add_sequence_step())
        
        self.remove_step_btn = QPushButton("➖  Remove")
        self.remove_step_btn.clicked.connect(self.remove_sequence_step)
        
        self.clear_steps_btn = QPushButton("Clear All")
        self.clear_steps_btn.clicked.connect(lambda: self.table.setRowCount(0))
        
        row1_layout.addWidget(self.record_seq_btn)
        row1_layout.addWidget(self.add_step_btn)
        row1_layout.addWidget(self.remove_step_btn)
        row1_layout.addWidget(self.clear_steps_btn)
        
        self.save_profile_btn = QPushButton("Save Profile")
        self.save_profile_btn.clicked.connect(self.save_profile)
        
        self.load_profile_btn = QPushButton("Load Profile")
        self.load_profile_btn.clicked.connect(self.load_profile)
        
        row2_layout.addWidget(self.save_profile_btn)
        row2_layout.addWidget(self.load_profile_btn)
        
        seq_btn_layout.addLayout(row1_layout)
        seq_btn_layout.addLayout(row2_layout)
        seq_layout.addLayout(seq_btn_layout)
        
        page_sequence_layout.addWidget(self.sequence_card)
        page_sequence_layout.addStretch()
        
        self.stacked_widget.addWidget(page_sequence)
        
        # ---- PAGE 2: SETTINGS & HOTKEYS ----
        page_settings = QWidget()
        page_settings_layout = QVBoxLayout(page_settings)
        page_settings_layout.setContentsMargins(25, 25, 25, 25)
        page_settings_layout.setSpacing(20)
        
        settings_title = QLabel("System Hotkeys & Settings")
        settings_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        settings_title.setStyleSheet("color: #89b4fa;")
        page_settings_layout.addWidget(settings_title)
        
        # Hotkey configuration
        self.hotkey_card = QFrame()
        self.hotkey_card.setObjectName("Card")
        hot_layout = QVBoxLayout(self.hotkey_card)
        hot_layout.setContentsMargins(20, 20, 20, 20)
        hot_layout.setSpacing(15)
        
        hot_header = QLabel("GLOBAL TRIGGER HOTKEYS")
        hot_header.setObjectName("CardHeader")
        hot_layout.addWidget(hot_header)
        
        hk_btns = QHBoxLayout()
        hk_btns.setSpacing(15)
        self.start_key_btn = QPushButton(f"START HOTKEY: {self.start_key.upper()}")
        self.start_key_btn.clicked.connect(self.record_start_key)
        self.start_key_btn.setFixedHeight(45)
        hk_btns.addWidget(self.start_key_btn)
        
        self.stop_key_btn = QPushButton(f"STOP HOTKEY: {self.stop_key.upper()}")
        self.stop_key_btn.clicked.connect(self.record_stop_key)
        self.stop_key_btn.setFixedHeight(45)
        hk_btns.addWidget(self.stop_key_btn)
        
        self.capture_key_btn = QPushButton(f"CAPTURE HOTKEY: {self.capture_key.upper()}")
        self.capture_key_btn.clicked.connect(self.record_capture_key)
        self.capture_key_btn.setFixedHeight(45)
        hk_btns.addWidget(self.capture_key_btn)
        hot_layout.addLayout(hk_btns)
        
        page_settings_layout.addWidget(self.hotkey_card)
        
        # Position Tracking Card
        pos_card = QFrame()
        pos_card.setObjectName("Card")
        pos_layout = QVBoxLayout(pos_card)
        pos_layout.setContentsMargins(20, 20, 20, 20)
        
        pos_header = QLabel("LIVE POSITION TRACKER")
        pos_header.setObjectName("CardHeader")
        pos_layout.addWidget(pos_header)
        
        self.live_pos_label = QLabel("Live Position: X: 0, Y: 0 (Hover & press 'P')")
        self.live_pos_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.live_pos_label.setStyleSheet("color: #a6e3a1;")
        self.live_pos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pos_layout.addWidget(self.live_pos_label)
        
        page_settings_layout.addWidget(pos_card)
        
        # General overlay settings card
        overlay_card = QFrame()
        overlay_card.setObjectName("Card")
        overlay_layout = QVBoxLayout(overlay_card)
        overlay_layout.setContentsMargins(20, 20, 20, 20)
        overlay_layout.setSpacing(15)
        
        overlay_header = QLabel("GENERAL PREFERENCES")
        overlay_header.setObjectName("CardHeader")
        overlay_layout.addWidget(overlay_header)
        
        self.show_reticles_checkbox = QCheckBox("Enable Target Crosshair Indicators (Reticles)")
        self.show_reticles_checkbox.setChecked(True)
        self.show_reticles_checkbox.toggled.connect(self.update_indicators)
        overlay_layout.addWidget(self.show_reticles_checkbox)

        # Theme Selector Row
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Accent Color Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Catppuccin Blue", "Jade Green", "Flamingo Pink", "Amber Orange", "Royal Purple"])
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        overlay_layout.addLayout(theme_row)
        
        page_settings_layout.addWidget(overlay_card)
        page_settings_layout.addStretch()
        
        self.stacked_widget.addWidget(page_settings)
        
        main_layout.addWidget(self.stacked_widget)
        
        # Initialize default page state and highlight first sidebar nav button
        self.switch_page(0)

    def switch_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        
        # Update Nav buttons active status property for styling
        self.nav_simple_btn.setProperty("active", index == 0)
        self.nav_sequence_btn.setProperty("active", index == 1)
        self.nav_settings_btn.setProperty("active", index == 2)
        
        # Refresh widgets style status
        for btn in (self.nav_simple_btn, self.nav_sequence_btn, self.nav_settings_btn):
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            
        if index in (0, 1):
            self.current_mode = 'simple' if index == 0 else 'sequence'
            
        self.update_settings()
        self.update_indicators()

    def add_sequence_step(self, x=0, y=0, button="Left", interval=0.1, variance=0.0):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        self.table.setItem(row, 0, QTableWidgetItem(str(x)))
        self.table.setItem(row, 1, QTableWidgetItem(str(y)))
        
        btn_combo = QComboBox()
        btn_combo.addItems(["Left", "Double Left", "Right", "Double Right", "Middle"])
        index = btn_combo.findText(button, Qt.MatchFlag.MatchFixedString)
        if index >= 0:
            btn_combo.setCurrentIndex(index)
        btn_combo.currentIndexChanged.connect(self.update_settings)
        self.table.setCellWidget(row, 2, btn_combo)
        
        self.table.setItem(row, 3, QTableWidgetItem(str(interval)))
        self.table.setItem(row, 4, QTableWidgetItem(str(variance)))
        self.update_indicators()

    def remove_sequence_step(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
            self.update_indicators()

    def save_profile(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Profile", "", "JSON Files (*.json)"
        )
        if file_path:
            self.update_settings()
            try:
                import json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.worker.sequence, f, indent=4)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save profile: {e}")

    def load_profile(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Profile", "", "JSON Files (*.json)"
        )
        if file_path:
            try:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    sequence = json.load(f)
                
                # Turn off change signals temporarily to avoid multiple recalculations
                self.table.blockSignals(True)
                self.table.setRowCount(0)
                for step in sequence:
                    self.add_sequence_step(
                        x=step.get('x', 0),
                        y=step.get('y', 0),
                        button=step.get('button', 'Left').title(),
                        interval=step.get('interval', 0.1),
                        variance=step.get('variance', 0.0)
                    )
                self.table.blockSignals(False)
                self.update_settings()
                self.update_indicators()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load profile: {e}")

    def toggle_limit(self, checked):
        self.limit_spin.setEnabled(not checked)
        self.update_settings()

    def toggle_location(self, checked):
        self.x_spin.setEnabled(checked)
        self.y_spin.setEnabled(checked)
        self.pick_btn.setEnabled(checked)
        self.update_settings()
        self.update_indicators()

    def record_start_key(self):
        self.recording_start = True
        self.recording_stop = False
        self.recording_capture = False
        self.start_key_btn.setText("Press any key...")
        self.start_key_btn.setStyleSheet("background-color: #f9e2af; color: #11111b;") # Warm yellow for recording

    def record_stop_key(self):
        self.recording_stop = True
        self.recording_start = False
        self.recording_capture = False
        self.stop_key_btn.setText("Press any key...")
        self.stop_key_btn.setStyleSheet("background-color: #f9e2af; color: #11111b;")

    def record_capture_key(self):
        self.recording_capture = True
        self.recording_start = False
        self.recording_stop = False
        self.capture_key_btn.setText("Press any key...")
        self.capture_key_btn.setStyleSheet("background-color: #f9e2af; color: #11111b;")

    def keyPressEvent(self, event):
        key_name = event.text().lower()
        if not key_name:
            return

        if self.recording_start:
            self.start_key = key_name
            self.recording_start = False
            self.start_key_btn.setText(f"START HOTKEY: {key_name.upper()}")
            self.start_key_btn.setStyleSheet("")
            self.setup_hotkeys()
        elif self.recording_stop:
            self.stop_key = key_name
            self.recording_stop = False
            self.stop_key_btn.setText(f"STOP HOTKEY: {key_name.upper()}")
            self.stop_key_btn.setStyleSheet("")
            self.setup_hotkeys()
        elif self.recording_capture:
            self.capture_key = key_name
            self.recording_capture = False
            self.capture_key_btn.setText(f"CAPTURE HOTKEY: {key_name.upper()}")
            self.capture_key_btn.setStyleSheet("")
            self.setup_hotkeys()

    def capture_mouse_pos(self):
        # Always update live mouse position label on settings page
        pos = self.cursor().pos()
        if hasattr(self, 'live_pos_label'):
            self.live_pos_label.setText(f"Live Position: X: {pos.x()}, Y: {pos.y()} (Hover & press '{self.capture_key.upper()}')")
            
        if keyboard.is_pressed(self.capture_key):
            # Use QCursor to get screen coordinates that are consistent with Qt's scaling
            if self.current_mode == 'simple':
                if self.fixed_loc_checkbox.isChecked():
                    self.x_spin.setValue(pos.x())
                    self.y_spin.setValue(pos.y())
            else: # Sequence Mode
                self.add_sequence_step(pos.x(), pos.y())
                time.sleep(0.2) # Debounce
            self.update_indicators()

    def update_settings(self):
        self.worker.mode = self.current_mode
        
        # Simple settings
        self.worker.interval = self.interval_spin.value()
        self.worker.random_variance = self.variance_spin.value()
        self.worker.button = self.button_combo.currentText().lower()
        self.worker.fixed_location = self.fixed_loc_checkbox.isChecked()
        self.worker.x = self.x_spin.value()
        self.worker.y = self.y_spin.value()
        
        # Sequence settings
        sequence = []
        for i in range(self.table.rowCount()):
            try:
                x_item = self.table.item(i, 0)
                y_item = self.table.item(i, 1)
                btn_widget = self.table.cellWidget(i, 2)
                inter_item = self.table.item(i, 3)
                var_item = self.table.item(i, 4)
                
                if x_item and y_item and btn_widget and inter_item and var_item:
                    sequence.append({
                        'x': int(x_item.text()),
                        'y': int(y_item.text()),
                        'button': btn_widget.currentText().lower(),
                        'interval': float(inter_item.text()),
                        'variance': float(var_item.text())
                    })
            except (ValueError, AttributeError):
                continue
        self.worker.sequence = sequence
        
        if self.limit_checkbox.isChecked():
            self.worker.limit = None
        else:
            self.worker.limit = self.limit_spin.value()

    def start_clicking(self):
        if not self.worker.running:
            if not self.limit_checkbox.isChecked() and self.worker.count >= self.limit_spin.value():
                self.worker.count = 0
                self.update_count(0)
            
            self.update_settings()
            self.set_running_state(True)

    def stop_clicking(self):
        if self.worker.running:
            self.set_running_state(False)

    def set_running_state(self, running):
        self.worker.running = running
        if running:
            self.status_label.setText("STATUS: ACTIVE")
            self.status_label.setObjectName("StatusActive")
            self.status_label.setStyle(self.status_label.style()) # Force style refresh
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.status_label.setText("STATUS: IDLE")
            self.status_label.setObjectName("StatusIdle")
            self.status_label.setStyle(self.status_label.style())
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def update_count(self, count):
        limit_text = "Infinite" if self.limit_checkbox.isChecked() else str(self.limit_spin.value())
        self.count_label.setText(f"Clicks: {count} / {limit_text}")

    def change_theme(self, index):
        themes = [
            ("#89b4fa", "#b4befe", "#11111b"), # Blue
            ("#a6e3a1", "#a6e3a1", "#11111b"), # Green
            ("#f38ba8", "#f5c2e7", "#11111b"), # Pink
            ("#fab387", "#f9e2af", "#11111b"), # Orange
            ("#cba6f7", "#f5c2e7", "#11111b")  # Purple
        ]
        accent, hover, dark = themes[index]
        self.apply_styles(accent, hover, dark)
        self.switch_page(self.stacked_widget.currentIndex())

    def start_interactive_recording(self):
        # Minimize and sleep to avoid capturing the button click
        self.showMinimized()
        QTimer.singleShot(400, self.begin_recording_loop)

    def begin_recording_loop(self):
        self.last_mouse_state = False
        self.recording_active = True
        
        self.record_timer = QTimer(self)
        self.record_timer.timeout.connect(self.record_tick)
        self.record_timer.start(20) # Check state every 20ms

    def record_tick(self):
        # Press ESC to stop
        if keyboard.is_pressed('esc'):
            self.record_timer.stop()
            self.recording_active = False
            self.showNormal()
            self.activateWindow()
            self.raise_()
            self.update_indicators()
            return
            
        # Check mouse press (LButton = 0x01)
        is_pressed = (ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000) != 0
        if is_pressed and not self.last_mouse_state:
            pos = self.cursor().pos()
            self.add_sequence_step(pos.x(), pos.y())
            
        self.last_mouse_state = is_pressed

    def closeEvent(self, event): 
        self.worker.stop()
        self.worker.wait()
        keyboard.unhook_all()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AutoClickerGUI()
    window.show()
    sys.exit(app.exec())
