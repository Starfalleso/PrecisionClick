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
    QHeaderView, QAbstractItemView
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
        if self.fixed_location:
            pyautogui.click(x=self.x, y=self.y, button=self.button)
        else:
            pyautogui.click(button=self.button)
        
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
            pyautogui.click(x=step['x'], y=step['y'], button=step['button'])
            
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
        self.setMinimumWidth(500)
        
        # State
        self.start_key = '['
        self.stop_key = ']'
        self.recording_start = False
        self.recording_stop = False
        self.indicators = []
        
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

        if self.mode_combo.currentIndex() == 0: # Simple Mode
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

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e2e;
            }
            QWidget {
                color: #cdd6f4;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            }
            #Card {
                background-color: #313244;
                border-radius: 12px;
            }
            #CardHeader {
                color: #89b4fa;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border-radius: 8px;
                padding: 10px;
                border: none;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #585b70;
            }
            QPushButton:pressed {
                background-color: #6c7086;
            }
            QPushButton:disabled {
                background-color: #181825;
                color: #585b70;
            }
            #StartBtn {
                background-color: #a6e3a1;
                color: #11111b;
            }
            #StartBtn:hover {
                background-color: #94e2d5;
            }
            #StopBtn {
                background-color: #f38ba8;
                color: #11111b;
            }
            #StopBtn:hover {
                background-color: #eba0ac;
            }
            QDoubleSpinBox, QSpinBox, QComboBox {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #89b4fa;
            }
            QComboBox::drop-down {
                border: none;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                background-color: #181825;
                border: 1px solid #313244;
            }
            QCheckBox::indicator:checked {
                background-color: #89b4fa;
            }
            QTableWidget {
                background-color: #181825;
                alternate-background-color: #1e1e2e;
                gridline-color: #313244;
                border-radius: 8px;
                border: none;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #89b4fa;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            #StatusIdle {
                color: #fab387;
                font-weight: bold;
            }
            #StatusActive {
                color: #a6e3a1;
                font-weight: bold;
            }
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
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)

        # Header
        header = QLabel("PrecisionClick")
        header.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #89b4fa; margin-bottom: 5px;")
        main_layout.addWidget(header)

        # --- Mode Switch ---
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Operation Mode:")
        mode_label.setStyleSheet("font-weight: bold; color: #a6adc8;")
        mode_layout.addWidget(mode_label)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Simple Repeating", "Macro Sequence"])
        self.mode_combo.currentIndexChanged.connect(self.toggle_mode)
        mode_layout.addWidget(self.mode_combo)

        self.show_reticles_checkbox = QCheckBox("Show Target Reticles")
        self.show_reticles_checkbox.setChecked(True)
        self.show_reticles_checkbox.toggled.connect(self.update_indicators)
        mode_layout.addWidget(self.show_reticles_checkbox)
        
        main_layout.addLayout(mode_layout)

        # --- Settings Card (Simple Mode) ---
        self.settings_card = QFrame()
        self.settings_card.setObjectName("Card")
        settings_layout = QVBoxLayout(self.settings_card)
        settings_layout.setContentsMargins(15, 15, 15, 15)
        
        settings_header = QLabel("CONFIGURATION")
        settings_header.setObjectName("CardHeader")
        settings_layout.addWidget(settings_header)

        grid = QGridLayout()
        grid.setSpacing(10)
        
        # Interval
        grid.addWidget(QLabel("Interval (s):"), 0, 0)
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.001, 3600.0)
        self.interval_spin.setValue(0.1)
        self.interval_spin.setSingleStep(0.01)
        self.interval_spin.valueChanged.connect(self.update_settings)
        grid.addWidget(self.interval_spin, 0, 1)

        # Variance
        grid.addWidget(QLabel("Variance (+/- s):"), 0, 2)
        self.variance_spin = QDoubleSpinBox()
        self.variance_spin.setRange(0.0, 10.0)
        self.variance_spin.setValue(0.0)
        self.variance_spin.setSingleStep(0.01)
        self.variance_spin.valueChanged.connect(self.update_settings)
        grid.addWidget(self.variance_spin, 0, 3)

        # Click Type
        grid.addWidget(QLabel("Click Type:"), 1, 0)
        self.button_combo = QComboBox()
        self.button_combo.addItems(["Left", "Right", "Middle"])
        self.button_combo.currentIndexChanged.connect(self.update_settings)
        grid.addWidget(self.button_combo, 1, 1)

        # Limit
        self.limit_checkbox = QCheckBox("Infinite")
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
        main_layout.addWidget(self.settings_card)

        # --- Location Card (Simple Mode) ---
        self.location_card = QFrame()
        self.location_card.setObjectName("Card")
        loc_layout = QVBoxLayout(self.location_card)
        loc_layout.setContentsMargins(15, 15, 15, 15)

        loc_header = QLabel("TARGET LOCATION")
        loc_header.setObjectName("CardHeader")
        loc_layout.addWidget(loc_header)

        loc_grid = QGridLayout()
        self.fixed_loc_checkbox = QCheckBox("Fixed Coordinates")
        self.fixed_loc_checkbox.toggled.connect(self.toggle_location)
        loc_grid.addWidget(self.fixed_loc_checkbox, 0, 0, 1, 2)

        loc_grid.addWidget(QLabel("X:"), 1, 0)
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 10000)
        self.x_spin.setEnabled(False)
        self.x_spin.valueChanged.connect(self.update_settings)
        self.x_spin.valueChanged.connect(self.update_indicators)
        loc_grid.addWidget(self.x_spin, 1, 1)

        loc_grid.addWidget(QLabel("Y:"), 1, 2)
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
        main_layout.addWidget(self.location_card)

        # --- Sequence Card (Sequence Mode) ---
        self.sequence_card = QFrame()
        self.sequence_card.setObjectName("Card")
        self.sequence_card.setVisible(False)
        seq_layout = QVBoxLayout(self.sequence_card)
        seq_layout.setContentsMargins(15, 15, 15, 15)

        seq_header = QLabel("MACRO SEQUENCE")
        seq_header.setObjectName("CardHeader")
        seq_layout.addWidget(seq_header)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["X", "Y", "Btn", "Delay (s)", "Var (s)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setFixedHeight(220)
        self.table.itemChanged.connect(self.update_indicators)
        seq_layout.addWidget(self.table)

        seq_btn_layout = QHBoxLayout()
        self.add_step_btn = QPushButton("+ Step")
        self.add_step_btn.clicked.connect(lambda: self.add_sequence_step())
        
        self.remove_step_btn = QPushButton("- Remove")
        self.remove_step_btn.clicked.connect(self.remove_sequence_step)
        
        self.clear_steps_btn = QPushButton("Clear")
        self.clear_steps_btn.clicked.connect(lambda: self.table.setRowCount(0))

        seq_btn_layout.addWidget(self.add_step_btn)
        seq_btn_layout.addWidget(self.remove_step_btn)
        seq_btn_layout.addWidget(self.clear_steps_btn)
        seq_layout.addLayout(seq_btn_layout)
        
        main_layout.addWidget(self.sequence_card)

        # --- Hotkey Card ---
        self.hotkey_card = QFrame()
        self.hotkey_card.setObjectName("Card")
        hot_layout = QVBoxLayout(self.hotkey_card)
        hot_layout.setContentsMargins(15, 15, 15, 15)

        hot_header = QLabel("GLOBAL HOTKEYS")
        hot_header.setObjectName("CardHeader")
        hot_layout.addWidget(hot_header)

        hk_btns = QHBoxLayout()
        self.start_key_btn = QPushButton(f"START: {self.start_key.upper()}")
        self.start_key_btn.clicked.connect(self.record_start_key)
        hk_btns.addWidget(self.start_key_btn)

        self.stop_key_btn = QPushButton(f"STOP: {self.stop_key.upper()}")
        self.stop_key_btn.clicked.connect(self.record_stop_key)
        hk_btns.addWidget(self.stop_key_btn)
        hot_layout.addLayout(hk_btns)

        main_layout.addWidget(self.hotkey_card)

        # --- Status & Actions ---
        status_card = QFrame()
        status_card.setObjectName("Card")
        stat_layout = QVBoxLayout(status_card)
        stat_layout.setContentsMargins(15, 15, 15, 15)
        
        self.status_label = QLabel("STATUS: IDLE")
        self.status_label.setObjectName("StatusIdle")
        self.status_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stat_layout.addWidget(self.status_label)

        self.count_label = QLabel("Total Clicks: 0")
        self.count_label.setFont(QFont("Segoe UI", 12))
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setStyleSheet("color: #a6adc8;")
        stat_layout.addWidget(self.count_label)
        
        main_layout.addWidget(status_card)

        # Main Action Buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("START EXECUTION")
        self.start_btn.setObjectName("StartBtn")
        self.start_btn.setFixedHeight(60)
        self.start_btn.clicked.connect(self.start_clicking)
        
        self.stop_btn = QPushButton("STOP EXECUTION")
        self.stop_btn.setObjectName("StopBtn")
        self.stop_btn.setFixedHeight(60)
        self.stop_btn.clicked.connect(self.stop_clicking)
        self.stop_btn.setEnabled(False)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        main_layout.addLayout(btn_layout)
        
        self.update_indicators()

    def toggle_mode(self, index):
        is_sequence = (index == 1)
        self.settings_card.setVisible(not is_sequence)
        self.location_card.setVisible(not is_sequence)
        self.sequence_card.setVisible(is_sequence)
        self.update_settings()
        self.update_indicators()

    def add_sequence_step(self, x=0, y=0):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        self.table.setItem(row, 0, QTableWidgetItem(str(x)))
        self.table.setItem(row, 1, QTableWidgetItem(str(y)))
        
        btn_combo = QComboBox()
        btn_combo.addItems(["Left", "Right", "Middle"])
        btn_combo.currentIndexChanged.connect(self.update_settings)
        self.table.setCellWidget(row, 2, btn_combo)
        
        self.table.setItem(row, 3, QTableWidgetItem("0.1"))
        self.table.setItem(row, 4, QTableWidgetItem("0.0"))
        self.update_indicators()

    def remove_sequence_step(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
            self.update_indicators()

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
        self.start_key_btn.setText("Press any key...")
        self.start_key_btn.setStyleSheet("background-color: #f9e2af; color: #11111b;") # Warm yellow for recording

    def record_stop_key(self):
        self.recording_stop = True
        self.recording_start = False
        self.stop_key_btn.setText("Press any key...")
        self.stop_key_btn.setStyleSheet("background-color: #f9e2af; color: #11111b;")

    def keyPressEvent(self, event):
        key_name = event.text().lower()
        if not key_name:
            return

        if self.recording_start:
            self.start_key = key_name
            self.recording_start = False
            self.start_key_btn.setText(f"START: {key_name.upper()}")
            self.start_key_btn.setStyleSheet("")
            self.setup_hotkeys()
        elif self.recording_stop:
            self.stop_key = key_name
            self.recording_stop = False
            self.stop_key_btn.setText(f"STOP: {key_name.upper()}")
            self.stop_key_btn.setStyleSheet("")
            self.setup_hotkeys()

    def capture_mouse_pos(self):
        if keyboard.is_pressed('p'):
            # Use QCursor to get screen coordinates that are consistent with Qt's scaling
            pos = self.cursor().pos()
            if self.mode_combo.currentIndex() == 0: # Simple Mode
                if self.fixed_loc_checkbox.isChecked():
                    self.x_spin.setValue(pos.x())
                    self.y_spin.setValue(pos.y())
            else: # Sequence Mode
                self.add_sequence_step(pos.x(), pos.y())
                time.sleep(0.2) # Debounce
            self.update_indicators()

    def update_settings(self):
        self.worker.mode = 'simple' if self.mode_combo.currentIndex() == 0 else 'sequence'
        
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
