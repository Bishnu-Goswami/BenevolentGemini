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
    QInputDialog, QMessageBox, QFileDialog, QLabel, QShortcut, QDialog, QSpinBox
)
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtPrintSupport import QPrinter

# ============================================================
# CONFIGURATION & CONSTANTS
# ============================================================
MODELS = [
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-3.1-pro-preview",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-pro-exp",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash-8b"
]

CHAT_DIR = os.path.expanduser("~/Gemini Chats")
KEYS_FILE = os.path.expanduser("~/.gemini_api_keys.json")
CONFIG_FILE = os.path.expanduser("~/.gemini_gui_config.json")
os.makedirs(CHAT_DIR, exist_ok=True)

# ============================================================
# THEME STYLESHEETS (QSS)
# ============================================================
THEMES = {
    "Classic Light": "",
    "Night Mode": """
        QWidget { background-color: #1e1e1e; color: #d4d4d4; font-family: sans-serif; }
        QTextBrowser, QTextEdit { background-color: #252526; color: #d4d4d4; border: 1px solid #3e3e42; border-radius: 4px; }
        QPushButton { background-color: #333333; color: #ffffff; border: 1px solid #444; border-radius: 3px; padding: 4px 10px; }
        QPushButton:hover { background-color: #444444; }
        QPushButton:disabled { background-color: #222; color: #666; }
        QComboBox, QSpinBox { background-color: #2d2d30; color: #fff; border: 1px solid #3e3e42; padding: 3px; border-radius: 3px; }
        QDialog { background-color: #1e1e1e; }
    """,
    "Intelligent Grayscale": """
        QWidget { background-color: #efefef; color: #1c1c1c; font-family: sans-serif; }
        QTextBrowser, QTextEdit { background-color: #f7f7f7; color: #111111; border: 1px solid #b0b0b0; border-radius: 4px; }
        QPushButton { background-color: #dfdfdf; color: #111111; border: 1px solid #999999; border-radius: 3px; padding: 4px 10px; }
        QPushButton:hover { background-color: #cccccc; }
        QPushButton:disabled { background-color: #e5e5e5; color: #888888; }
        QComboBox, QSpinBox { background-color: #f7f7f7; color: #111111; border: 1px solid #b0b0b0; padding: 3px; border-radius: 3px; }
        QDialog { background-color: #efefef; }
    """,
    "Warm Sepia": """
        QWidget { background-color: #f6eedb; color: #3b2f2f; font-family: sans-serif; }
        QTextBrowser, QTextEdit { background-color: #fcf6e8; color: #2e2323; border: 1px solid #d4c5a9; border-radius: 4px; }
        QPushButton { background-color: #ebdcc0; color: #332424; border: 1px solid #c2b090; border-radius: 3px; padding: 4px 10px; }
        QPushButton:hover { background-color: #dfceb0; }
        QPushButton:disabled { background-color: #ede6d6; color: #9c8e7c; }
        QComboBox, QSpinBox { background-color: #fcf6e8; color: #3b2f2f; border: 1px solid #d4c5a9; padding: 3px; border-radius: 3px; }
        QDialog { background-color: #f6eedb; }
    """,
    "High Contrast": """
        QWidget { background-color: #000000; color: #ffffff; font-family: sans-serif; }
        QTextBrowser, QTextEdit { background-color: #000000; color: #ffffff; border: 2px solid #ffffff; }
        QPushButton { background-color: #000000; color: #ffffff; border: 2px solid #ffffff; padding: 4px 10px; font-weight: bold; }
        QPushButton:hover { background-color: #ffffff; color: #000000; }
        QPushButton:disabled { border-color: #555555; color: #555555; }
        QComboBox, QSpinBox { background-color: #000000; color: #ffffff; border: 2px solid #ffffff; padding: 3px; }
        QDialog { background-color: #000000; }
    """
}

# ============================================================
# BACKGROUND API WORKER
# ============================================================
class ApiWorker(QThread):
    finished = pyqtSignal(str, str)
    error = pyqtSignal(str)

    def __init__(self, prompt, history, selected_model, api_key, image_path=None):
        super().__init__()
        self.prompt = prompt
        self.history = history
        self.selected_model = selected_model
        self.api_key = api_key
        self.image_path = image_path

    def run(self):
        try:
            client = genai.Client(api_key=self.api_key)
        except Exception as e:
            self.error.emit(f"Failed to initialize client: {str(e)}")
            return

        models_to_try = [self.selected_model] + [
            m for m in MODELS if m != self.selected_model
        ]

        answer = None
        used_model = None

        payload = self.prompt
        if self.image_path and os.path.exists(self.image_path):
            try:
                img = Image.open(self.image_path)
                payload = [img, self.prompt]
            except Exception as e:
                self.error.emit(f"Error loading image: {str(e)}")
                return

        for current_model in models_to_try:
            try:
                chat = client.chats.create(
                    model=current_model,
                    history=self.history
                )
                response = chat.send_message(message=payload)
                answer = response.text
                used_model = current_model
                break
            except Exception as e:
                err_str = str(e).lower()
                is_temporary = any(
                    x in err_str for x in [
                        "503", "service unavailable", "unavailable",
                        "overloaded", "high demand", "spike"
                    ]
                )
                if is_temporary:
                    continue
                else:
                    self.error.emit(f"API Error ({current_model}): {str(e)}")
                    return

        if answer is not None:
            self.finished.emit(answer, used_model)
        else:
            self.error.emit("All fallback models were busy or failed.")


