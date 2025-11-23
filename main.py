import os
import re
import base64
import threading
import json
import webbrowser
import requests
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from bs4 import BeautifulSoup
from PIL import Image
from datetime import datetime
import customtkinter as ctk

# ------------------------------------------------------------
# KONSTANTEN
# ------------------------------------------------------------

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0",
    "Referer": "https://data.matricula-online.eu/",
}

FONT_DEFAULT = ("Calibri", 12)
REQ_TIMEOUT = 25

TXT = {
    "title": "📜 Matricula Downloader",
    "book_url": "Buch-URL:",
    "target_dir": "Zielordner:",
    "choose_dir": "📂 Zielordner wählen",
    "open_home": "🏠 Matricula",
    "add_book": "➕ Hinzufügen",
    "delete_book": "🗑️ Löschen",
    "import_list": "📥 Importieren",
    "export_list": "📤 Exportieren",
    "pages": "Seiten:",
    "pages_hint": "(z. B. 1,3,5-10; leer = alle)",
    "download": "⬇️ Herunterladen",
    "stop": "⏹️ Stopp",
    "reset": "🔄 Zurücksetzen",
    "pdf": "📄 Als PDF speichern",
    "waiting_list": "Warteliste:",
    "col_book": "Buch / ID",
    "col_pages": "Seiten",
    "col_status": "Status",
    "progress": "Gesamtfortschritt:",
}

# ------------------------------------------------------------
# HILFSFUNKTIONEN
# ------------------------------------------------------------

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def safe_name(s: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]+', "_", s.strip())
    return "".join(c if c.isprintable() else "_" for c in s)


def open_homepage():
    webbrowser.open("https://data.matricula-online.eu/de/bestande/")


# ------------------------------------------------------------
# METADATEN-EXTRAKTION
# ------------------------------------------------------------

def extract_book_title(soup: BeautifulSoup, url: str) -> str:
    title = None

    h2 = soup.find("h2")
    if h2 and h2.text.strip():
        title = h2.text.strip()

    if not title and "findbuch.net" in url:
        h1 = soup.find("h1")
        if h1 and h1.text.strip():
            title = h1.text.strip()
        else:
            td = soup.find("td", class_="text2")
            if td and td.text.strip():
                title = td.text.strip()

    if not title and soup.title and soup.title.text.strip():
        title = soup.title.text.strip()

    if not title:
        parts = [p for p in url.split("/") if p]
        title = parts[-1] if parts else "Unbekanntes_Buch"

    return safe_name(title)


def extract_page_metadata(soup: BeautifulSoup, html_text: str, book_url: str) -> dict:
    meta = {}

    label_map = {
        "Signatur": "signatur",
        "Bestand": "bestand",
        "Datierung": "daterange",
        "Titel": "title",
        "Edition": "edition",
        "Ersteller": "creator",
        "Bemerkung": "remark",
    }

    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        label_text = cells[0].get_text(strip=True)
        value_text = cells[1].get_text(strip=True)

        if label_text.endswith(":"):
            label_text_stripped = label_text[:-1]
        else:
            label_text_stripped = label_text

        if label_text_stripped in label_map:
            key = label_map[label_text_stripped]
            if value_text:
                meta[key] = value_text

    if "kirchenbücher-südtirol" in book_url:
        ort = None
        bestand = meta.get("bestand", "")

        m = re.search(r"KB_([A-Z_]+)", bestand)
        if m:
            ort_raw = m.group(1)
            tokens = ort_raw.split("_")
            if tokens:
                ort = tokens[-1].title()

        if not ort:
            m2 = re.search(r"~KB_([A-Z_]+)\._~", html_text)
            if m2:
                ort_raw = m2.group(1)
                tokens = ort_raw.split("_")
                if tokens:
                    ort = tokens[-1].title()

        if ort:
            meta["ort"] = ort

    return meta


