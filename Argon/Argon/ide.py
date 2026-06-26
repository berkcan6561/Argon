# -*- coding: utf-8 -*-
"""TürkCode IDE."""

from __future__ import annotations

import io
import os
import re
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Dict, List, Optional

def _find_qt_plugin_path(prefix: str) -> Optional[str]:
    candidate_paths = [
        Path(prefix, "Lib", "site-packages", "PyQt5", "Qt5", "plugins"),
        Path(prefix, "Lib", "site-packages", "PyQt5", "plugins"),
        Path(prefix, "Lib", "site-packages", "PySide6", "Qt", "plugins"),
        Path(prefix, "Lib", "site-packages", "PySide6", "Qt5", "plugins"),
        Path(prefix, "Lib", "site-packages", "PySide6", "plugins"),
        Path(prefix, "Library", "plugins"),
    ]
    for path in candidate_paths:
        if path.is_dir():
            return str(path)
    return None

if "QT_QPA_PLATFORM_PLUGIN_PATH" not in os.environ:
    plugin_path = _find_qt_plugin_path(sys.prefix)
    if plugin_path:
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path

try:
    from PyQt5.QtCore import QDir, QRect, QSize, Qt, QTimer, pyqtSignal
    from PyQt5.QtGui import (
        QColor,
        QFont,
        QKeySequence,
        QPainter,
        QTextCharFormat,
        QTextCursor,
        QTextFormat,
        QSyntaxHighlighter,
    )
    from PyQt5.QtWidgets import (
        QAction,
        QApplication,
        QCompleter,
        QDockWidget,
        QFileDialog,
        QFileSystemModel,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPlainTextEdit,
        QTabWidget,
        QTextEdit,
        QToolBar,
        QTreeView,
        QTreeWidget,
        QTreeWidgetItem,
        QWidget,
    )
    QT_BINDING = "PyQt5"
except ModuleNotFoundError:
    try:
        from PySide6.QtCore import QDir, QRect, QSize, Qt, QTimer, Signal as pyqtSignal
        from PySide6.QtGui import (
            QColor,
            QFont,
            QKeySequence,
            QPainter,
            QTextCharFormat,
            QTextCursor,
            QTextFormat,
            QSyntaxHighlighter,
        )
        from PySide6.QtWidgets import (
            QAction,
            QApplication,
            QCompleter,
            QDockWidget,
            QFileDialog,
            QFileSystemModel,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QMainWindow,
            QMessageBox,
            QPlainTextEdit,
            QTabWidget,
            QTextEdit,
            QToolBar,
            QTreeView,
            QTreeWidget,
            QTreeWidgetItem,
            QWidget,
        )
        QT_BINDING = "PySide6"
    except ModuleNotFoundError as exc:
        current_python = Path(sys.executable).resolve()
        project_root = Path(__file__).resolve().parents[1]
        venv_python = project_root / ".venv" / "Scripts" / "python.exe"
        message = [
            "Qt arayuz kutuphanesi bulunamadi.",
            "",
            f"Kullanilan Python: {current_python}",
            "",
        ]
        if venv_python.exists():
            message.extend(
                [
                    "Bu projede IDE'yi sanal ortam icindeki Python ile calistirman gerekiyor:",
                    f'  & "{venv_python}" "{Path(__file__).resolve()}"',
                ]
            )
        else:
            message.extend(
                [
                    "PyQt5 veya PySide6 kurman gerekiyor.",
                    "Ornek kurulum:",
                    "  python -m pip install PyQt5",
                ]
            )
        raise SystemExit("\n".join(message)) from exc

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from interpreter import KEYWORDS, TurkCodeError, TurkCodeInterpreter


