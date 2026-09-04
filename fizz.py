import sys
import os
import json
from datetime import datetime
from PIL import Image
from google import genai
from google.genai import types

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QTextEdit, QPushButton, QComboBox, 
    QInputDialog, QMessageBox, QFileDialog, QLabel, QShortcut, QDialog, QSpinBox,
    QMenu, QFormLayout, QFontComboBox, QTabBar, QStackedWidget, QSizeGrip,
    QStyleOption, QStyle, QCheckBox
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer, QUrl
from PyQt5.QtGui import QKeySequence, QFont, QPainter, QColor, QDesktopServices
from PyQt5.QtPrintSupport import QPrinter

# ============================================================
# CONFIGURATION & CONSTANTS
# ============================================================
MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-pro-preview"
]

CHAT_DIR = os.path.expanduser("~/Gemini Chats")
KEYS_FILE = os.path.expanduser("~/.gemini_api_keys.json")
CONFIG_FILE = os.path.expanduser("~/.gemini_gui_config.json")
DEBUG_LOG = os.path.join(CHAT_DIR, "api_debug.log")
os.makedirs(CHAT_DIR, exist_ok=True)

# ============================================================
# THEME STYLESHEETS (QSS)
# ============================================================
THEMES = {
    "Classic Light": """
        QWidget#MainWindow { border: 1px solid #aaa; }
        QWidget#TitleBar { background-color: #e0e0e0; }
        QPushButton#WindowCtrl { border: none; background: transparent; font-size: 14px; padding: 5px 12px; }
        QPushButton#WindowCtrl:hover { background-color: #d0d0d0; }
        QPushButton#CloseBtn:hover { background-color: #e81123; color: white; }
    """,
    "Night Mode": """
        QWidget { background-color: #1e1e1e; color: #d4d4d4; }
        QWidget#MainWindow { border: 1px solid #3e3e42; }
        QWidget#TitleBar { background-color: #2d2d30; }
        QTextBrowser, QTextEdit { background-color: #252526; color: #d4d4d4; border: 1px solid #3e3e42; border-radius: 4px; }
        QPushButton { background-color: #333333; color: #ffffff; border: 1px solid #444; border-radius: 3px; padding: 4px 10px; }
        QPushButton:hover { background-color: #444444; }
        QPushButton:disabled { background-color: #222; color: #666; }
        QComboBox, QSpinBox { background-color: #2d2d30; color: #fff; border: 1px solid #3e3e42; padding: 3px; border-radius: 3px; }
        QDialog { background-color: #1e1e1e; }
        QTabBar::tab { background: #2d2d30; border: none; border-right: 1px solid #1e1e1e; padding: 8px 15px; color: #888; }
        QTabBar::tab:selected { background: #1e1e1e; color: #fff; }
        QPushButton#WindowCtrl { border: none; background: transparent; font-size: 14px; padding: 5px 12px; }
        QPushButton#WindowCtrl:hover { background-color: #3e3e42; }
        QPushButton#CloseBtn:hover { background-color: #e81123; color: white; }
    """,
    "Intelligent Grayscale": """
        QWidget { background-color: #efefef; color: #1c1c1c; }
        QWidget#MainWindow { border: 1px solid #b0b0b0; }
        QWidget#TitleBar { background-color: #dfdfdf; }
        QTextBrowser, QTextEdit { background-color: #f7f7f7; color: #111111; border: 1px solid #b0b0b0; border-radius: 4px; }
        QPushButton { background-color: #dfdfdf; color: #111111; border: 1px solid #999999; border-radius: 3px; padding: 4px 10px; }
        QPushButton:hover { background-color: #cccccc; }
        QPushButton:disabled { background-color: #e5e5e5; color: #888888; }
        QComboBox, QSpinBox { background-color: #f7f7f7; color: #111111; border: 1px solid #b0b0b0; padding: 3px; border-radius: 3px; }
        QDialog { background-color: #efefef; }
        QTabBar::tab { background: #dfdfdf; border: none; border-right: 1px solid #b0b0b0; padding: 8px 15px; color: #555; }
        QTabBar::tab:selected { background: #efefef; color: #111; }
        QPushButton#WindowCtrl { border: none; background: transparent; font-size: 14px; padding: 5px 12px; }
        QPushButton#WindowCtrl:hover { background-color: #cccccc; }
        QPushButton#CloseBtn:hover { background-color: #e81123; color: white; }
    """,
    "Warm Sepia": """
        QWidget { background-color: #f6eedb; color: #3b2f2f; }
        QWidget#MainWindow { border: 1px solid #d4c5a9; }
        QWidget#TitleBar { background-color: #ede6d6; }
        QTextBrowser, QTextEdit { background-color: #fcf6e8; color: #2e2323; border: 1px solid #d4c5a9; border-radius: 4px; }
        QPushButton { background-color: #ebdcc0; color: #332424; border: 1px solid #c2b090; border-radius: 3px; padding: 4px 10px; }
        QPushButton:hover { background-color: #dfceb0; }
        QPushButton:disabled { background-color: #ede6d6; color: #9c8e7c; }
        QComboBox, QSpinBox { background-color: #fcf6e8; color: #3b2f2f; border: 1px solid #d4c5a9; padding: 3px; border-radius: 3px; }
        QDialog { background-color: #f6eedb; }
        QTabBar::tab { background: #ede6d6; border: none; border-right: 1px solid #d4c5a9; padding: 8px 15px; color: #7c7263; }
        QTabBar::tab:selected { background: #f6eedb; color: #2e2323; }
        QPushButton#WindowCtrl { border: none; background: transparent; font-size: 14px; padding: 5px 12px; }
        QPushButton#WindowCtrl:hover { background-color: #dfceb0; }
        QPushButton#CloseBtn:hover { background-color: #e81123; color: white; }
    """,
    "High Contrast": """
        QWidget { background-color: #000000; color: #ffffff; }
        QWidget#MainWindow { border: 2px solid #ffffff; }
        QWidget#TitleBar { background-color: #000000; border-bottom: 2px solid #ffffff; }
        QTextBrowser, QTextEdit { background-color: #000000; color: #ffffff; border: 2px solid #ffffff; }
        QPushButton { background-color: #000000; color: #ffffff; border: 2px solid #ffffff; padding: 4px 10px; font-weight: bold; }
        QPushButton:hover { background-color: #ffffff; color: #000000; }
        QPushButton:disabled { border-color: #555555; color: #555555; }
        QComboBox, QSpinBox { background-color: #000000; color: #ffffff; border: 2px solid #ffffff; padding: 3px; }
        QDialog { background-color: #000000; }
        QTabBar::tab { background: #000000; border: 2px solid #555555; padding: 8px 15px; color: #aaaaaa; }
        QTabBar::tab:selected { background: #000000; border: 2px solid #ffffff; color: #ffffff; }
        QPushButton#WindowCtrl { border: 2px solid transparent; background: transparent; font-size: 14px; padding: 5px 12px; }
        QPushButton#WindowCtrl:hover { background-color: #ffffff; color: #000000; }
        QPushButton#CloseBtn:hover { background-color: #ffffff; color: #000000; }
    """
}