def enrich_matricula_metadata(soup: BeautifulSoup, html_text: str, meta: dict) -> dict:
    label = soup.find(string=re.compile(r"Pfarre/Ort"))
    if label:
        parent = label.parent
        a = parent.find_next("a")
        if a and a.get_text(strip=True):
            meta.setdefault("ort", a.get_text(strip=True))
        else:
            text = parent.get_text(" ", strip=True)
            m = re.search(r"Pfarre/Ort\s+(.+)", text)
            if m and m.group(1).strip():
                meta.setdefault("ort", m.group(1).strip())

    sig_label = soup.find(string=re.compile(r"Signatur"))
    if sig_label:
        text = sig_label.parent.get_text(" ", strip=True)
        m = re.search(r"Signatur\s+([A-Z0-9+ ]+)", text)
        if m:
            signatur = m.group(1).strip()
            meta.setdefault("signatur", signatur)

    bt_label = soup.find(string=re.compile(r"Buchtyp"))
    if bt_label:
        text = bt_label.parent.get_text(" ", strip=True)
        m = re.search(r"Buchtyp\s+(.+)", text)
        if m:
            buchtyp = m.group(1).strip()
            meta.setdefault("buchtyp", buchtyp)

    if "title" not in meta:
        if meta.get("buchtyp") or meta.get("signatur"):
            meta["title"] = f"{meta.get('buchtyp','')} {meta.get('signatur','')}".strip()

    if "daterange" not in meta or not meta["daterange"]:
        m = re.search(r"(\d{4}).{0,40}(\d{4})", html_text, re.DOTALL)
        if m:
            meta["daterange"] = f"{m.group(1)}-{m.group(2)}"

    return meta


def extract_matricula_metadata(html_text: str) -> dict:
    meta = {}

    # 1️⃣ ORT ERKENNEN
    m_ort = re.search(r'<th>Pfarre/Ort</th><td><a [^>]*>([^<]+)</a>', html_text)
    if not m_ort:
        m_ort = re.search(r'<li class="breadcrumb-item"><a [^>]*>/[^>]*/([^<]+)/</a>', html_text)
    if not m_ort:
        m_ort = re.search(r'<title>[^|]*\|\s*([^|]+)\s*\|', html_text)

    if m_ort:
        meta["ort"] = m_ort.group(1).strip()

    # 2️⃣ BUCHTITEL ERKENNEN
    m_title = re.search(
        r'<li class="breadcrumb-item active">\s*([^<]+?)\s*\|',
        html_text
    )

    if not m_title:
        m_title = re.search(
            r'<th>Buchtyp</th><td>([^<]+)</td>',
            html_text
        )

    if not m_title:
        m_title = re.search(
            r'<title>([^|]+?)\|',
            html_text
        )

    if not m_title:
        m_json = re.search(r'MatriculaDocView\.init\(\{(.*?)\}\)', html_text, re.DOTALL)
        if m_json:
            m_desc = re.search(r'"description"\s*:\s*"([^"]+)"', m_json.group(1))
            m_book = re.search(r'"book"\s*:\s*"([^"]+)"', m_json.group(1))
            if m_desc:
                title_str = m_desc.group(1)
                if m_book:
                    title_str += " " + m_book.group(1)
                m_title = [title_str]

    if m_title:
        meta["title"] = m_title[0] if isinstance(m_title, list) else m_title.group(1).strip()

    m_date = re.search(
        r'<th>Datum von</th><td>([^<]+)</td>.*?<th>Datum bis</th><td>([^<]+)</td>',
        html_text,
        re.DOTALL
    )
    if m_date:
        d1 = m_date.group(1).strip()
        d2 = m_date.group(2).strip()

        y1 = re.search(r'(\d{4})', d1)
        y2 = re.search(r'(\d{4})', d2)

        if y1 and y2:
            meta["daterange"] = f"{y1.group(1)}–{y2.group(1)}"

    return meta


# ------------------------------------------------------------
# BILD-URLS / METADATEN je nach Seite
# ------------------------------------------------------------

