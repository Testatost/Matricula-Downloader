from __future__ import annotations

import os

from PySide6.QtCore import QThread, Signal

from matriculadownloader.models import BookEntry
from matriculadownloader.network import download_binary, extract_image_urls
from matriculadownloader.text_utils import ensure_dir, parse_pages, safe_name


class DownloaderWorker(QThread):
    log_message = Signal(str)
    book_status = Signal(int, str)
    global_progress = Signal(float)
    finished_signal = Signal()

    def __init__(self, books: list[BookEntry], parent=None):
        super().__init__(parent)
        self.books = books
        self._stop_requested = False

    def stop(self) -> None:
        self._stop_requested = True

    def log(self, message: str) -> None:
        self.log_message.emit(message)

    def run(self) -> None:
        total = len(self.books)

        for idx, book in enumerate(self.books):
            if self._stop_requested:
                self.log("[*] Abgebrochen.")
                self.book_status.emit(idx, "❌")
                break

            progress = int((idx / total) * 100) if total else 0
            self.global_progress.emit(progress)

            self.log(f"[+] Lade Buch: {book.url}")
            self.book_status.emit(idx, "🔄")

            image_urls, folder_name, meta = extract_image_urls(book.url)
            if not image_urls:
                self.log(f"[!] Keine Seiten gefunden: {book.url}")
                self.book_status.emit(idx, "⚠️")
                continue

            ensure_dir(book.outdir)
            pages = parse_pages(book.pages, len(image_urls))
            self.log(f" → {len(pages)} Seiten ausgewählt.")
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
                    download_binary(img_url, target)
                    self.log(f"  ✅ {target}")
                except Exception as exc:
                    self.log(f"  ⚠️ Fehler bei Seite {page_no}: {exc}")
                    errors += 1

            self.global_progress.emit(int(((idx + 1) / total) * 100) if total else 100)
            self.book_status.emit(idx, "✅" if errors == 0 else (f"⚠️ {errors}" if errors < len(pages) else "❌"))

        self.log("[*] Alle Bücher fertig.")
        self.finished_signal.emit()