SNIPPETS: Dict[str, str] = {
    "Fonksiyon": (
        "fonksiyon yeniFonksiyon(parametre) {\n"
        "    dondur parametre;\n"
        "}\n"
    ),
    "Koşul": (
        "eger (kosul) {\n"
        "    yaz(\"Dogru\");\n"
        "}\n"
        "degilse {\n"
        "    yaz(\"Yanlis\");\n"
        "}\n"
    ),
    "Döngü": (
        "dongu (degisken i = 0; i < 10; i++) {\n"
        "    yaz(i);\n"
        "}\n"
    ),
    "Sınıf": (
        "sinif YeniSinif {\n"
        "    degisken ad = \"Ornek\";\n\n"
        "    fonksiyon baslat(ad) {\n"
        "        this.ad = ad;\n"
        "    }\n\n"
        "    fonksiyon ozet() {\n"
        "        dondur this.ad;\n"
        "    }\n"
        "}\n"
    ),
    "Try/Catch": (
        "dene {\n"
        "    yaz(\"Calisiyor\");\n"
        "}\n"
        "yakala (hata) {\n"
        "    yaz(hata);\n"
        "}\n"
    ),
    "İthal": 'ithal "yardimci.tc" olarak yardimci;\n',
    "Ok Fonksiyon": "degisken kare = (x) => x * x;\n",
}


class LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        self.editor.line_number_area_paint_event(event)


class CodeHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.formats: Dict[str, QTextCharFormat] = {}
        self._build_formats()
        self.keyword_patterns = [re.compile(rf"\b{re.escape(word)}\b") for word in sorted(set(KEYWORDS.keys()))]

    def _build_formats(self) -> None:
        self.formats["comment"] = self._fmt("#6A9955", italic=True)
        self.formats["string"] = self._fmt("#CE9178")
        self.formats["number"] = self._fmt("#B5CEA8")
        self.formats["keyword"] = self._fmt("#569CD6", bold=True)
        self.formats["function"] = self._fmt("#DCDCAA", bold=True)
        self.formats["class"] = self._fmt("#4EC9B0", bold=True)
        self.formats["operator"] = self._fmt("#C586C0")

    @staticmethod
    def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    def highlightBlock(self, text: str) -> None:
        for match in re.finditer(r"//.*$", text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats["comment"])

        for match in re.finditer(r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'', text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats["string"])

        for match in re.finditer(r"\b\d+(\.\d+)?\b", text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats["number"])

        for pattern in self.keyword_patterns:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), self.formats["keyword"])

        for match in re.finditer(r"\b(fonksiyon)\s+([A-Za-z_ÇĞİÖŞÜçğıöşü][\wÇĞİÖŞÜçğıöşü]*)", text):
            self.setFormat(match.start(2), len(match.group(2)), self.formats["function"])

        for match in re.finditer(r"\b(sinif|sınıf)\s+([A-Za-z_ÇĞİÖŞÜçğıöşü][\wÇĞİÖŞÜçğıöşü]*)", text):
            self.setFormat(match.start(2), len(match.group(2)), self.formats["class"])

        for match in re.finditer(r"==|!=|>=|<=|\+=|-=|\*=|/=|%=|=>|\+\+|--|\bveya\b|\bve\b|\bdegil\b|\bdeğil\b", text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats["operator"])