def extract_image_urls(book_url: str):
    try:
        urls = []
        folder_name = "Unbekannt"
        meta = {}

        # Grund-HTML laden
        r = requests.get(book_url, headers=HEADERS, timeout=REQ_TIMEOUT)
        r.raise_for_status()
        html_text = r.text
        soup = BeautifulSoup(html_text, "html.parser")

        image_urls = []
        meta = extract_page_metadata(soup, html_text, book_url)

        # ------------------------------------------------------------
        # DFG-VIEWER
        # ------------------------------------------------------------
        if "dfg-viewer.de" in book_url:

            # page=1 erzwingen
            if "tx_dlf[page]" not in book_url:
                sep = "&" if "?" in book_url else "?"
                book_url = f"{book_url}{sep}tx_dlf[page]=1"

            r = requests.get(book_url, headers=HEADERS, timeout=REQ_TIMEOUT)
            r.raise_for_status()
            html = r.text
            soup = BeautifulSoup(html, "html.parser")

            # Titel
            title_dd = soup.select_one("dd.tx-dlf-title")
            title = title_dd.get_text(strip=True) if title_dd else "Unbekannt"
            title = title.strip()

            # Bestand
            ctx_dds = soup.select("dl.tx-dlf-metadata-titledata dd")
            bestand_raw = ctx_dds[1].get_text(strip=True) if len(ctx_dds) >= 2 else ""

            m_bestand = re.search(r"Bestand:\s*(.+)", bestand_raw)
            bestand_full = m_bestand.group(1).strip() if m_bestand else ""

            ort_raw = bestand_full.split(" - ")[0]
            ort_parts = ort_raw.split(" ", 1)
            ort = ort_parts[1].strip() if len(ort_parts) > 1 else ort_raw.strip()

            m_years = re.search(r"(\d{4})\D+(\d{4})", bestand_full)
            years = f"{m_years.group(1)}-{m_years.group(2)}" if m_years else ""

            meta = {
                "title": title,
                "ort": ort,
                "daterange": years,
            }

            folder_name = safe_name(f"{title} {years}") if years else safe_name(title)

            options = soup.select("select[name='tx_dlf[page]'] option")
            total_pages = len(options) if options else 1

            m = re.search(
                r'tx_dlf_viewer\s*=\s*new dlfViewer\([^)]*?images\s*:\s*\[\s*\{\s*"url"\s*:\s*"([^"]+)"',
                html,
                re.DOTALL
            )

            if not m:
                return [], folder_name, meta

            first_url = m.group(1).replace("\\/", "/")
            base_url, filename = first_url.rsplit("/", 1)

            m2 = re.match(r"(.+_)(\d{4})_(\d{4})_(\d{3}\.jpg)", filename)
            if not m2:
                return [first_url], folder_name, meta

            prefix, first_page, fix_mid, tail = m2.groups()

            urls = []
            for i in range(1, total_pages + 1):
                urls.append(f"{base_url}/{prefix}{i:04d}_{fix_mid}_{tail}")

            return urls, folder_name, meta

        # ------------------------------------------------------------
        # MATRICULA
        # ------------------------------------------------------------
        if "matricula-online.eu" in book_url:

            js_meta = extract_matricula_metadata(html_text)
            for k, v in js_meta.items():
                if v:
                    meta[k] = v

            meta = enrich_matricula_metadata(soup, html_text, meta)

            if not meta.get("title"):
                meta["title"] = extract_book_title(soup, book_url)

            folder_name = safe_name(meta.get("ort", meta["title"]))

            if "MatriculaDocView" in html_text:
                script_tags = soup.find_all("script")
                for tag in script_tags:
                    text = tag.string or tag.text
                    if not text or '"files": [' not in text:
                        continue

                    m_files = re.search(r'"files":\s*(\[[^\]]+\])', text)
                    if not m_files:
                        continue
                    raw_list = m_files.group(1)

                    encoded = re.findall(r'"(/image/[^"]+)"', raw_list)
                    for ef in encoded:
                        b64 = ef.split("/image/")[-1].strip("/")
                        try:
                            missing = len(b64) % 4
                            if missing:
                                b64 += "=" * (4 - missing)
                            decoded = base64.b64decode(b64).decode("utf-8")
                            if decoded.startswith("http"):
                                image_urls.append(decoded)
                            else:
                                image_urls.append("https://img.data.matricula-online.eu" + decoded)
                        except:
                            continue

                return sorted(set(image_urls)), folder_name, meta

        # ------------------------------------------------------------
        # FINDBUCH.NET
        # ------------------------------------------------------------
        if "findbuch.net" in book_url:
            possible = re.findall(r"/a_pics/ks/[^\"']+\.jpg", html_text)
            for p in possible:
                full = f"https://www.findbuch.net{p}"
                if full not in image_urls:
                    image_urls.append(full)

            if not image_urls:
                onclick_links = re.findall(r"javascript:m_click\(\d+\)", html_text)
                if onclick_links:
                    base_guess = re.search(r'(/a_pics/ks/[^\s"]+_)\d{3}\.jpg', html_text)
                    if base_guess:
                        base_url = "https://www.findbuch.net" + base_guess.group(1)
                        indices = [int(x.split("(")[1].split(")")[0]) for x in onclick_links]
                        for i in indices:
                            img_num = f"{i+3:03d}"
                            image_urls.append(base_url + img_num + ".jpg")

            folder_name = extract_book_title(soup, book_url)

            return sorted(set(image_urls)), folder_name, meta

        # ------------------------------------------------------------
        # ARCHIVIO DIOCESANO REGGIO CALABRIA–BOVA (ITALIEN)
        # ------------------------------------------------------------
        if "archiviodiocesanoreggiobova.it" in book_url:

            # Text der Seite (für die Info-Zeilen)
            page_text = soup.get_text("\n", strip=True)

            def get_field(label: str) -> str:
                m = re.search(rf'{label}:\s*([^\n]+)', page_text, re.I)
                return m.group(1).strip() if m else ""

            file_code = get_field("File") or "page"
            parish = get_field("Parish") or "Unbekannt"
            typology = get_field("Typology") or "Unbekannt"
            period = get_field("Period") or ""

            # Seitenanzahl: "Image 1 of 86"
            m_total = re.search(r'Image\s+\d+\s+of\s+(\d+)', page_text, re.I)
            total_pages = int(m_total.group(1)) if m_total else 1

            # Album-ID aus URL
            m_album = re.search(r"/photo_details/(\d+)/", book_url)
            album_id = m_album.group(1) if m_album else "unknown"

            # Basis-Dateiname (z.B. MRASRGCLB17821790P001)
            base_filename = file_code
            m_fn = re.match(r"(.+?)(\d{3})$", base_filename)
            if not m_fn:
                # Falls unerwartetes Format → lieber abbrechen
                return [], safe_name(parish), {
                    "ort": parish,
                    "title": typology,
                    "daterange": period
                }

            prefix, first_page = m_fn.groups()

            base_img_url = (
                f"https://www.archiviodiocesanoreggiobova.it/wp-content/uploads/wp_photo_seller/{album_id}"
            )

            urls = []
            for i in range(1, total_pages + 1):
                fname = f"{prefix}{i:03d}.jpg"
                urls.append(f"{base_img_url}/watermark_{fname}")

            # Metadaten für die spätere Ordnerlogik
            meta = {
                "ort": parish,       # Parish
                "title": typology,   # Typology
                "daterange": period  # z.B. 1782-1790
            }

            # folder_name wird bei Italien im Downloader nicht benutzt,
            # aber wir geben einen sinnvollen Wert zurück:
            folder_name = safe_name(f"{typology} {period}".strip() or typology)

            return urls, folder_name, meta

        # Fallback
        return urls, folder_name, meta

    except Exception:
        return [], "Unbekanntes_Buch", {}


