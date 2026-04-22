from __future__ import annotations

import os

from PySide6.QtCore import QThread, Signal

from matriculadownloader.i18n import LANG
from matriculadownloader.models import BookEntry
from matriculadownloader.network import download_binary, extract_image_urls
from matriculadownloader.text_utils import ensure_dir, parse_pages, safe_name


class DownloaderWorker(QThread):
    log_message = Signal(str)
    book_status = Signal(int, str)
    global_progress = Signal(float)
    finished_signal = Signal()

    def __init__(self, books: list[BookEntry], ui_lang: str = "de", parent=None):
        super().__init__(parent)
        self.books = books
        self.ui_lang = ui_lang
        self._stop_requested = False

    def _t(self, key: str) -> str:
        lang = self.ui_lang if self.ui_lang in LANG else "de"
        return LANG.get(lang, LANG["de"]).get(key, LANG.get("en", {}).get(key, LANG["de"].get(key, key)))

    def stop(self) -> None:
        self._stop_requested = True

    def log(self, message: str) -> None:
        self.log_message.emit(message)

    def run(self) -> None:
        total = len(self.books)

        for idx, book in enumerate(self.books):
            if self._stop_requested:
                self.log(self._t("worker_cancelled"))
                self.book_status.emit(idx, "❌")
                break

            progress = int((idx / total) * 100) if total else 0
            self.global_progress.emit(progress)

            self.log(f"[+] {self._t('worker_opening').format(url=book.url)}")
            self.book_status.emit(idx, "🔄")

            try:
                image_urls, folder_name, meta = extract_image_urls(book.url)
            except Exception as exc:
                self.log(self._t("worker_load_error").format(url=book.url, error=exc))
                self.book_status.emit(idx, "❌")
                continue

            if not image_urls:
                self.log(self._t("worker_no_pages").format(url=book.url))
                self.book_status.emit(idx, "⚠️")
                continue

            ensure_dir(book.outdir)
            pages = parse_pages(book.pages, len(image_urls))
            if not pages:
                self.log(self._t("worker_invalid_pages").format(url=book.url, pages=book.pages))
                self.book_status.emit(idx, "⚠️")
                continue

            errors = 0

            for page_no in pages:
                if self._stop_requested:
                    errors += 1
                    break

                img_url = image_urls[page_no - 1]
                if "archiviodiocesanoreggiobova.it" in book.url:
                    parish = safe_name((meta.get("ort") or "").strip()) or "Unbekannt"
                    title_raw = (meta.get("title") or "").strip() or "Buch"
                    dater_raw = (meta.get("daterange") or "").strip()
                    base_name = safe_name(f"{title_raw} {dater_raw}".strip()) if dater_raw else safe_name(title_raw)
                    book_folder = os.path.join(book.outdir, parish, base_name)
                else:
                    ort_raw = (meta.get("ort") or meta.get("title") or folder_name or "").strip()
                    ort = safe_name(ort_raw) if ort_raw else "Unbekannt"
                    title_raw = (meta.get("title") or folder_name or "").strip()
                    dater_raw = (meta.get("daterange") or "").strip()
                    base_name = safe_name(f"{title_raw} {dater_raw}".strip()) if dater_raw else safe_name(title_raw or "Unbekannt")
                    book_folder = os.path.join(book.outdir, ort, base_name)

                ensure_dir(book_folder)
                target = os.path.join(book_folder, f"{base_name}_{page_no:03d}.jpg")

                try:
                    self.log(f"[💾] {self._t('worker_downloading').format(name=os.path.basename(target), path=target)}")
                    download_binary(img_url, target)
                except Exception as exc:
                    self.log(f"[!] {self._t('worker_download_error').format(page=page_no, error=exc)}")
                    errors += 1

            self.global_progress.emit(int(((idx + 1) / total) * 100) if total else 100)
            self.book_status.emit(idx, "✅" if errors == 0 else (f"⚠️ {errors}" if errors < len(pages) else "❌"))

        self.log(self._t("worker_all_done"))
        self.finished_signal.emit()