class CodeEditor(QPlainTextEdit):
    cursorDetailsChanged = pyqtSignal(int, int)
    contentContextChanged = pyqtSignal()

    def __init__(self, ide: "TurkCodeIDE", file_path: Optional[str] = None):
        super().__init__(ide)
        self.ide = ide
        self.file_path = file_path
        self.highlighter = CodeHighlighter(self.document())
        self.line_number_area = LineNumberArea(self)
        self.symbol_timer = QTimer(self)
        self.symbol_timer.setSingleShot(True)
        self.symbol_timer.setInterval(150)
        self.symbol_timer.timeout.connect(self.contentContextChanged.emit)

        font = QFont("Consolas", 12)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                selection-background-color: #264f78;
                border: none;
            }
            """
        )

        self.completer = QCompleter(self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setWidget(self)
        self.completer.activated[str].connect(self.insert_completion)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.cursorPositionChanged.connect(self._emit_cursor_details)
        self.textChanged.connect(self.symbol_timer.start)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def display_name(self) -> str:
        return Path(self.file_path).name if self.file_path else "Adsiz.tc"

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 18 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        content_rect = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(content_rect.left(), content_rect.top(), self.line_number_area_width(), content_rect.height())
        )

    def line_number_area_paint_event(self, event) -> None:
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#252526"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#858585"))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self) -> None:
        selection = QTextEdit.ExtraSelection()
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        selection.format.setBackground(QColor("#2A2D2E"))
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        self.setExtraSelections([selection])

    def _emit_cursor_details(self) -> None:
        cursor = self.textCursor()
        self.cursorDetailsChanged.emit(cursor.blockNumber() + 1, cursor.positionInBlock() + 1)

    def current_line_and_column(self) -> tuple[int, int]:
        cursor = self.textCursor()
        return cursor.blockNumber() + 1, cursor.positionInBlock() + 1

    def goto_line(self, line: int, column: int = 1) -> None:
        block = self.document().findBlockByNumber(max(0, line - 1))
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, max(0, column - 1))
        self.setTextCursor(cursor)
        self.centerCursor()
        self.setFocus()

    def keyPressEvent(self, event) -> None:
        if self.completer.popup().isVisible() and event.key() in (
            Qt.Key_Return,
            Qt.Key_Enter,
            Qt.Key_Tab,
            Qt.Key_Backtab,
            Qt.Key_Escape,
        ):
            event.ignore()
            return

        if event.matches(QKeySequence.Save):
            self.ide._save_current_file()
            return

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._insert_newline_with_indent()
            return

        if event.key() == Qt.Key_Tab and self.textCursor().hasSelection():
            self._indent_selection()
            return

        if event.key() == Qt.Key_Backtab and self.textCursor().hasSelection():
            self._outdent_selection()
            return

        if not (event.modifiers() & (Qt.ControlModifier | Qt.AltModifier)):
            pairs = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}
            text = event.text()
            if text in pairs:
                self._insert_pair(text, pairs[text])
                return

        super().keyPressEvent(event)
        self._update_completion_popup(event)

    def _insert_pair(self, left: str, right: str) -> None:
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            cursor.insertText(f"{left}{selected}{right}")
            return
        cursor.insertText(f"{left}{right}")
        cursor.movePosition(QTextCursor.Left)
        self.setTextCursor(cursor)

    def _insert_newline_with_indent(self) -> None:
        cursor = self.textCursor()
        block_text = cursor.block().text()
        indent = re.match(r"\s*", block_text).group(0)
        trimmed = block_text.strip()
        if trimmed.endswith("{"):
            indent += "    "
        super().insertPlainText("\n" + indent)

    def _indent_selection(self) -> None:
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.setPosition(start)
        start_block = cursor.blockNumber()
        cursor.setPosition(end)
        end_block = cursor.blockNumber()
        cursor.beginEditBlock()
        for block_no in range(start_block, end_block + 1):
            block = self.document().findBlockByNumber(block_no)
            line_cursor = QTextCursor(block)
            line_cursor.insertText("    ")
        cursor.endEditBlock()

    def _outdent_selection(self) -> None:
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.setPosition(start)
        start_block = cursor.blockNumber()
        cursor.setPosition(end)
        end_block = cursor.blockNumber()
        cursor.beginEditBlock()
        for block_no in range(start_block, end_block + 1):
            block = self.document().findBlockByNumber(block_no)
            text = block.text()
            remove_count = 4 if text.startswith("    ") else 1 if text.startswith("\t") else 0
            if remove_count:
                line_cursor = QTextCursor(block)
                line_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, remove_count)
                line_cursor.removeSelectedText()
        cursor.endEditBlock()

    def _update_completion_popup(self, event) -> None:
        if event.text() and event.text().isspace():
            self.completer.popup().hide()
            return

        if event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
            return

        if event.key() in (
            Qt.Key_Escape,
            Qt.Key_Enter,
            Qt.Key_Return,
            Qt.Key_Tab,
            Qt.Key_Backtab,
            Qt.Key_Left,
            Qt.Key_Right,
            Qt.Key_Up,
            Qt.Key_Down,
        ):
            return

        prefix = self._word_under_cursor()
        if len(prefix) < 1:
            if self.completer.popup().isVisible():
                self.completer.popup().hide()
            return

        self.completer.setCompletionPrefix(prefix)
        popup = self.completer.popup()
        model = self.completer.completionModel()
        if model.rowCount() == 0:
            popup.hide()
            return

        popup.setCurrentIndex(model.index(0, 0))
        rect = self.cursorRect()
        rect.setWidth(max(260, popup.sizeHintForColumn(0) + 32))
        self.completer.complete(rect)

    def _word_under_cursor(self) -> str:
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        return cursor.selectedText()

    def set_completion_words(self, words: List[str]) -> None:
        from PyQt5.QtCore import QStringListModel

        self.completer.setModel(QStringListModel(sorted(set(words)), self.completer))

    def insert_completion(self, completion: str) -> None:
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        cursor.insertText(completion)
        self.setTextCursor(cursor)

    def toggle_comment(self) -> None:
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.setPosition(start)
        start_block = cursor.blockNumber()
        cursor.setPosition(end)
        end_block = cursor.blockNumber()
        cursor.beginEditBlock()
        blocks = [self.document().findBlockByNumber(block_no) for block_no in range(start_block, end_block + 1)]
        all_commented = all(block.text().lstrip().startswith("//") or not block.text().strip() for block in blocks)
        for block in blocks:
            text = block.text()
            line_cursor = QTextCursor(block)
            if all_commented:
                match = re.match(r"(\s*)//\s?", text)
                if match:
                    line_cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, len(match.group(1)))
                    line_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(match.group(0)) - len(match.group(1)))
                    line_cursor.removeSelectedText()
            else:
                leading = len(text) - len(text.lstrip())
                line_cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, leading)
                line_cursor.insertText("// ")
        cursor.endEditBlock()


class TurkCodeIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.workspace_root = Path(__file__).resolve().parent
        self.interpreter = TurkCodeInterpreter(str(self.workspace_root))
        self.last_problem_path: Optional[str] = None

        self.setWindowTitle("TürkCode IDE")
        self.resize(1440, 900)
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            QTabWidget::pane, QTreeView, QListWidget, QTreeWidget, QTextEdit {
                border: 1px solid #303031;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background: #2d2d30;
                color: #d4d4d4;
                padding: 8px 14px;
                border: 1px solid #303031;
            }
            QTabBar::tab:selected {
                background: #1f1f1f;
            }
            QMenuBar, QMenu, QToolBar {
                background-color: #252526;
                color: #d4d4d4;
            }
            """
        )

        self._build_ui()
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_status_bar()
        self._set_workspace(self.workspace_root)
        self._new_file()

    def _build_ui(self) -> None:
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._current_tab_changed)
        self.setCentralWidget(self.tabs)

        self.project_dock = QDockWidget("Proje", self)
        self.project_tree = QTreeView()
        self.project_model = QFileSystemModel(self)
        self.project_model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Files)
        self.project_model.setRootPath(str(self.workspace_root))
        self.project_tree.setModel(self.project_model)
        self.project_tree.doubleClicked.connect(self._open_index)
        for column in range(1, 4):
            self.project_tree.hideColumn(column)
        self.project_dock.setWidget(self.project_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.project_dock)

        self.console_dock = QDockWidget("Konsol", self)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 11))
        self.console_dock.setWidget(self.console)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.console_dock)

        self.problems_dock = QDockWidget("Sorunlar", self)
        self.problems_list = QListWidget()
        self.problems_list.itemDoubleClicked.connect(self._go_to_problem)
        self.problems_dock.setWidget(self.problems_list)
        self.addDockWidget(Qt.RightDockWidgetArea, self.problems_dock)

        self.symbols_dock = QDockWidget("Semboller", self)
        self.symbols_tree = QTreeWidget()
        self.symbols_tree.setHeaderHidden(True)
        self.symbols_tree.itemDoubleClicked.connect(self._go_to_symbol)
        self.symbols_dock.setWidget(self.symbols_tree)
        self.addDockWidget(Qt.RightDockWidgetArea, self.symbols_dock)
        self.tabifyDockWidget(self.problems_dock, self.symbols_dock)
        self.problems_dock.raise_()

    def _build_actions(self) -> None:
        self.action_new = QAction("Yeni Dosya", self)
        self.action_new.setShortcut("Ctrl+N")
        self.action_new.triggered.connect(self._new_file)

        self.action_open = QAction("Dosya Aç...", self)
        self.action_open.setShortcut("Ctrl+O")
        self.action_open.triggered.connect(self._open_file_dialog)

        self.action_open_folder = QAction("Klasör Aç...", self)
        self.action_open_folder.setShortcut("Ctrl+Shift+O")
        self.action_open_folder.triggered.connect(self._open_folder_dialog)

        self.action_save = QAction("Kaydet", self)
        self.action_save.setShortcut("Ctrl+S")
        self.action_save.triggered.connect(self._save_current_file)

        self.action_save_as = QAction("Farklı Kaydet...", self)
        self.action_save_as.setShortcut("Ctrl+Shift+S")
        self.action_save_as.triggered.connect(self._save_current_file_as)

        self.action_run = QAction("Çalıştır", self)
        self.action_run.setShortcut("F5")
        self.action_run.triggered.connect(self._run_current_file)

        self.action_check = QAction("Sözdizimi Kontrolü", self)
        self.action_check.setShortcut("Ctrl+Shift+B")
        self.action_check.triggered.connect(self._check_current_file)

        self.action_comment = QAction("Yorum Aç/Kapat", self)
        self.action_comment.setShortcut("Ctrl+/")
        self.action_comment.triggered.connect(self._toggle_comment)

        self.action_close_tab = QAction("Sekmeyi Kapat", self)
        self.action_close_tab.setShortcut("Ctrl+W")
        self.action_close_tab.triggered.connect(lambda: self._close_tab(self.tabs.currentIndex()))

        self.action_about = QAction("Hakkında", self)
        self.action_about.triggered.connect(self._show_about)

    def _build_menus(self) -> None:
        dosya_menu = self.menuBar().addMenu("Dosya")
        dosya_menu.addAction(self.action_new)
        dosya_menu.addAction(self.action_open)
        dosya_menu.addAction(self.action_open_folder)
        dosya_menu.addSeparator()
        dosya_menu.addAction(self.action_save)
        dosya_menu.addAction(self.action_save_as)
        dosya_menu.addSeparator()
        dosya_menu.addAction(self.action_close_tab)

        kod_menu = self.menuBar().addMenu("Kod")
        kod_menu.addAction(self.action_run)
        kod_menu.addAction(self.action_check)
        kod_menu.addAction(self.action_comment)
        kod_menu.addSeparator()
        for title in SNIPPETS:
            action = QAction(title, self)
            action.triggered.connect(lambda _, name=title: self._insert_snippet(name))
            kod_menu.addAction(action)

        gorunum_menu = self.menuBar().addMenu("Görünüm")
        for title, dock in (
            ("Proje", self.project_dock),
            ("Konsol", self.console_dock),
            ("Sorunlar", self.problems_dock),
            ("Semboller", self.symbols_dock),
        ):
            action = dock.toggleViewAction()
            action.setText(title)
            gorunum_menu.addAction(action)

        yardim_menu = self.menuBar().addMenu("Yardım")
        yardim_menu.addAction(self.action_about)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Araçlar", self)
        toolbar.setMovable(False)
        toolbar.addAction(self.action_new)
        toolbar.addAction(self.action_open)
        toolbar.addAction(self.action_save)
        toolbar.addSeparator()
        toolbar.addAction(self.action_run)
        toolbar.addAction(self.action_check)
        self.addToolBar(toolbar)

    def _build_status_bar(self) -> None:
        self.workspace_label = QLabel()
        self.file_label = QLabel("Dosya: -")
        self.cursor_label = QLabel("Satır 1, Sütun 1")
        self.state_label = QLabel("Hazır")
        self.statusBar().addPermanentWidget(self.workspace_label)
        self.statusBar().addPermanentWidget(self.file_label)
        self.statusBar().addPermanentWidget(self.cursor_label)
        self.statusBar().addPermanentWidget(self.state_label)

    def _set_workspace(self, path: Path) -> None:
        self.workspace_root = Path(path).resolve()
        self.interpreter.workspace_root = self.workspace_root
        self.project_model.setRootPath(str(self.workspace_root))
        self.project_tree.setRootIndex(self.project_model.index(str(self.workspace_root)))
        self.workspace_label.setText(f"Çalışma Alanı: {self.workspace_root.name}")

    def _current_editor(self) -> Optional[CodeEditor]:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, CodeEditor) else None

    def _new_file(self) -> None:
        editor = self._create_editor()
        self.tabs.addTab(editor, editor.display_name())
        self.tabs.setCurrentWidget(editor)
        self._refresh_editor_context(editor)

    def _create_editor(self, file_path: Optional[str] = None, content: str = "") -> CodeEditor:
        editor = CodeEditor(self, file_path=file_path)
        editor.setPlainText(content)
        editor.document().setModified(False)
        editor.document().modificationChanged.connect(lambda _: self._update_tab_title(editor))
        editor.cursorDetailsChanged.connect(self._update_cursor_position)
        editor.contentContextChanged.connect(lambda: self._refresh_editor_context(editor))
        return editor

    def _open_index(self, index) -> None:
        path = self.project_model.filePath(index)
        if Path(path).is_file():
            self._open_file(path)

    def _open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "TürkCode Dosyası Aç",
            str(self.workspace_root),
            "TürkCode Dosyaları (*.tc);;Tüm Dosyalar (*.*)",
        )
        if path:
            self._open_file(path)

    def _open_folder_dialog(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Klasör Aç", str(self.workspace_root))
        if path:
            self._set_workspace(Path(path))
            self.state_label.setText("Çalışma alanı güncellendi")

    def _open_file(self, path: str) -> None:
        normalized = str(Path(path).resolve())
        for index in range(self.tabs.count()):
            editor = self.tabs.widget(index)
            if isinstance(editor, CodeEditor) and editor.file_path == normalized:
                self.tabs.setCurrentIndex(index)
                return

        try:
            content = Path(normalized).read_text(encoding="utf-8")
        except Exception as exc:
            QMessageBox.warning(self, "Hata", f"Dosya açılamadı: {exc}")
            return

        editor = self._create_editor(file_path=normalized, content=content)
        self.tabs.addTab(editor, editor.display_name())
        self.tabs.setCurrentWidget(editor)
        self._refresh_editor_context(editor)

    def _save_editor(self, editor: CodeEditor, path: Optional[str] = None) -> bool:
        target = path or editor.file_path
        if not target:
            return self._save_editor_as(editor)

        try:
            Path(target).write_text(editor.toPlainText(), encoding="utf-8")
            editor.file_path = str(Path(target).resolve())
            editor.document().setModified(False)
            self._update_tab_title(editor)
            self._refresh_editor_context(editor)
            self.state_label.setText("Kaydedildi")
            return True
        except Exception as exc:
            QMessageBox.warning(self, "Hata", f"Dosya kaydedilemedi: {exc}")
            return False

    def _save_editor_as(self, editor: CodeEditor) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Farklı Kaydet",
            str(self.workspace_root / editor.display_name()),
            "TürkCode Dosyaları (*.tc);;Tüm Dosyalar (*.*)",
        )
        if not path:
            return False
        if not path.endswith(".tc"):
            path += ".tc"
        return self._save_editor(editor, path)

    def _save_current_file(self) -> bool:
        editor = self._current_editor()
        return self._save_editor(editor) if editor else False

    def _save_current_file_as(self) -> bool:
        editor = self._current_editor()
        return self._save_editor_as(editor) if editor else False

    def _close_tab(self, index: int) -> None:
        if index < 0:
            return
        editor = self.tabs.widget(index)
        if isinstance(editor, CodeEditor) and not self._confirm_close(editor):
            return
        self.tabs.removeTab(index)
        if self.tabs.count() == 0:
            self._new_file()

    def _confirm_close(self, editor: CodeEditor) -> bool:
        if not editor.document().isModified():
            return True
        answer = QMessageBox.question(
            self,
            "Kaydedilmemiş Değişiklikler",
            f"{editor.display_name()} kaydedilmedi. Kapatmadan önce kaydedilsin mi?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Cancel:
            return False
        if answer == QMessageBox.Yes:
            return self._save_editor(editor)
        return True

    def closeEvent(self, event) -> None:
        for index in range(self.tabs.count()):
            editor = self.tabs.widget(index)
            if isinstance(editor, CodeEditor) and not self._confirm_close(editor):
                event.ignore()
                return
        event.accept()

    def _current_tab_changed(self, _: int) -> None:
        editor = self._current_editor()
        if editor:
            self._refresh_editor_context(editor)
            line, column = editor.current_line_and_column()
            self._update_cursor_position(line, column)

    def _update_tab_title(self, editor: CodeEditor) -> None:
        index = self.tabs.indexOf(editor)
        if index == -1:
            return
        title = editor.display_name()
        if editor.document().isModified():
            title += " *"
        self.tabs.setTabText(index, title)
        if self.tabs.currentWidget() is editor:
            self.file_label.setText(f"Dosya: {editor.file_path or title}")
            self.setWindowTitle(f"TürkCode IDE - {title}")

    def _refresh_editor_context(self, editor: CodeEditor) -> None:
        if self.tabs.currentWidget() is not editor:
            return
        completion_words = set(self.interpreter.tamamlama_sozcukleri())
        completion_words.update(re.findall(r"[A-Za-z_ÇĞİÖŞÜçğıöşü][\wÇĞİÖŞÜçğıöşü]*", editor.toPlainText()))
        editor.set_completion_words(sorted(completion_words))
        self.file_label.setText(f"Dosya: {editor.file_path or editor.display_name()}")
        self._update_tab_title(editor)
        self._update_symbols(editor.toPlainText())

    def _update_cursor_position(self, line: int, column: int) -> None:
        self.cursor_label.setText(f"Satır {line}, Sütun {column}")

    def _update_symbols(self, source: str) -> None:
        self.symbols_tree.clear()
        groups = {
            "Sınıflar": r"^\s*sinif\s+([A-Za-z_ÇĞİÖŞÜçğıöşü][\wÇĞİÖŞÜçğıöşü]*)",
            "Fonksiyonlar": r"^\s*fonksiyon\s+([A-Za-z_ÇĞİÖŞÜçğıöşü][\wÇĞİÖŞÜçğıöşü]*)",
            "Değişkenler": r"^\s*degisken\s+([A-Za-z_ÇĞİÖŞÜçğıöşü][\wÇĞİÖŞÜçğıöşü]*)",
            "İthaller": r'^\s*ithal\s+"([^"]+)"',
        }
        lines = source.splitlines()
        for title, pattern in groups.items():
            root = QTreeWidgetItem([title])
            matches = 0
            for line_no, line in enumerate(lines, start=1):
                match = re.search(pattern, line)
                if not match:
                    continue
                child = QTreeWidgetItem([match.group(1)])
                child.setData(0, Qt.UserRole, {"line": line_no, "column": max(1, match.start(1) + 1)})
                root.addChild(child)
                matches += 1
            if matches:
                self.symbols_tree.addTopLevelItem(root)
                root.setExpanded(True)

    def _go_to_symbol(self, item: QTreeWidgetItem) -> None:
        payload = item.data(0, Qt.UserRole)
        if not payload:
            return
        editor = self._current_editor()
        if editor:
            editor.goto_line(payload["line"], payload["column"])

    def _clear_problems(self) -> None:
        self.problems_list.clear()

    def _add_problem(self, message: str, file_path: Optional[str], line: Optional[int], column: Optional[int]) -> None:
        item_text = message
        if line is not None:
            item_text = f"Satır {line}, Sütun {column or 1}: {message}"
        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, {"file_path": file_path, "line": line, "column": column})
        self.problems_list.addItem(item)

    def _go_to_problem(self, item: QListWidgetItem) -> None:
        payload = item.data(Qt.UserRole) or {}
        file_path = payload.get("file_path")
        if file_path and Path(file_path).exists():
            self._open_file(file_path)
        editor = self._current_editor()
        if editor and payload.get("line"):
            editor.goto_line(payload["line"], payload.get("column") or 1)

    def _run_current_file(self) -> None:
        editor = self._current_editor()
        if not editor:
            return

        self._clear_problems()
        self.console.clear()
        run_path = editor.file_path or str(self.workspace_root / "__gecici__.tc")
        self.interpreter = TurkCodeInterpreter(str(self.workspace_root))

        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        started = time.perf_counter()
        error: Optional[Exception] = None

        try:
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                self.interpreter.calistir(editor.toPlainText(), dosya_adi=run_path)
        except Exception as exc:
            error = exc

        duration_ms = (time.perf_counter() - started) * 1000
        output = stdout_buffer.getvalue()
        stderr_output = stderr_buffer.getvalue()

        self.console.append("=== Çalıştırma Başladı ===")
        if output.strip():
            self.console.append(output.rstrip())
        if stderr_output.strip():
            self.console.append(stderr_output.rstrip())

        if error is None:
            self.console.append(f"\nProgram başarıyla tamamlandı ({duration_ms:.1f} ms).")
            self.state_label.setText("Çalıştırma başarılı")
        else:
            self.console.append(f"\nHata: {error}")
            self.state_label.setText("Çalıştırma hatası")
            line = getattr(error, "line", None)
            column = getattr(error, "column", None)
            filename = getattr(error, "filename", None) or editor.file_path
            self._add_problem(str(error), filename, line, column)

        self.console.append("=== Çalıştırma Bitti ===")

    def _check_current_file(self) -> None:
        editor = self._current_editor()
        if not editor:
            return

        self._clear_problems()
        check_path = editor.file_path or str(self.workspace_root / "__gecici__.tc")
        self.interpreter = TurkCodeInterpreter(str(self.workspace_root))

        try:
            self.interpreter.cozumle(editor.toPlainText(), dosya_adi=check_path)
            self.state_label.setText("Sözdizimi temiz")
            self.console.append("Sözdizimi kontrolü başarılı.")
        except Exception as exc:
            self.state_label.setText("Sözdizimi hatası")
            self._add_problem(str(exc), getattr(exc, "filename", None) or editor.file_path, getattr(exc, "line", None), getattr(exc, "column", None))
            self.console.append(f"Sözdizimi hatası: {exc}")

    def _toggle_comment(self) -> None:
        editor = self._current_editor()
        if editor:
            editor.toggle_comment()

    def _insert_snippet(self, name: str) -> None:
        editor = self._current_editor()
        if editor:
            editor.insertPlainText(SNIPPETS[name])

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "TürkCode IDE",
            "TürkCode IDE v2.0\n\n"
            "Proje gezgini, akıllı editör, sembol paneli,\n"
            "sözdizimi kontrolü ve yorumlayıcı entegrasyonu içerir.",
        )


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("TürkCode IDE")
    app.setStyle("Fusion")

    window = TurkCodeIDE()
    window.show()
    exec_fn = getattr(app, "exec", None) or getattr(app, "exec_", None)
    sys.exit(exec_fn())


if __name__ == "__main__":
    main()