# ------------------------------------------------------------
# SEITENLISTE
# ------------------------------------------------------------

def parse_pages(pages_str: str, total: int) -> list[int]:
    if not pages_str.strip():
        return list(range(1, total + 1))

    result = []
    for part in pages_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                a, b = map(int, part.split("-"))
                result.extend(range(a, b + 1))
            except Exception:
                pass
        else:
            try:
                result.append(int(part))
            except Exception:
                pass

    return [p for p in sorted(set(result)) if 1 <= p <= total]


# ------------------------------------------------------------
# DOWNLOADER
# ------------------------------------------------------------

class Downloader:
    def __init__(self, books, log, update, stop_flag):
        self.books = books
        self.log = log
        self.update = update
        self.stop_flag = stop_flag

    def run(self):
        total = len(self.books)
        for idx, b in enumerate(self.books):
            if self.stop_flag():
                break

            perc = int((idx / total) * 100) if total else 0
            self.update("global", perc)

            url = b["url"]
            outdir = b["outdir"]
            pages_str = b["pages"]

            self.log(f"[+] Lade Buch: {url}")
            self.update(idx, "🔄")

            image_urls, folder_name, meta = extract_image_urls(url)
            self.meta = meta

            if not image_urls:
                self.log(f"[!] Keine Seiten gefunden: {url}")
                self.update(idx, "⚠️")
                continue

            ensure_dir(outdir)

            pages = parse_pages(pages_str, len(image_urls))
            self.log(f" → {len(pages)} Seiten ausgewählt.")

            errors = 0

            for i in pages:
                if self.stop_flag():
                    errors += 1
                    break

                img_url = image_urls[i - 1]

                # ------------------------------------------------
                # ORDNERVERARBEITUNG NACH DOMAIN
                # ------------------------------------------------

                # 1) ITALIEN: Archivio Diocesano Reggio Calabria–Bova
                if "archiviodiocesanoreggiobova.it" in url:
                    parish_raw = (meta.get("ort") or "").strip()
                    parish_safe = safe_name(parish_raw) if parish_raw else "Unbekannt"

                    title_raw = (meta.get("title") or "").strip() or "Buch"
                    dater_raw = (meta.get("daterange") or "").strip()
                    if dater_raw:
                        base_name = safe_name(f"{title_raw} {dater_raw}")
                    else:
                        base_name = safe_name(title_raw)

                    book_folder = os.path.join(outdir, parish_safe, base_name)
                    ensure_dir(book_folder)
                    fn = os.path.join(book_folder, f"{base_name}_{i:03d}.jpg")

                # 2) STANDARD: Matricula, DFG, Findbuch
                else:
                    ort_raw = (meta.get("ort") or meta.get("title") or folder_name or "").strip()
                    ort = safe_name(ort_raw) if ort_raw else "Unbekannt"

                    title_raw = (meta.get("title") or folder_name or "").strip()
                    dater_raw = (meta.get("daterange") or "").strip()

                    if dater_raw:
                        base_name = f"{title_raw} {dater_raw}"
                    else:
                        base_name = title_raw

                    base_name = safe_name(base_name) if base_name else "Unbekannt"

                    book_folder = os.path.join(outdir, ort, base_name)
                    ensure_dir(book_folder)
                    fn = os.path.join(book_folder, f"{base_name}_{i:03d}.jpg")

                # ------------------------------------------------
                # DOWNLOAD
                # ------------------------------------------------
                try:
                    r = requests.get(img_url, headers=HEADERS, stream=True, timeout=30)
                    r.raise_for_status()
                    with open(fn, "wb") as f:
                        for chunk in r.iter_content(65536):
                            f.write(chunk)
                    self.log(f"  ✅ {fn}")
                except Exception as e:
                    self.log(f"  ⚠️ Fehler bei Seite {i}: {e}")
                    errors += 1

            self.update("global", 100)
            if errors == 0:
                self.update(idx, "✅")
            else:
                self.update(idx, f"⚠️ {errors}")