# ============================================================
# BACKGROUND API WORKER
# ============================================================
class ApiWorker(QThread):
    finished = pyqtSignal(str, str)
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, prompt, history, selected_model, api_key, image_path=None):
        super().__init__()
        self.prompt = prompt
        self.history = history
        self.selected_model = selected_model
        self.api_key = api_key
        self.image_path = image_path

    def write_debug_log(self, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass

    def run(self):
        masked_key = f"...{self.api_key[-8:]}" if len(self.api_key) > 8 else self.api_key
        
        self.write_debug_log("-" * 50)
        self.write_debug_log(f"NEW REQUEST INITIATED")
        self.write_debug_log(f"Key in use: {masked_key}")
        self.write_debug_log(f"Model precisely selected from Dropdown: '{self.selected_model}'")
        
        try:
            self.write_debug_log("Initializing genai.Client...")
            client = genai.Client(api_key=self.api_key)
        except Exception as e:
            err = f"Failed to initialize client: {str(e)}"
            self.write_debug_log(f"CRITICAL ERROR: {err}")
            self.error.emit(f"Failed to initialize client [Key: {masked_key}]: {str(e)}")
            return

        payload = self.prompt
        if self.image_path and os.path.exists(self.image_path):
            try:
                self.write_debug_log(f"Loading attached image: {self.image_path}")
                img = Image.open(self.image_path)
                payload = [img, self.prompt]
            except Exception as e:
                err = f"Error loading image: {str(e)}"
                self.write_debug_log(f"CRITICAL ERROR: {err}")
                self.error.emit(err)
                return

        try:
            self.write_debug_log(f"Executing client.chats.create() targeting model '{self.selected_model}' explicitly...")
            chat = client.chats.create(
                model=self.selected_model,
                history=self.history
            )
            self.write_debug_log("Network call fired (send_message). Awaiting Google servers...")
            response = chat.send_message(message=payload)
            self.write_debug_log(f"SUCCESS. Response received from '{self.selected_model}'.")
            self.finished.emit(response.text, self.selected_model)
        except Exception as e:
            err_str = str(e)
            self.write_debug_log(f"API FAILURE CAUGHT for '{self.selected_model}': {err_str}")
            self.error.emit(f"API Error ({self.selected_model}) [Key: {masked_key}]: {err_str}")


# ============================================================
# CUSTOM UI WIDGET: FLOATING PROMPT DIALOG
# ============================================================
class PromptDialog(QDialog):
    def __init__(self, parent=None, active_font=None, initial_text="", initial_image=None, default_model_idx=0):
        super().__init__(parent)
        self.setWindowTitle("New Prompt")
        self.resize(550, 250)
        self.image_path = initial_image
        
        layout = QVBoxLayout(self)
        
        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Type your prompt here...\n(Press Ctrl+Enter to send)")
        
        if initial_text:
            self.input_box.setPlainText(initial_text)
            
        if active_font:
            self.input_box.setFont(active_font)
        
        layout.addWidget(self.input_box)
        
        bottom_row = QHBoxLayout()
        
        model_label = QLabel("&Model:")
        self.model_selector = QComboBox()
        self.model_selector.addItems(MODELS)
        self.model_selector.setCurrentIndex(default_model_idx)
        model_label.setBuddy(self.model_selector)
        bottom_row.addWidget(model_label)
        bottom_row.addWidget(self.model_selector)
        
        bottom_row.addSpacing(15)
        
        self.attach_btn = QPushButton("&Attach Image")
        self.attach_btn.clicked.connect(self.attach_image)
        bottom_row.addWidget(self.attach_btn)
        
        self.file_label = QLabel("")
        self.file_label.setStyleSheet("color: gray; font-style: italic;")
        if self.image_path:
            self.file_label.setText(os.path.basename(self.image_path))
            
        bottom_row.addWidget(self.file_label)
        
        bottom_row.addStretch()
        
        # Open in New Tab Checkbox
        self.new_tab_checkbox = QCheckBox("Open in &New Tab")
        bottom_row.addWidget(self.new_tab_checkbox)
        
        self.send_btn = QPushButton("&Send")
        self.send_btn.clicked.connect(self.accept)
        bottom_row.addWidget(self.send_btn)
        
        layout.addLayout(bottom_row)
        
        self.shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.shortcut.activated.connect(self.accept)

    def attach_image(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if filepath:
            self.image_path = filepath
            self.file_label.setText(os.path.basename(filepath))

    def get_data(self):
        return self.input_box.toPlainText().strip(), self.image_path, self.model_selector.currentText(), self.new_tab_checkbox.isChecked()


# ============================================================
# CUSTOM TITLE BAR (For Frameless Window)
# ============================================================
class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("TitleBar")
        self.setFixedHeight(35)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)

        self.tab_bar = QTabBar()
        self.tab_bar.setTabsClosable(True)
        self.tab_bar.setExpanding(False)
        self.layout.addWidget(self.tab_bar)

        self.new_tab_btn = QPushButton("+")
        self.new_tab_btn.setFixedSize(26, 26)
        self.new_tab_btn.setToolTip("New Chat (Ctrl+T)")
        self.layout.addWidget(self.new_tab_btn)

        self.layout.addStretch()

        self.status_label = QLabel("Ready")
        self.layout.addWidget(self.status_label)
        self.layout.addSpacing(10)

        size_label = QLabel("Si&ze:")
        self.font_spinner = QSpinBox()
        self.font_spinner.setRange(8, 48)
        self.font_spinner.setValue(11)
        self.font_spinner.valueChanged.connect(self.parent_window.apply_font)
        size_label.setBuddy(self.font_spinner)
        self.layout.addWidget(size_label)
        self.layout.addWidget(self.font_spinner)

        width_label = QLabel("&Width:")
        self.width_selector = QComboBox()
        self.width_selector.addItems(["100%", "80%", "60%", "40%"])
        self.width_selector.currentTextChanged.connect(self.parent_window.apply_width)
        width_label.setBuddy(self.width_selector)
        self.layout.addWidget(width_label)
        self.layout.addWidget(self.width_selector)

        self.layout.addSpacing(10)

        self.prompt_btn = QPushButton("💬 &Prompt")
        self.prompt_btn.setStyleSheet("font-weight: bold; padding: 2px 10px;")
        self.prompt_btn.setToolTip("Open Prompt (Ctrl+Space)")
        self.layout.addWidget(self.prompt_btn)
        
        self.menu_btn = QPushButton("🚀")
        self.menu_btn.setToolTip("Menu & Settings (Alt+M)")
        robot_font = self.menu_btn.font()
        robot_font.setPointSize(14)
        self.menu_btn.setFont(robot_font)
        self.menu_btn.setFixedSize(30, 30)
        self.menu_btn.setShortcut("Alt+M")
        self.layout.addWidget(self.menu_btn)

        self.layout.addSpacing(10)

        self.min_btn = QPushButton("—")
        self.min_btn.setObjectName("WindowCtrl")
        self.min_btn.clicked.connect(self.parent_window.showMinimized)
        self.layout.addWidget(self.min_btn)

        self.max_btn = QPushButton("☐")
        self.max_btn.setObjectName("WindowCtrl")
        self.max_btn.clicked.connect(self.parent_window.toggle_maximize)
        self.layout.addWidget(self.max_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.setStyleSheet("border: none; background: transparent; font-size: 14px; padding: 5px 12px;")
        self.close_btn.clicked.connect(self.parent_window.close)
        self.layout.addWidget(self.close_btn)

        self.start_pos = None

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)
        
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(0.18) 
        
        font = self.font()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        
        painter.setPen(QColor(130, 130, 130)) 
        painter.drawText(self.rect(), Qt.AlignCenter, "BenevolentGemini by Dr. Bishnu Goswami")
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.globalPos()
            self.window_pos = self.parent_window.pos()

    def mouseMoveEvent(self, event):
        if self.start_pos and not self.parent_window.isMaximized():
            delta = event.globalPos() - self.start_pos
            self.parent_window.move(self.window_pos + delta)

    def mouseReleaseEvent(self, event):
        self.start_pos = None
        
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.parent_window.toggle_maximize()
            
    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        
        display_menu = context_menu.addMenu("📅 &Tab Display Format")
        time_action = display_menu.addAction("&Time Only (e.g. Chat 14:30)")
        datetime_action = display_menu.addAction("&Date & Time (e.g. Sep 04, 14:30)")
        name_action = display_menu.addAction("&Raw Filename")
        
        context_menu.addSeparator()
        close_all_action = context_menu.addAction("❌ &Close All Tabs")
        
        action = context_menu.exec_(self.mapToGlobal(event.pos()))
        
        if action == time_action:
            self.parent_window.update_tab_names("time")
        elif action == datetime_action:
            self.parent_window.update_tab_names("datetime")
        elif action == name_action:
            self.parent_window.update_tab_names("name")
        elif action == close_all_action:
            self.parent_window.close_all_tabs()


# ============================================================
# CHAT TAB WIDGET
# ============================================================
class ChatTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.left_spacer = QWidget()
        self.right_spacer = QWidget()
        
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        
        self.layout.addWidget(self.left_spacer)
        self.layout.addWidget(self.browser)
        self.layout.addWidget(self.right_spacer)
        
        self.set_margins(0, 100)
        
        self.history = []
        self.current_chat_path = None
        self.worker = None

    def set_margins(self, margin_pct, center_pct):
        self.layout.setStretch(0, margin_pct)
        self.layout.setStretch(1, center_pct)
        self.layout.setStretch(2, margin_pct)


# ============================================================
# MAIN GUI WINDOW
# ============================================================
class GeminiGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setObjectName("MainWindow")
        
        self.setWindowTitle("BenevolentGemini")
        self.current_font = QFont("sans-serif", 11)
        self.tab_display_mode = "time"
        
        self.recovered_prompt = ""
        self.recovered_image = None
        self.current_model_index = 0

        self.init_ui()
        self.load_persistent_settings()
        
        QTimer.singleShot(200, self.open_prompt_dialog)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(1, 1, 1, 1)
        self.main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        self.main_layout.addWidget(self.title_bar)
        
        self.title_bar.new_tab_btn.clicked.connect(self.new_chat)
        self.title_bar.tab_bar.tabCloseRequested.connect(self.close_tab)
        self.title_bar.tab_bar.currentChanged.connect(self.change_tab)
        self.title_bar.prompt_btn.clicked.connect(self.open_prompt_dialog)

        self.setup_settings_dialog()
        
        # Build Main Global Menu
        self.main_menu = QMenu(self)
        
        action_new = self.main_menu.addAction("✨ &New Chat")
        action_new.setShortcut("Ctrl+T")
        action_new.triggered.connect(self.new_chat)
        
        action_resume = self.main_menu.addAction("📂 &Resume Chat")
        action_resume.setShortcut("Ctrl+O")
        action_resume.triggered.connect(self.resume_chat_dialog)
        
        action_export = self.main_menu.addAction("📄 &Export PDF")
        action_export.setShortcut("Ctrl+E")
        action_export.triggered.connect(self.export_pdf)
        
        self.main_menu.addSeparator()
        
        action_settings = self.main_menu.addAction("⚙️ &Settings")
        action_settings.setShortcut("Ctrl+S")
        action_settings.triggered.connect(self.open_settings)
        
        action_help = self.main_menu.addAction("❓ &Help")
        action_help.setShortcut("F1")
        action_help.triggered.connect(self.show_help)
        
        self.title_bar.menu_btn.setMenu(self.main_menu)
        
        # Add actions to window so shortcuts work globally
        self.addActions(self.main_menu.actions())

        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        self.size_grip = QSizeGrip(self)

        self.prompt_shortcut = QShortcut(QKeySequence("Ctrl+Space"), self)
        self.prompt_shortcut.activated.connect(self.open_prompt_dialog)
        
        self.close_tab_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        self.close_tab_shortcut.activated.connect(lambda: self.close_tab(self.title_bar.tab_bar.currentIndex()))

        self.next_tab_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), self)
        self.next_tab_shortcut.activated.connect(self.next_tab)

        self.fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        self.fullscreen_shortcut_alt = QShortcut(QKeySequence("Ctrl+F"), self)
        self.fullscreen_shortcut_alt.activated.connect(self.toggle_fullscreen)

        self.maximize_shortcut = QShortcut(QKeySequence("Ctrl+Up"), self)
        self.maximize_shortcut.activated.connect(self.showMaximized)
        
        self.normal_shortcut = QShortcut(QKeySequence("Ctrl+Down"), self)
        self.normal_shortcut.activated.connect(self.showNormal)

    def update_config(self, **kwargs):
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                pass
                
        config.update(kwargs)
        
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f)
        except Exception:
            pass

    def load_persistent_settings(self):
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                pass

        self.tab_display_mode = config.get("tab_display_mode", "time")
        
        theme = config.get("theme", "Classic Light")
        self.theme_selector.blockSignals(True)
        self.theme_selector.setCurrentText(theme)
        self.theme_selector.blockSignals(False)
        self.apply_theme(theme)

        font_family = config.get("font_family", "sans-serif")
        font_size = config.get("font_size", 11)
        self.font_selector.blockSignals(True)
        self.font_selector.setCurrentFont(QFont(font_family))
        self.font_selector.blockSignals(False)
        
        self.title_bar.font_spinner.blockSignals(True)
        self.title_bar.font_spinner.setValue(font_size)
        self.title_bar.font_spinner.blockSignals(False)
        self.apply_font()

        width_pct = config.get("width_pct", "100%")
        self.title_bar.width_selector.blockSignals(True)
        self.title_bar.width_selector.setCurrentText(width_pct)
        self.title_bar.width_selector.blockSignals(False)

        restored = False
        saved_tabs = config.get("session_tabs", [])
        for path in saved_tabs:
            if os.path.exists(path):
                self.load_chat_from_path(path)
                restored = True
                
        if not restored:
            self.new_chat()

    def setup_settings_dialog(self):
        self.settings_dialog = QDialog(self)
        self.settings_dialog.setWindowTitle("Preferences & Diagnostics")
        self.settings_dialog.resize(320, 230)
        
        form = QFormLayout(self.settings_dialog)

        key_widget = QWidget()
        key_layout = QHBoxLayout(key_widget)
        key_layout.setContentsMargins(0, 0, 0, 0)
        self.key_selector = QComboBox()
        self.load_keys()
        key_layout.addWidget(self.key_selector)
        self.add_key_btn = QPushButton("&Add")
        self.add_key_btn.clicked.connect(self.add_key)
        key_layout.addWidget(self.add_key_btn)
        
        key_label = QLabel("&Key:")
        key_label.setBuddy(self.key_selector)
        form.addRow(key_label, key_widget)

        self.theme_selector = QComboBox()
        self.theme_selector.addItems(list(THEMES.keys()))
        self.theme_selector.currentTextChanged.connect(self.apply_theme)
        form.addRow("&Theme:", self.theme_selector)

        self.font_selector = QFontComboBox()
        self.font_selector.currentFontChanged.connect(self.apply_font)
        form.addRow("&Global Font:", self.font_selector)
        
        self.view_log_btn = QPushButton("&View Detailed API Log")
        self.view_log_btn.clicked.connect(self.open_debug_log)
        form.addRow("", self.view_log_btn)
        
        self.last_log_label = QLabel("No logs available yet.")
        self.last_log_label.setStyleSheet("color: #888; font-style: italic; margin-top: 10px;")
        form.addRow("Last Output:", self.last_log_label)
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if "last_log" in config:
                        self.last_log_label.setText(config["last_log"])
            except Exception:
                pass
                
    def open_debug_log(self):
        if os.path.exists(DEBUG_LOG):
            QDesktopServices.openUrl(QUrl.fromLocalFile(DEBUG_LOG))
        else:
            QMessageBox.information(self, "No Log", "No API requests have been logged yet.")
        
    def open_settings(self):
        self.settings_dialog.exec_()

    # ============================================================
    # WINDOW & TAB MANAGEMENT
    # ============================================================
    def closeEvent(self, event):
        open_tabs = []
        for i in range(self.stack.count()):
            tab = self.stack.widget(i)
            if hasattr(tab, "current_chat_path") and tab.current_chat_path:
                open_tabs.append(tab.current_chat_path)
                
        self.update_config(session_tabs=open_tabs)
        event.accept()

    def resizeEvent(self, event):
        self.size_grip.move(self.width() - self.size_grip.width(), self.height() - self.size_grip.height())
        super().resizeEvent(event)

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.title_bar.setVisible(True)
        else:
            self.showFullScreen()
            self.title_bar.setVisible(False)

    def change_tab(self, index):
        if index >= 0:
            self.stack.setCurrentIndex(index)

    def next_tab(self):
        if self.title_bar.tab_bar.count() > 1:
            next_idx = (self.title_bar.tab_bar.currentIndex() + 1) % self.title_bar.tab_bar.count()
            self.title_bar.tab_bar.setCurrentIndex(next_idx)

    def close_tab(self, index):
        if self.title_bar.tab_bar.count() > 1:
            self.title_bar.tab_bar.removeTab(index)
            widget_to_remove = self.stack.widget(index)
            self.stack.removeWidget(widget_to_remove)
            widget_to_remove.deleteLater()
        else:
            QMessageBox.information(self, "Notice", "You cannot close the last remaining chat tab.")
            
    def close_all_tabs(self):
        reply = QMessageBox.question(self, "Close All Tabs", 
                                     "Are you sure you want to clear all open tabs? Your history will remain saved.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            for i in range(self.stack.count() - 1, -1, -1):
                self.title_bar.tab_bar.removeTab(i)
                widget = self.stack.widget(i)
                self.stack.removeWidget(widget)
                widget.deleteLater()
            
            self.new_chat()

    def update_tab_names(self, mode):
        self.tab_display_mode = mode
        for i in range(self.stack.count()):
            tab = self.stack.widget(i)
            if hasattr(tab, "current_chat_path") and tab.current_chat_path:
                base_name = os.path.basename(tab.current_chat_path).replace(".md", "")
                try:
                    dt = datetime.strptime(base_name, "%Y-%m-%d_%H-%M-%S")
                    if mode == "time":
                        title = f"Chat {dt.strftime('%H:%M')}"
                    elif mode == "datetime":
                        title = dt.strftime("%b %d, %H:%M")
                    else:
                        title = base_name
                except ValueError:
                    title = base_name[:12]
                self.title_bar.tab_bar.setTabText(i, title)
                
        self.update_config(tab_display_mode=mode)

    def new_chat(self):
        tab = ChatTab()
        filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.md")
        tab.current_chat_path = os.path.join(CHAT_DIR, filename)
        
        with open(tab.current_chat_path, "w", encoding="utf-8") as f:
            f.write("")

        tab.browser.setFont(self.current_font)
        self.apply_width_to_tab(tab)
        
        self.stack.addWidget(tab)
        idx = self.title_bar.tab_bar.addTab("New Chat")
        self.title_bar.tab_bar.setCurrentIndex(idx)
        self.title_bar.status_label.setText("New chat tab opened.")
        
        self.update_tab_names(self.tab_display_mode)

    def load_chat_from_path(self, filepath):
        tab = ChatTab()
        tab.current_chat_path = filepath
        tab.history = self.parse_markdown_chat(filepath)
        
        tab.browser.setFont(self.current_font)
        self.apply_width_to_tab(tab)
        
        self.stack.addWidget(tab)
        
        tooltip_text = "New Chat"
        if tab.history:
            for item in tab.history:
                if item.role == "user":
                    text = item.parts[0].text
                    tooltip_text = text if len(text) <= 97 else text[:97] + "..."
                    break
                    
        idx = self.title_bar.tab_bar.addTab("Loading...")
        self.title_bar.tab_bar.setTabToolTip(idx, tooltip_text)
        self.title_bar.tab_bar.setCurrentIndex(idx)
        
        self.update_tab_names(self.tab_display_mode)
        self.render_entire_chat(tab)

    # ============================================================
    # THEME, FONT, & UI FUNCTIONS
    # ============================================================
    def apply_theme(self, theme_name):
        qss = THEMES.get(theme_name, "")
        QApplication.instance().setStyleSheet(qss)
        self.update_config(theme=theme_name)

    def apply_width(self, *args):
        width_pct = self.title_bar.width_selector.currentText()
        for i in range(self.stack.count()):
            tab = self.stack.widget(i)
            self.apply_width_to_tab(tab)
        self.update_config(width_pct=width_pct)
            
    def apply_width_to_tab(self, tab):
        pct_text = self.title_bar.width_selector.currentText()
        center_pct = int(pct_text.replace("%", ""))
        margin_pct = (100 - center_pct) // 2
        tab.set_margins(margin_pct, center_pct)

    def load_keys(self):
        self.key_selector.clear()
        if os.path.exists(KEYS_FILE):
            try:
                with open(KEYS_FILE, "r", encoding="utf-8") as f:
                    keys = json.load(f)
                    for i, key in enumerate(keys):
                        mask = f"Key {i+1} (***{key[-4:]})" if len(key) > 4 else f"Key {i+1}"
                        self.key_selector.addItem(mask, key)
            except Exception:
                pass

    def add_key(self):
        key, ok = QInputDialog.getText(self, "Add API Key", "Paste Gemini API Key:")
        if ok and key.strip():
            key = key.strip()
            keys = []
            if os.path.exists(KEYS_FILE):
                try:
                    with open(KEYS_FILE, "r", encoding="utf-8") as f:
                        keys = json.load(f)
                except Exception:
                    pass

            if key not in keys:
                keys.append(key)
                with open(KEYS_FILE, "w", encoding="utf-8") as f:
                    json.dump(keys, f)

            self.load_keys()
            self.key_selector.setCurrentIndex(self.key_selector.count() - 1)
            
    def apply_font(self, *args):
        font = self.font_selector.currentFont()
        size = self.title_bar.font_spinner.value()
        font.setPointSize(size)
        self.current_font = font
        
        for i in range(self.stack.count()):
            tab = self.stack.widget(i)
            tab.browser.setFont(self.current_font)
            
        self.update_config(font_family=font.family(), font_size=size)

    def show_help(self):
        help_text = (
            "Made by Dr. Bishnu Goswami.\n\n"
            f"Local Save Path for Chats:\n{CHAT_DIR}\n\n"
            "Keyboard Shortcuts:\n"
            "• Ctrl+Space : Open Prompt\n"
            "• Ctrl+Enter : Send Prompt (in dialog)\n"
            "• Ctrl+T : New Tab\n"
            "• Ctrl+W : Close Tab\n"
            "• Ctrl+Tab : Next Tab\n"
            "• Ctrl+O : Resume Chat\n"
            "• Ctrl+S : Open Settings\n"
            "• Ctrl+E : Export PDF\n"
            "• Alt+M : Open Menu 🚀\n"
            "• Alt+P : Click Prompt Button\n"
            "• Alt+Z : Edit Font Size\n"
            "• Alt+W : Edit Reading Width\n"
            "• F11 / Ctrl+F : Toggle Fullscreen\n"
            "• Ctrl+Up/Down : Maximize / Normal Window\n\n"
            "Prompt Dialog Shortcuts:\n"
            "• Alt+M : Focus Model Selector\n"
            "• Alt+N : Open in New Tab\n"
            "• Alt+A : Attach Image\n"
            "• Alt+S : Send\n\n"
            "Website: GitHub.com/bishnu-goswami"
        )
        QMessageBox.information(self, "Help & Shortcuts", help_text)
        
    def export_pdf(self):
        current_tab = self.stack.currentWidget()
        if not current_tab or not current_tab.current_chat_path:
            return
        
        default_name = current_tab.current_chat_path.replace(".md", ".pdf")
        filepath, _ = QFileDialog.getSaveFileName(self, "Export to PDF", default_name, "PDF Files (*.pdf)")
        
        if filepath:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(filepath)
            
            current_tab.browser.document().print_(printer)
            self.title_bar.status_label.setText("PDF Exported successfully.")

    # ============================================================
    # CHAT FILE & MEMORY MANAGEMENT
    # ============================================================
    def resume_chat_dialog(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Resume Markdown Chat", CHAT_DIR, "Markdown Files (*.md)"
        )
        if not filepath:
            return

        self.load_chat_from_path(filepath)
        self.title_bar.status_label.setText(f"Resumed: {os.path.basename(filepath)}")

    def parse_markdown_chat(self, path):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        history = []
        for block in text.split("---"):
            if "## Question" not in block or "## Answer" not in block:
                continue
            try:
                user_text = block.split("## Question", 1)[1].split("## Answer", 1)[0].strip()
                gemini_text = block.split("## Answer", 1)[1].strip()
                
                if "<img" in user_text:
                    user_text = user_text.split("<br><br>")[-1].strip()

                if user_text and gemini_text:
                    history.append(types.Content(role="user", parts=[types.Part(text=user_text)]))
                    history.append(types.Content(role="model", parts=[types.Part(text=gemini_text)]))
            except Exception:
                continue

        return history

    def save_exchange_to_file(self, tab, user_text, gemini_text, image_path=None):
        img_str = f'<img src="{image_path}" width="250" /><br><br>' if image_path else ""
        with open(tab.current_chat_path, "a", encoding="utf-8") as f:
            f.write(f"## Question\n\n{img_str}{user_text.rstrip()}\n\n")
            f.write(f"## Answer\n\n{gemini_text.rstrip()}\n\n---\n\n")

    def render_entire_chat(self, tab):
        if not os.path.exists(tab.current_chat_path):
            tab.browser.clear()
            return

        with open(tab.current_chat_path, "r", encoding="utf-8") as f:
            md = f.read()
        tab.browser.setMarkdown(md)
        
        sb = tab.browser.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ============================================================
    # PROMPT DIALOG & API LOGIC
    # ============================================================
    def open_prompt_dialog(self):
        current_tab = self.stack.currentWidget()
        if not current_tab:
            return

        api_key = self.key_selector.currentData()
        if not api_key:
            QMessageBox.warning(self, "Missing Key", "Please add an API Key first in Settings.")
            self.open_settings()
            return
            
        dialog = PromptDialog(
            self, 
            active_font=self.current_font, 
            initial_text=self.recovered_prompt, 
            initial_image=self.recovered_image,
            default_model_idx=self.current_model_index
        )
        
        self.recovered_prompt = ""
        self.recovered_image = None
        
        if dialog.exec_() == QDialog.Accepted:
            prompt, image_path, selected_model, open_in_new_tab = dialog.get_data()
            
            if selected_model in MODELS:
                self.current_model_index = MODELS.index(selected_model)
                
            if prompt or image_path:
                if not prompt: 
                    prompt = "Describe this image."
                    
                if open_in_new_tab:
                    self.new_chat()
                    current_tab = self.stack.currentWidget()
                    
                self.send_message(prompt, image_path, api_key, current_tab, selected_model)
        else:
            draft_prompt, draft_image, draft_model, _ = dialog.get_data()
            self.recovered_prompt = draft_prompt
            self.recovered_image = draft_image

    def send_message(self, prompt, image_path, api_key, tab, selected_model):
        self.title_bar.prompt_btn.setEnabled(False)
        self.title_bar.status_label.setText("Thinking...")

        current_md = tab.browser.toMarkdown()
        img_notice = f'<img src="{image_path}" width="250" /><br><br>' if image_path else ""
        tab.browser.setMarkdown(current_md + f"\n\n## Question\n\n{img_notice}{prompt}\n\n*Waiting for response...*")
        sb = tab.browser.verticalScrollBar()
        sb.setValue(sb.maximum())

        tab.worker = ApiWorker(prompt, tab.history, selected_model, api_key, image_path)
        
        tab.worker.status_update.connect(lambda msg: self.title_bar.status_label.setText(msg))
        
        tab.worker.finished.connect(lambda text, model, t=tab, p=image_path, pr=prompt, k=api_key: self.on_success(pr, text, model, p, t, k))
        
        tab.worker.error.connect(lambda err, t=tab, k=api_key, pr=prompt, img=image_path, m=selected_model: self.on_error(err, t, k, pr, img, m))
        
        tab.worker.start()

    def on_success(self, prompt, answer, used_model, image_path, tab, api_key):
        if len(tab.history) == 0:
            idx = self.stack.indexOf(tab)
            if idx != -1:
                tooltip_text = prompt if len(prompt) <= 97 else prompt[:97] + "..."
                self.title_bar.tab_bar.setTabToolTip(idx, tooltip_text)

        tab.history.append(types.Content(role="user", parts=[types.Part(text=prompt)]))
        tab.history.append(types.Content(role="model", parts=[types.Part(text=answer)]))
        
        self.save_exchange_to_file(tab, prompt, answer, image_path)

        masked = f"...{api_key[-4:]}" if len(api_key) > 4 else api_key
        log_text = f"Time: {datetime.now().strftime('%H:%M:%S')}\nModel: {used_model}\nKey: {masked}"
        self.last_log_label.setText(log_text)
        self.update_config(last_log=log_text)

        self.render_entire_chat(tab)
        self.title_bar.prompt_btn.setEnabled(True)
        self.title_bar.status_label.setText(f"Done (via {used_model})")

    def on_error(self, err_msg, tab, api_key, prompt, image_path, failed_model):
        self.recovered_prompt = prompt
        self.recovered_image = image_path
        
        extra_notice = ""
        if "429" in err_msg or "quota" in err_msg.lower() or "exhausted" in err_msg.lower():
            if self.current_model_index < len(MODELS) - 1:
                self.current_model_index += 1
                next_model = MODELS[self.current_model_index]
                extra_notice = f"The app has automatically downgraded you to {next_model}."
            else:
                extra_notice = "You are currently on the lowest available model."
        else:
            extra_notice = "Please check your network connection or API key."
            
        QMessageBox.critical(self, "API Error", f"{err_msg}\n\nYour prompt has been saved safely. {extra_notice}")
        
        masked = f"...{api_key[-4:]}" if len(api_key) > 4 else api_key
        log_text = f"Time: {datetime.now().strftime('%H:%M:%S')}\nModel: FAILED ({failed_model})\nKey: {masked}"
        self.last_log_label.setText(log_text)
        self.update_config(last_log=log_text)

        self.render_entire_chat(tab)
        self.title_bar.prompt_btn.setEnabled(True)
        self.title_bar.status_label.setText("Failed.")
        
        QTimer.singleShot(200, self.open_prompt_dialog)

# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    gui = GeminiGUI()
    gui.showMaximized()
    sys.exit(app.exec_())