from __future__ import annotations

import json
import os
from datetime import datetime

from PySide6.QtCore import QSettings, Qt, QUrl, Slot
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QStatusBar,
    QStyleFactory,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QButtonGroup,
)

from matriculadownloader.app_constants import APP_FONT, SETTINGS_APP, SETTINGS_ORG, SUPPORTED_DOMAINS
from matriculadownloader.icons import get_app_icon
from matriculadownloader.i18n import LANG, LANG_LABELS
from matriculadownloader.models import BookEntry
from matriculadownloader.pdf_utils import create_pdf_from_folder
from matriculadownloader.styles import dark_stylesheet, light_stylesheet
from matriculadownloader.text_utils import open_homepage
from matriculadownloader.worker import DownloaderWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(get_app_icon())
        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self.lang = self._load_language_setting()
        self.is_dark = self._load_theme_setting()
        self.books: list[BookEntry] = []
        self.worker: DownloaderWorker | None = None

        self.setWindowTitle(LANG[self.lang]["title"])
        self.resize(1000, 900)
        self.setMinimumSize(880, 580)
        self.setFont(APP_FONT)

        qapp = QStyleFactory.create("Fusion")
        if qapp:
            self.setStyle(qapp)

        self._build_ui()
        self.apply_theme()
        self.retranslate_ui()
        self.statusBar().showMessage(self._t("status_ready"))

    def _t(self, key: str) -> str:
        return LANG[self.lang][key]

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.btn_home = QPushButton()
        self.btn_home.clicked.connect(open_homepage)
        top_bar.addWidget(self.btn_home)

        self.btn_theme = QPushButton()
        self.btn_theme.setFixedSize(46, 40)
        self.btn_theme.clicked.connect(self.toggle_theme)
        top_bar.addWidget(self.btn_theme)

        top_bar.addStretch(1)

        self.lbl_lang = QLabel()
        top_bar.addWidget(self.lbl_lang)

        self.lang_combo = QComboBox()
        for code, label in LANG_LABELS.items():
            self.lang_combo.addItem(f"{code.upper()} – {label}", code)
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        top_bar.addWidget(self.lang_combo)

        main_layout.addLayout(top_bar)

        input_group = QGroupBox()
        input_layout = QGridLayout(input_group)
        input_layout.setHorizontalSpacing(12)
        input_layout.setVerticalSpacing(10)

        self.lbl_url = QLabel()
        self.url_entry = QLineEdit()
        self.url_entry.setPlaceholderText("https://data.matricula-online.eu/…")
        input_layout.addWidget(self.lbl_url, 0, 0)
        input_layout.addWidget(self.url_entry, 0, 1, 1, 3)

        self.lbl_outdir = QLabel()
        self.outdir_entry = QLineEdit()
        input_layout.addWidget(self.lbl_outdir, 1, 0)
        input_layout.addWidget(self.outdir_entry, 1, 1, 1, 2)

        self.btn_choose = QPushButton()
        self.btn_choose.clicked.connect(self.choose_dir)
        input_layout.addWidget(self.btn_choose, 1, 3)

        self.lbl_pages = QLabel()
        self.pages_entry = QLineEdit()
        input_layout.addWidget(self.lbl_pages, 2, 0)
        input_layout.addWidget(self.pages_entry, 2, 1)

        self.lbl_pages_hint = QLabel()
        self.lbl_pages_hint.setObjectName("hintLabel")
        input_layout.addWidget(self.lbl_pages_hint, 2, 2, 1, 2)

        main_layout.addWidget(input_group)

        self.btn_add_book = QPushButton()
        self.btn_add_book.setObjectName("addBookButton")
        self.btn_add_book.clicked.connect(self.add_book)

        self.btn_delete_book = QPushButton()
        self.btn_delete_book.setObjectName("deleteBookButton")
        self.btn_delete_book.clicked.connect(self.delete_book)

        self.btn_change_pages = QPushButton()
        self.btn_change_pages.setObjectName("changePagesButton")
        self.btn_change_pages.clicked.connect(self.change_pages)

        self.btn_download = QPushButton()
        self.btn_download.setObjectName("downloadButton")
        self.btn_download.clicked.connect(self.start_books)

        self.btn_stop = QPushButton()
        self.btn_stop.setObjectName("stopButton")
        self.btn_stop.clicked.connect(self.stop_download)

        self.btn_reset = QPushButton()
        self.btn_reset.setObjectName("resetButton")
        self.btn_reset.clicked.connect(self.reset_books)

        self.btn_save_list = QPushButton()
        self.btn_save_list.clicked.connect(self.save_list)

        self.btn_load_list = QPushButton()
        self.btn_load_list.clicked.connect(self.load_list)

        self.btn_export_pdf = QPushButton()
        self.btn_export_pdf.clicked.connect(self.export_pdf)

        self.btn_log_toggle = QPushButton()
        self.btn_log_toggle.clicked.connect(self.toggle_log)

        self.btn_save_log = QPushButton()
        self.btn_save_log.clicked.connect(self.save_log_to_file)

        action_rows = []
        for _ in range(3):
            row = QHBoxLayout()
            row.setSpacing(10)
            action_rows.append(row)
            main_layout.addLayout(row)

        action_rows[0].addStretch(1)
        for btn in (self.btn_add_book, self.btn_delete_book, self.btn_change_pages):
            btn.setMinimumHeight(42)
            btn.setMinimumWidth(185)
            action_rows[0].addWidget(btn)
        action_rows[0].addStretch(1)

        action_rows[1].addStretch(1)
        for btn in (self.btn_download, self.btn_stop, self.btn_reset):
            btn.setMinimumHeight(42)
            btn.setMinimumWidth(185)
            action_rows[1].addWidget(btn)
        action_rows[1].addStretch(1)

        action_rows[2].addStretch(1)
        for btn in (self.btn_save_list, self.btn_load_list, self.btn_export_pdf, self.btn_save_log, self.btn_log_toggle):
            btn.setMinimumHeight(40)
            btn.setMinimumWidth(155)
            action_rows[2].addWidget(btn)
        action_rows[2].addStretch(1)

        self.lbl_waiting = QLabel()
        main_layout.addWidget(self.lbl_waiting)

        self.table = QTableWidget(0, 3)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.cellDoubleClicked.connect(self.open_book_url)
        self.table.setMinimumHeight(320)
        main_layout.addWidget(self.table, 1)

        progress_row = QHBoxLayout()
        self.lbl_progress = QLabel()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_label = QLabel("0%")
        self.progress_label.setMinimumWidth(48)
        progress_row.addWidget(self.lbl_progress)
        progress_row.addWidget(self.progress_bar, 1)
        progress_row.addWidget(self.progress_label)
        main_layout.addLayout(progress_row)

        self.log_container = QGroupBox()
        self.log_container_layout = QVBoxLayout(self.log_container)
        self.log_container_layout.setContentsMargins(8, 8, 8, 8)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(160)
        self.log_container_layout.addWidget(self.log_text)
        main_layout.addWidget(self.log_container)
        self.log_container.hide()

        delete_action = QAction(self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self.delete_book)
        self.addAction(delete_action)

        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

    def _load_theme_setting(self) -> bool:
        value = self.settings.value("ui/is_dark", False)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "on")

    def _save_theme_setting(self) -> None:
        self.settings.setValue("ui/is_dark", self.is_dark)

    def _load_language_setting(self) -> str:
        value = str(self.settings.value("ui/lang", "de") or "de").strip().lower()
        return value if value in LANG else "de"

    def _save_language_setting(self) -> None:
        self.settings.setValue("ui/lang", self.lang)

    def apply_theme(self) -> None:
        self.setStyleSheet(dark_stylesheet() if self.is_dark else light_stylesheet())
        self.btn_theme.setText("☀️" if self.is_dark else "🪩")
        self.btn_theme.setToolTip(self._t("theme_light") if self.is_dark else self._t("theme_dark"))

    @Slot()
    def toggle_theme(self) -> None:
        self.is_dark = not self.is_dark
        self._save_theme_setting()
        self.apply_theme()

    def on_language_changed(self) -> None:
        code = self.lang_combo.currentData()
        if not code or code == self.lang:
            return
        self.lang = code
        self._save_language_setting()
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setWindowTitle(self._t("title"))
        self.btn_home.setText(self._t("home"))
        self.lbl_lang.setText(self._t("lang_label"))
        self.lbl_url.setText(self._t("book_url"))
        self.lbl_outdir.setText(self._t("target_dir"))
        self.btn_choose.setText(self._t("choose_dir"))
        self.lbl_pages.setText(self._t("pages"))
        self.lbl_pages_hint.setText(self._t("pages_hint"))

        self.btn_add_book.setText(self._t("add_book"))
        self.btn_delete_book.setText(self._t("delete_book"))
        self.btn_change_pages.setText(self._t("change_pages"))
        self.btn_download.setText(self._t("download"))
        self.btn_stop.setText(self._t("stop"))
        self.btn_reset.setText(self._t("reset"))
        self.btn_save_list.setText(self._t("save_list"))
        self.btn_load_list.setText(self._t("load_list"))
        self.btn_export_pdf.setText(self._t("export_pdf"))
        self.btn_save_log.setText(self._t("log_save"))
        self.btn_log_toggle.setText(self._t("log_close") if self.log_container.isVisible() else self._t("log_open"))

        idx = self.lang_combo.findData(self.lang)
        if idx >= 0 and self.lang_combo.currentIndex() != idx:
            self.lang_combo.blockSignals(True)
            self.lang_combo.setCurrentIndex(idx)
            self.lang_combo.blockSignals(False)

        self.lbl_waiting.setText(self._t("waiting_list"))
        self.table.setHorizontalHeaderLabels([self._t("col_book"), self._t("col_pages"), self._t("col_status")])
        self.lbl_progress.setText(self._t("global_progress"))
        self.log_container.setTitle(self._t("log_title"))
        self.statusBar().showMessage(self._t("status_ready"))
        self.apply_theme()

    @Slot()
    def choose_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, self._t("choose_dir"))
        if path:
            self.outdir_entry.setText(path)

    @Slot()
    def add_book(self) -> None:
        url = self.url_entry.text().strip()
        if not url:
            QMessageBox.warning(self, self._t("title"), self._t("error_no_url"))
            return
        if not any(domain in url for domain in SUPPORTED_DOMAINS):
            QMessageBox.warning(self, self._t("title"), self._t("error_no_supported"))
            return
        if "archiviodiocesanoreggiobova.it" in url and "/photo_details/" not in url:
            QMessageBox.critical(self, self._t("title"), self._t("error_photo_details"))
            return

        book = BookEntry(url=url, outdir=self.outdir_entry.text().strip() or os.getcwd(), pages=self.pages_entry.text().strip())
        self.books.append(book)
        self._append_book_to_table(book)
        self.log(f"[+] Buch hinzugefügt: {url}")
        self.url_entry.clear()

    def _append_book_to_table(self, book: BookEntry) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(book.url))
        self.table.setItem(row, 1, QTableWidgetItem(book.pages))
        self.table.setItem(row, 2, QTableWidgetItem(book.status))

    @Slot()
    def delete_book(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            if 0 <= row < len(self.books):
                del self.books[row]
                self.table.removeRow(row)
        if rows:
            self.log("[-] Buch gelöscht.")

    @Slot()
    def change_pages(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if not rows:
            QMessageBox.warning(self, self._t("title"), self._t("error_no_selection"))
            return
        current_value = self.books[rows[0]].pages if rows else ""
        value, ok = QInputDialog.getText(self, self._t("pages_dialog_title"), self._t("pages"), text=current_value)
        if not ok:
            return
        for row in rows:
            self.books[row].pages = value.strip()
            self.table.item(row, 1).setText(self.books[row].pages)
        self.log(f"[*] Seitenbereich geändert: {value.strip()}")

    @Slot()
    def start_books(self) -> None:
        if not self.books:
            QMessageBox.warning(self, self._t("title"), self._t("error_no_book"))
            return
        if self.worker and self.worker.isRunning():
            return

        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")
        self.worker = DownloaderWorker(self.books, self)
        self.worker.log_message.connect(self.log)
        self.worker.book_status.connect(self.update_book_status)
        self.worker.global_progress.connect(self.update_global_progress)
        self.worker.finished_signal.connect(self.download_finished)
        self.worker.start()

        self.btn_download.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.statusBar().showMessage(self._t("status_running"))

    @Slot()
    def stop_download(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.statusBar().showMessage(self._t("status_stopped"))

    @Slot()
    def reset_books(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, self._t("title"), self._t("error_running_reset"))
            return
        self.books.clear()
        self.table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")
        self.log("[*] Warteliste zurückgesetzt.")

    @Slot(int, str)
    def update_book_status(self, row: int, status: str) -> None:
        if 0 <= row < len(self.books):
            self.books[row].status = status
        item = self.table.item(row, 2)
        if item is None:
            item = QTableWidgetItem(status)
            self.table.setItem(row, 2, item)
        else:
            item.setText(status)

    @Slot(float)
    def update_global_progress(self, value: float) -> None:
        progress = int(value)
        self.progress_bar.setValue(progress)
        self.progress_label.setText(f"{progress}%")

    @Slot()
    def download_finished(self) -> None:
        self.btn_download.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.statusBar().showMessage(self._t("status_finished"))

    def export_pdf(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self._t("pdf_choose"))
        if not folder:
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            self._t("export_pdf"),
            os.path.join(os.path.dirname(folder), f"{os.path.basename(folder)}.pdf"),
            "PDF Files (*.pdf)",
        )
        if not save_path:
            return
        try:
            self.log(f"[*] Erstelle PDF: {save_path}")
            create_pdf_from_folder(folder, save_path)
            self.log(f"[+] PDF erstellt: {save_path}")
            QMessageBox.information(self, self._t("title"), self._t("pdf_created").format(path=save_path))
        except FileNotFoundError:
            QMessageBox.warning(self, self._t("title"), self._t("pdf_error_no_books"))
        except Exception as exc:
            self.log(f"[!] Fehler beim PDF-Erstellen: {exc}")
            QMessageBox.critical(self, self._t("title"), self._t("pdf_error").format(error=exc))

    def save_list(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            self._t("save_list"),
            self._t("save_list_default"),
            "JSON Files (*.json);;Text Files (*.txt)",
        )
        if not path:
            return
        try:
            if path.lower().endswith(".txt"):
                with open(path, "w", encoding="utf-8") as handle:
                    for book in self.books:
                        handle.write(f"{book.url} | {book.outdir} | {book.pages}\n")
            else:
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump([book.to_dict() for book in self.books], handle, indent=2, ensure_ascii=False)
            self.log(f"[+] Warteliste exportiert: {path}")
        except Exception as exc:
            QMessageBox.critical(self, self._t("title"), str(exc))

    def load_list(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._t("load_list"),
            "",
            "Supported Files (*.json *.txt)",
        )
        if not path:
            return
        try:
            imported: list[BookEntry] = []
            if path.lower().endswith(".json"):
                with open(path, "r", encoding="utf-8") as handle:
                    imported = [BookEntry.from_dict(item) for item in json.load(handle)]
            else:
                with open(path, "r", encoding="utf-8") as handle:
                    for line in handle:
                        parts = [part.strip() for part in line.split("|")]
                        if len(parts) >= 2:
                            imported.append(BookEntry(url=parts[0], outdir=parts[1], pages=parts[2] if len(parts) > 2 else ""))
            for book in imported:
                self.books.append(book)
                self._append_book_to_table(book)
            self.log(f"[+] {len(imported)} Bücher importiert.")
        except Exception as exc:
            QMessageBox.critical(self, self._t("title"), str(exc))

    def toggle_log(self) -> None:
        is_visible = self.log_container.isVisible()
        self.log_container.setVisible(not is_visible)
        self.btn_log_toggle.setText(self._t("log_open") if is_visible else self._t("log_close"))

    def save_log_to_file(self) -> None:
        text = self.log_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, self._t("title"), self._t("log_empty"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            self._t("log_save"),
            self._t("save_log_default"),
            "Text Files (*.txt)",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        QMessageBox.information(self, self._t("title"), self._t("log_saved"))

    def open_book_url(self, row: int, _column: int) -> None:
        if 0 <= row < len(self.books):
            QDesktopServices.openUrl(QUrl(self.books[row].url))

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"{timestamp} {message}")
