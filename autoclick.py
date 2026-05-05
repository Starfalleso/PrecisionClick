import sys
import time
import threading
import pyautogui
import keyboard
import random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QDoubleSpinBox, QSpinBox, QPushButton, QCheckBox, QFrame,
    QComboBox, QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon

# Disable pyautogui's default 0.1s delay to allow user-defined intervals
pyautogui.PAUSE = 0

class ClickWorker(QThread):
    """Worker thread for the clicking loop to keep UI responsive."""
    clicked = pyqtSignal(int)
    finished = pyqtSignal()
    status_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.running = False
        self.interval = 0.1
        self.random_variance = 0.0
        self.limit = None
        self.count = 0
        self._stop_requested = False
        self.button = 'left'
        self.fixed_location = False
        self.x = 0
        self.y = 0

    def stop(self):
        self._stop_requested = True[]
        self.running = False

    def run(self):
        self._stop_requested = False
        while not self._stop_requested:
            if self.running:
                # Execute Click
                if self.fixed_location:
                    pyautogui.click(x=self.x, y=self.y, button=self.button)
                else:
                    pyautogui.click(button=self.button)
                
                self.count += 1
                self.clicked.emit(self.count)
                
                if self.limit and self.count >= self.limit:
                    self.running = False
                    self.status_changed.emit(False)
                    break
                
                # Calculate next interval with variance
                current_delay = self.interval
                if self.random_variance > 0:
                    current_delay += random.uniform(-self.random_variance, self.random_variance)
                    current_delay = max(0.001, current_delay)

                # Sleep in small chunks to remain responsive to stop requests
                start_sleep = time.time()
                while time.time() - start_sleep < current_delay:
                    if not self.running or self._stop_requested:
                        break
                    time.sleep(0.005)
            else:
                time.sleep(0.05)

class AutoClickerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PrecisionClick")
        self.setMinimumWidth(450)
        
        # State
        self.start_key = '['
        self.stop_key = ']'
        self.recording_start = False
        self.recording_stop = False
        
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

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QWidget {
                color: #E0E0E0;
                font-family: 'Segoe UI', Arial;
            }
            QGroupBox {
                border: 1px solid #333333;
                border-radius: 8px;
                margin-top: 20px;
                font-weight: bold;
                background-color: #1E1E1E;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #2196F3;
            }
            QPushButton {
                background-color: #333333;
                color: white;
                border-radius: 5px;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:pressed {
                background-color: #555555;
            }
            QPushButton:disabled {
                background-color: #222222;
                color: #555555;
            }
            QDoubleSpinBox, QSpinBox, QComboBox {
                background-color: #2D2D2D;
                color: white;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 4px;
            }
            QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #2196F3;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
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
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("PrecisionClick")
        header.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #2196F3; margin-bottom: 10px;")
        main_layout.addWidget(header)

        # --- Settings Group ---
        settings_group = QGroupBox("Configuration")
        settings_layout = QGridLayout(settings_group)
        settings_layout.setContentsMargins(15, 25, 15, 15)
        settings_layout.setSpacing(10)
        
        # Interval
        settings_layout.addWidget(QLabel("Click Interval (s):"), 0, 0)
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.001, 3600.0)
        self.interval_spin.setValue(0.1)
        self.interval_spin.setSingleStep(0.01)
        self.interval_spin.valueChanged.connect(self.update_settings)
        settings_layout.addWidget(self.interval_spin, 0, 1)

        # Variance
        settings_layout.addWidget(QLabel("Random Variance:"), 0, 2)
        self.variance_spin = QDoubleSpinBox()
        self.variance_spin.setRange(0.0, 10.0)
        self.variance_spin.setValue(0.0)
        self.variance_spin.setSingleStep(0.01)
        self.variance_spin.valueChanged.connect(self.update_settings)
        settings_layout.addWidget(self.variance_spin, 0, 3)

        # Click Type
        settings_layout.addWidget(QLabel("Mouse Button:"), 1, 0)
        self.button_combo = QComboBox()
        self.button_combo.addItems(["Left", "Right", "Middle"])
        self.button_combo.currentIndexChanged.connect(self.update_settings)
        settings_layout.addWidget(self.button_combo, 1, 1)

        # Limit
        self.limit_checkbox = QCheckBox("Infinite Mode")
        self.limit_checkbox.setChecked(True)
        self.limit_checkbox.toggled.connect(self.toggle_limit)
        settings_layout.addWidget(self.limit_checkbox, 1, 2)
        
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 10000000)
        self.limit_spin.setValue(100)
        self.limit_spin.setEnabled(False)
        self.limit_spin.valueChanged.connect(self.update_settings)
        settings_layout.addWidget(self.limit_spin, 1, 3)
        
        main_layout.addWidget(settings_group)

        # --- Location Group ---
        location_group = QGroupBox("Target Location")
        location_layout = QGridLayout(location_group)
        location_layout.setContentsMargins(15, 25, 15, 15)
        location_layout.setSpacing(10)

        self.fixed_loc_checkbox = QCheckBox("Enabled Fixed Coordinates")
        self.fixed_loc_checkbox.toggled.connect(self.toggle_location)
        location_layout.addWidget(self.fixed_loc_checkbox, 0, 0, 1, 2)

        location_layout.addWidget(QLabel("X Pos:"), 1, 0)
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 10000)
        self.x_spin.setEnabled(False)
        self.x_spin.valueChanged.connect(self.update_settings)
        location_layout.addWidget(self.x_spin, 1, 1)

        location_layout.addWidget(QLabel("Y Pos:"), 1, 2)
        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 10000)
        self.y_spin.setEnabled(False)
        self.y_spin.valueChanged.connect(self.update_settings)
        location_layout.addWidget(self.y_spin, 1, 3)

        self.pick_btn = QPushButton("Capture (P)")
        self.pick_btn.setEnabled(False)
        self.pick_btn.setToolTip("Press 'P' while hovering to capture coordinates")
        location_layout.addWidget(self.pick_btn, 1, 4)
        
        main_layout.addWidget(location_group)

        # --- Hotkey Group ---
        hotkey_group = QGroupBox("System Hotkeys")
        hotkey_layout = QHBoxLayout(hotkey_group)
        hotkey_layout.setContentsMargins(15, 25, 15, 15)

        self.start_key_btn = QPushButton(f"START KEY: {self.start_key.upper()}")
        self.start_key_btn.clicked.connect(self.record_start_key)
        hotkey_layout.addWidget(self.start_key_btn)

        self.stop_key_btn = QPushButton(f"STOP KEY: {self.stop_key.upper()}")
        self.stop_key_btn.clicked.connect(self.record_stop_key)
        hotkey_layout.addWidget(self.stop_key_btn)

        main_layout.addWidget(hotkey_group)

        # --- Status Display ---
        status_frame = QFrame()
        status_layout = QVBoxLayout(status_frame)
        
        self.status_label = QLabel("STATUS: IDLE")
        self.status_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #FFA000;")
        status_layout.addWidget(self.status_label)

        self.count_label = QLabel("Clicks: 0")
        self.count_label.setFont(QFont("Segoe UI", 14))
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.count_label)
        
        main_layout.addWidget(status_frame)

        # Main Action Buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("START EXECUTION")
        self.start_btn.setFixedHeight(55)
        self.start_btn.setStyleSheet("background-color: #2E7D32; color: white; font-size: 16px;")
        self.start_btn.clicked.connect(self.start_clicking)
        
        self.stop_btn = QPushButton("STOP EXECUTION")
        self.stop_btn.setFixedHeight(55)
        self.stop_btn.setStyleSheet("background-color: #C62828; color: white; font-size: 16px;")
        self.stop_btn.clicked.connect(self.stop_clicking)
        self.stop_btn.setEnabled(False)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        main_layout.addLayout(btn_layout)

    def toggle_limit(self, checked):
        self.limit_spin.setEnabled(not checked)
        self.update_settings()

    def toggle_location(self, checked):
        self.x_spin.setEnabled(checked)
        self.y_spin.setEnabled(checked)
        self.pick_btn.setEnabled(checked)
        self.update_settings()

    def record_start_key(self):
        self.recording_start = True
        self.recording_stop = False
        self.start_key_btn.setText("Press any key...")
        self.start_key_btn.setStyleSheet("background-color: #1565C0; color: white;")

    def record_stop_key(self):
        self.recording_stop = True
        self.recording_start = False
        self.stop_key_btn.setText("Press any key...")
        self.stop_key_btn.setStyleSheet("background-color: #1565C0; color: white;")

    def keyPressEvent(self, event):
        key_name = event.text().lower()
        if not key_name:
            return

        if self.recording_start:
            self.start_key = key_name
            self.recording_start = False
            self.start_key_btn.setText(f"START KEY: {key_name.upper()}")
            self.start_key_btn.setStyleSheet("")
            self.setup_hotkeys()
        elif self.recording_stop:
            self.stop_key = key_name
            self.recording_stop = False
            self.stop_key_btn.setText(f"STOP KEY: {key_name.upper()}")
            self.stop_key_btn.setStyleSheet("")
            self.setup_hotkeys()

    def capture_mouse_pos(self):
        # Listen for 'P' key to capture mouse position if location group is active
        if self.fixed_loc_checkbox.isChecked() and keyboard.is_pressed('p'):
            pos = pyautogui.position()
            self.x_spin.setValue(pos.x)
            self.y_spin.setValue(pos.y)

    def update_settings(self):
        self.worker.interval = self.interval_spin.value()
        self.worker.random_variance = self.variance_spin.value()
        self.worker.button = self.button_combo.currentText().lower()
        self.worker.fixed_location = self.fixed_loc_checkbox.isChecked()
        self.worker.x = self.x_spin.value()
        self.worker.y = self.y_spin.value()
        
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
            self.status_label.setStyleSheet("color: #66BB6A; font-weight: bold;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.status_label.setText("STATUS: IDLE")
            self.status_label.setStyleSheet("color: #FFA726; font-weight: bold;")
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