# ============================================================
# CUSTOM UI WIDGET: FLOATING PROMPT DIALOG
# ============================================================
class PromptDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Prompt")
        self.resize(550, 250)
        self.image_path = None
        
        layout = QVBoxLayout(self)
        
        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Type your prompt here...\n(Press Ctrl+Enter to send)")
        layout.addWidget(self.input_box)
        
        bottom_row = QHBoxLayout()
        
        self.attach_btn = QPushButton("📎 Attach Image")
        self.attach_btn.clicked.connect(self.attach_image)
        bottom_row.addWidget(self.attach_btn)
        
        self.file_label = QLabel("")
        self.file_label.setStyleSheet("color: gray; font-style: italic;")
        bottom_row.addWidget(self.file_label)
        
        bottom_row.addStretch()
        
        self.send_btn = QPushButton("Send")
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
        return self.input_box.toPlainText().strip(), self.image_path


# ============================================================
# MAIN GUI WINDOW
# ============================================================
class GeminiGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BenevolentGemini (By Dr. Bishnu Goswami)")
        self.resize(1000, 600)

        self.history = []
        self.current_chat_path = None

        self.init_ui()
        self.new_chat()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # ----------------- Top Controls -----------------
        top_bar = QHBoxLayout()

        top_bar.addWidget(QLabel("Model:"))
        self.model_selector = QComboBox()
        self.model_selector.addItems(MODELS)
        top_bar.addWidget(self.model_selector)

        top_bar.addWidget(QLabel("Key:"))
        self.key_selector = QComboBox()
        self.load_keys()
        top_bar.addWidget(self.key_selector)

        self.add_key_btn = QPushButton("Add Key")
        self.add_key_btn.clicked.connect(self.add_key)
        top_bar.addWidget(self.add_key_btn)
        
        # Theme Dropdown
        top_bar.addWidget(QLabel("Theme:"))
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(list(THEMES.keys()))
        self.theme_selector.currentTextChanged.connect(self.apply_theme)
        top_bar.addWidget(self.theme_selector)
        
        top_bar.addWidget(QLabel("Size:"))
        self.font_spinner = QSpinBox()
        self.font_spinner.setRange(8, 32)
        self.font_spinner.setValue(11)
        self.font_spinner.valueChanged.connect(self.change_font_size)
        top_bar.addWidget(self.font_spinner)

        self.new_chat_btn = QPushButton("New Chat")
        self.new_chat_btn.clicked.connect(self.new_chat)
        top_bar.addWidget(self.new_chat_btn)

        self.resume_chat_btn = QPushButton("Resume Chat")
        self.resume_chat_btn.clicked.connect(self.resume_chat_dialog)
        top_bar.addWidget(self.resume_chat_btn)
        
        self.pdf_btn = QPushButton("Export PDF")
        self.pdf_btn.clicked.connect(self.export_pdf)
        top_bar.addWidget(self.pdf_btn)

        self.prompt_btn = QPushButton("💬 Prompt")
        self.prompt_btn.setStyleSheet("font-weight: bold; padding: 5px 15px;")
        self.prompt_btn.clicked.connect(self.open_prompt_dialog)
        top_bar.addWidget(self.prompt_btn)
        
        self.help_btn = QPushButton("?")
        self.help_btn.clicked.connect(self.show_help)
        top_bar.addWidget(self.help_btn)

        self.status_label = QLabel("Ready")
        top_bar.addWidget(self.status_label)
        
        top_bar.addStretch() 
        layout.addLayout(top_bar)

        # ----------------- Markdown Display -----------------
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.change_font_size(self.font_spinner.value())
        layout.addWidget(self.chat_display)

        # ----------------- Global Keyboard Shortcut -----------------
        self.shortcut = QShortcut(QKeySequence("Ctrl+Space"), self)
        self.shortcut.activated.connect(self.open_prompt_dialog)
        
        # ----------------- Persistent Theme Setup -----------------
        default_theme = "Classic Light"
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    default_theme = config.get("theme", "Classic Light")
            except Exception:
                pass
        
        # Block signals briefly so setting the text doesn't trigger a redundant file write
        self.theme_selector.blockSignals(True)
        self.theme_selector.setCurrentText(default_theme)
        self.theme_selector.blockSignals(False)
        self.apply_theme(default_theme)

    # ============================================================
    # THEME & UI FUNCTIONS
    # ============================================================
    def apply_theme(self, theme_name):
        qss = THEMES.get(theme_name, "")
        QApplication.instance().setStyleSheet(qss)
        
        # Save choice to config automatically
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                pass
                
        config["theme"] = theme_name
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f)
        except Exception:
            pass

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
            
    def change_font_size(self, size):
        font = self.chat_display.font()
        font.setPointSize(size)
        self.chat_display.setFont(font)
        
    def show_help(self):
        QMessageBox.information(
            self, "Help",
            "Made by Dr. Bishnu Goswami.\n"
            "Ctrl+Space to open prompt window.Ctrl+Enter to send prompt.\n"
            "Website: GitHub.com/bishnu-goswami/BenevolentGemini"
        )
        
    def export_pdf(self):
        if not self.current_chat_path:
            return
        
        default_name = self.current_chat_path.replace(".md", ".pdf")
        filepath, _ = QFileDialog.getSaveFileName(self, "Export to PDF", default_name, "PDF Files (*.pdf)")
        
        if filepath:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(filepath)
            
            self.chat_display.document().print_(printer)
            self.status_label.setText("PDF Exported successfully.")

    # ============================================================
    # CHAT FILE & MEMORY MANAGEMENT
    # ============================================================
    def new_chat(self):
        filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.md")
        self.current_chat_path = os.path.join(CHAT_DIR, filename)
        
        with open(self.current_chat_path, "w", encoding="utf-8") as f:
            f.write("")

        self.history = []
        self.render_entire_chat()
        self.status_label.setText("New chat created.")

    def resume_chat_dialog(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Resume Markdown Chat", CHAT_DIR, "Markdown Files (*.md)"
        )
        if not filepath:
            return

        self.current_chat_path = filepath
        self.history = self.parse_markdown_chat(filepath)
        self.render_entire_chat()
        self.status_label.setText(f"Resumed: {os.path.basename(filepath)}")

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

                if user_text and gemini_text:
                    history.append(types.Content(role="user", parts=[types.Part(text=user_text)]))
                    history.append(types.Content(role="model", parts=[types.Part(text=gemini_text)]))
            except Exception:
                continue

        return history

    def save_exchange_to_file(self, user_text, gemini_text, image_path=None):
        img_str = f"*[Image Attached: {os.path.basename(image_path)}]*\n\n" if image_path else ""
        with open(self.current_chat_path, "a", encoding="utf-8") as f:
            f.write(f"## Question\n\n{img_str}{user_text.rstrip()}\n\n")
            f.write(f"## Answer\n\n{gemini_text.rstrip()}\n\n---\n\n")

    def render_entire_chat(self):
        if not os.path.exists(self.current_chat_path):
            self.chat_display.clear()
            return

        with open(self.current_chat_path, "r", encoding="utf-8") as f:
            md = f.read()
        self.chat_display.setMarkdown(md)
        
        sb = self.chat_display.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ============================================================
    # PROMPT DIALOG & API LOGIC
    # ============================================================
    def open_prompt_dialog(self):
        api_key = self.key_selector.currentData()
        
        if not api_key:
            QMessageBox.warning(self, "Missing Key", "Please add an API Key first.")
            return
            
        dialog = PromptDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            prompt, image_path = dialog.get_data()
            if prompt or image_path:
                if not prompt: 
                    prompt = "Describe this image."
                self.send_message(prompt, image_path, api_key)

    def send_message(self, prompt, image_path, api_key):
        self.prompt_btn.setEnabled(False)
        self.status_label.setText("Thinking...")

        current_md = self.chat_display.toMarkdown()
        img_notice = f"*[Attached: {os.path.basename(image_path)}]*\n\n" if image_path else ""
        self.chat_display.setMarkdown(current_md + f"\n\n## Question\n\n{img_notice}{prompt}\n\n*Waiting for response...*")
        sb = self.chat_display.verticalScrollBar()
        sb.setValue(sb.maximum())

        selected_model = self.model_selector.currentText()
        self.worker = ApiWorker(prompt, self.history, selected_model, api_key, image_path)
        self.worker.finished.connect(lambda text, model: self.on_success(prompt, text, model, image_path))
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_success(self, prompt, answer, used_model, image_path):
        self.history.append(types.Content(role="user", parts=[types.Part(text=prompt)]))
        self.history.append(types.Content(role="model", parts=[types.Part(text=answer)]))
        
        self.save_exchange_to_file(prompt, answer, image_path)

        idx = self.model_selector.findText(used_model)
        if idx != -1:
            self.model_selector.setCurrentIndex(idx)

        self.render_entire_chat()
        self.prompt_btn.setEnabled(True)
        self.status_label.setText(f"Done (via {used_model})")

    def on_error(self, err_msg):
        QMessageBox.critical(self, "Error", err_msg)
        self.render_entire_chat()
        self.prompt_btn.setEnabled(True)
        self.status_label.setText("Failed.")

# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    gui = GeminiGUI()
    gui.show()
    sys.exit(app.exec_())