# ------------------------------------------------------------
# GUI (CustomTkinter)
# ------------------------------------------------------------

class DownloaderGUI:
    def __init__(self, master):
        self.master = master
        self.books = []
        self.stop_flag = False

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        master.title(TXT["title"])
        master.geometry("1000x900")

        self.topbar = ctk.CTkFrame(master, corner_radius=0, fg_color=("white", "#1e1f22"))
        self.topbar.pack(fill="x")

        self.btn_home = ctk.CTkButton(self.topbar, text=TXT["open_home"], command=open_homepage, width=120)
        self.btn_home.pack(side="left", padx=12, pady=10)

        self.main = ctk.CTkFrame(master, corner_radius=12, fg_color=("white", "#1e1f22"))
        self.main.pack(fill="x", padx=12, pady=(12, 6))

        self.grid_left = ctk.CTkFrame(self.main, fg_color="transparent")
        self.grid_left.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.main.grid_columnconfigure(0, weight=1)

        self.grid_right = ctk.CTkFrame(self.main, fg_color="transparent")
        self.grid_right.grid(row=0, column=1, sticky="ne", padx=12, pady=12)

        self.lbl_url = ctk.CTkLabel(self.grid_left, text=TXT["book_url"], font=ctk.CTkFont(*FONT_DEFAULT))
        self.lbl_url.grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.url = ctk.CTkEntry(self.grid_left, width=700, font=ctk.CTkFont(*FONT_DEFAULT))
        self.url.grid(row=0, column=1, sticky="we", padx=(10, 0), pady=(0, 6))
        self.grid_left.grid_columnconfigure(1, weight=1)

        self.lbl_out = ctk.CTkLabel(self.grid_left, text=TXT["target_dir"], font=ctk.CTkFont(*FONT_DEFAULT))
        self.lbl_out.grid(row=1, column=0, sticky="w", pady=(0, 6))
        self.outdir = ctk.CTkEntry(self.grid_left, width=700, font=ctk.CTkFont(*FONT_DEFAULT))
        self.outdir.grid(row=1, column=1, sticky="we", padx=(10, 0), pady=(0, 6))

        self.btn_choose = ctk.CTkButton(
            self.grid_left,
            text=TXT["choose_dir"],
            command=self.choose_dir,
            width=180,
            fg_color="#6c757d",
            hover_color="#5b646b",
        )
        self.btn_choose.grid(row=1, column=2, padx=(10, 0), pady=(0, 6))

        self.lbl_pages = ctk.CTkLabel(self.grid_left, text=TXT["pages"], font=ctk.CTkFont(*FONT_DEFAULT))
        self.lbl_pages.grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.pages = ctk.CTkEntry(self.grid_left, width=300, font=ctk.CTkFont(*FONT_DEFAULT))
        self.pages.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(0, 2))

        self.lbl_hint = ctk.CTkLabel(
            self.grid_left,
            text=TXT["pages_hint"],
            font=ctk.CTkFont(family="Calibri", size=10, slant="italic"),
            text_color=("gray30", "gray70"),
        )
        self.lbl_hint.grid(row=3, column=1, sticky="w", padx=(10, 0), pady=(0, 6))

        self.btn_add = ctk.CTkButton(
            self.grid_right,
            text=TXT["add_book"],
            command=self.add_book,
            width=200,
            fg_color="#007bff",
            hover_color="#0a68d1",
        )
        self.btn_add.pack(pady=4)

        self.btn_del = ctk.CTkButton(
            self.grid_right,
            text=TXT["delete_book"],
            command=self.delete_book,
            width=200,
            fg_color="#dc3545",
            hover_color="#b52a38",
        )
        self.btn_del.pack(pady=4)

        self.btn_imp = ctk.CTkButton(
            self.grid_right,
            text=TXT["import_list"],
            command=self.import_list,
            width=200,
            fg_color="#ffc107",
            text_color="black",
            hover_color="#e0ad06",
        )
        self.btn_imp.pack(pady=4)

        self.btn_exp = ctk.CTkButton(
            self.grid_right,
            text=TXT["export_list"],
            command=self.export_list,
            width=200,
            fg_color="#17a2b8",
            hover_color="#148fa0",
        )
        self.btn_exp.pack(pady=4)

        self.downbar = ctk.CTkFrame(master, corner_radius=12, fg_color=("white", "#1e1f22"))
        self.downbar.pack(fill="x", padx=12, pady=(6, 6))

        self.btn_download = ctk.CTkButton(
            self.downbar,
            text=TXT["download"],
            command=self.start_download,
            width=200,
            fg_color="#28a745",
            hover_color="#218838",
        )
        self.btn_download.pack(side="left", padx=6, pady=10)

        self.btn_stop = ctk.CTkButton(
            self.downbar,
            text=TXT["stop"],
            command=self.stop_download,
            width=200,
            fg_color="#dc3545",
            hover_color="#b52a38",
        )
        self.btn_stop.pack(side="left", padx=6, pady=10)

        self.btn_reset = ctk.CTkButton(
            self.downbar,
            text=TXT["reset"],
            command=self.reset_books,
            width=200,
            fg_color="#007bff",
            hover_color="#0a68d1",
        )
        self.btn_reset.pack(side="left", padx=6, pady=10)

        self.btn_pdf = ctk.CTkButton(
            self.downbar,
            text=TXT["pdf"],
            command=self.create_pdf,
            width=200,
            fg_color="#6f42c1",
            hover_color="#5d37a3",
        )
        self.btn_pdf.pack(side="left", padx=6, pady=10)

        self.section_wait = ctk.CTkFrame(master, corner_radius=12, fg_color=("white", "#1e1f22"))
        self.section_wait.pack(fill="both", expand=False, padx=12, pady=(6, 6))

        self.lbl_wait = ctk.CTkLabel(self.section_wait, text=TXT["waiting_list"], font=ctk.CTkFont(*FONT_DEFAULT))
        self.lbl_wait.pack(anchor="w", padx=10, pady=(10, 0))

        self.tree_container = ctk.CTkFrame(self.section_wait, fg_color=("white", "#1e1f22"))
        self.tree_container.pack(fill="both", expand=True, padx=10, pady=10)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Treeview",
            rowheight=28,
            font=("Calibri", 11),
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#222222",
        )
        style.configure("Treeview.Heading", font=("Calibri", 12, "bold"))

        cols = ("book", "pages", "status")
        self.tree = ttk.Treeview(self.tree_container, columns=cols, show="headings")
        for c, t in zip(cols, [TXT["col_book"], TXT["col_pages"], TXT["col_status"]]):
            self.tree.heading(c, text=t)

        self.tree.column("book", width=700, anchor="w")
        self.tree.column("pages", width=140, anchor="center")
        self.tree.column("status", width=100, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        self.sb = ttk.Scrollbar(self.tree_container, orient="vertical", command=self.tree.yview)
        self.sb.pack(side="right", fill="y")
        self.tree.config(yscrollcommand=self.sb.set)

        self.section_prog = ctk.CTkFrame(master, corner_radius=12, fg_color=("white", "#1e1f22"))
        self.section_prog.pack(fill="x", padx=12, pady=(6, 6))

        self.lbl_prog = ctk.CTkLabel(self.section_prog, text=TXT["progress"], font=ctk.CTkFont(*FONT_DEFAULT))
        self.lbl_prog.pack(anchor="w", padx=10, pady=(10, 0))

        self.prog_container = ctk.CTkFrame(self.section_prog, fg_color="transparent")
        self.prog_container.pack(fill="x", padx=10, pady=10)

        self.pb = ctk.CTkProgressBar(self.prog_container, height=18)
        self.pb.set(0.0)
        self.pb.pack(side="left", fill="x", expand=True)

        self.pb_label = ctk.CTkLabel(self.prog_container, text="0%", font=ctk.CTkFont(*FONT_DEFAULT))
        self.pb_label.pack(side="left", padx=10)

        self.section_log = ctk.CTkFrame(master, corner_radius=12, fg_color=("white", "#1e1f22"))
        self.section_log.pack(fill="both", expand=True, padx=12, pady=(6, 12))

        self.log_text = ctk.CTkTextbox(self.section_log, height=180, font=ctk.CTkFont("Consolas", 11))
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)

    # GUI METHODS

    def choose_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.outdir.delete(0, "end")
            self.outdir.insert(0, d)

    def add_book(self):
        u = self.url.get().strip()
        if not u:
            messagebox.showwarning(TXT["title"], "Bitte eine Buch-URL eingeben.")
            return

        SUPPORTED = [
            "matricula-online.eu",
            "dfg-viewer.de",
            "findbuch.net",
            "archiviodiocesanoreggiobova.it"
        ]

        if not any(x in u for x in SUPPORTED):
            messagebox.showwarning(
                TXT["title"],
                "Nur matricula-online.eu, dfg-viewer.de, findbuch.net "
                "oder archiviodiocesanoreggiobova.it werden unterstützt."
            )
            return

        if "archiviodiocesanoreggiobova.it" in u:
            if "/photo_details/" not in u:
                messagebox.showerror(
                    TXT["title"],
                    "Dieser Link ist keine Buchseite.\n\n"
                    "Bitte öffnen Sie ein einzelnes Bild und kopieren Sie den "
                    "URL der Buchseite (enthält /photo_details/...)."
                )
                return

        self.books.append({
            "url": u,
            "outdir": self.outdir.get().strip() or os.getcwd(),
            "pages": self.pages.get().strip()
        })
        self.tree.insert("", "end", values=(u, self.pages.get().strip(), "⏳"))
        self.log(f"[+] Buch hinzugefügt: {u}")
        self.url.delete(0, "end")

    def delete_book(self):
        sel = self.tree.selection()
        for i in sel:
            idx = self.tree.index(i)
            del self.books[idx]
            self.tree.delete(i)
        self.log("[-] Buch gelöscht.")

    def reset_books(self):
        self.books.clear()
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.log("[*] Warteliste zurückgesetzt.")

    def export_list(self):
        if not self.books:
            messagebox.showinfo(TXT["title"], "Keine Einträge zum Exportieren.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Dateien", "*.json"), ("Textdateien", "*.txt")],
            title="Warteliste exportieren",
        )
        if not path:
            return
        try:
            if path.endswith(".json"):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.books, f, indent=2, ensure_ascii=False)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    for b in self.books:
                        f.write(f"{b['url']} | {b['outdir']} | {b['pages']}\n")
            self.log(f"[+] Warteliste exportiert: {path}")
        except Exception as e:
            messagebox.showerror(TXT["title"], f"Fehler beim Exportieren:\n{e}")

    def import_list(self):
        path = filedialog.askopenfilename(
            filetypes=[("Unterstützte Dateien", "*.json *.txt")],
            title="Warteliste importieren",
        )
        if not path:
            return
        try:
            imported = []
            if path.endswith(".json"):
                with open(path, "r", encoding="utf-8") as f:
                    imported = json.load(f)
            else:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = [p.strip() for p in line.split("|")]
                        if len(parts) >= 2:
                            imported.append(
                                {
                                    "url": parts[0],
                                    "outdir": parts[1],
                                    "pages": parts[2] if len(parts) > 2 else "",
                                }
                            )
            for b in imported:
                self.books.append(b)
                self.tree.insert("", "end", values=(b["url"], b["pages"], "⏳"))
            self.log(f"[+] {len(imported)} Bücher importiert.")
        except Exception as e:
            messagebox.showerror(TXT["title"], f"Fehler beim Importieren:\n{e}")

    def log(self, msg: str):
        line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")

    def update(self, idx, val):
        if idx == "global":
            frac = max(0.0, min(1.0, float(val) / 100.0))
            self.pb.set(frac)
            self.pb_label.configure(text=f"{int(val)}%")
        else:
            item = self.tree.get_children()[idx]
            vals = list(self.tree.item(item, "values"))
            vals[2] = val
            self.tree.item(item, values=vals)

    def start_download(self):
        if not self.books:
            messagebox.showwarning(TXT["title"], "Keine Bücher in der Warteliste.")
            return
        self.pb.set(0.0)
        self.pb_label.configure(text="0%")
        self.stop_flag = False
        threading.Thread(target=self.run_thread, daemon=True).start()

    def run_thread(self):
        d = Downloader(self.books, log=self.log, update=self.update, stop_flag=lambda: self.stop_flag)
        d.run()

    def stop_download(self):
        self.stop_flag = True

    def create_pdf(self):
        folder = filedialog.askdirectory(title="Buchordner wählen")
        if not folder:
            return
        images = sorted(
            [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".jpg")]
        )
        if not images:
            messagebox.showwarning(TXT["title"], "Keine Bilder im gewählten Ordner gefunden.")
            return
        title = os.path.basename(folder)
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=f"{title}.pdf",
            filetypes=[("PDF Dateien", "*.pdf")],
        )
        if not save_path:
            return
        self.log(f"[*] Erstelle PDF: {save_path}")
        try:
            im1 = Image.open(images[0]).convert("RGB")
            im_list = [Image.open(p).convert("RGB") for p in images[1:]]
            im1.save(save_path, save_all=True, append_images=im_list)
            self.log(f"[+] PDF erstellt: {save_path}")
            messagebox.showinfo(TXT["title"], f"✅ PDF erfolgreich erstellt:\n{save_path}")
        except Exception as e:
            self.log(f"[!] Fehler beim PDF-Erstellen: {e}")
            messagebox.showerror(TXT["title"], f"Fehler beim PDF-Erstellen:\n{e}")


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

if __name__ == "__main__":
    app = ctk.CTk()
    gui = DownloaderGUI(app)
    app.mainloop()
