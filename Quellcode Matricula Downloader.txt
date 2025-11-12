# HINWEIS: Dieses GUI verwendet "customtkinter" für ein modernes Look & Feel.
# Installation (einmalig):  pip install customtkinter

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
# FUNKTIONEN
# ------------------------------------------------------------

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def safe_name(s):
    # Erlaubt alle Unicode-Buchstaben (auch äöüß), ersetzt nur Windows-verbote
    s = re.sub(r'[\\/:*?"<>|]+', "_", s.strip())
    return "".join(c if c.isprintable() else "_" for c in s)

def open_homepage():
    """Öffnet die Matricula-Startseite im Standardbrowser."""
    webbrowser.open("https://data.matricula-online.eu/de/bestande/")

def extract_book_title(soup, url):
    """Versucht, den Buchtitel aus Matricula oder Findbuch-Seite zu ermitteln."""
    title = None
    h2 = soup.find("h2")
    if h2 and h2.text.strip():
        title = h2.text.strip()
    elif soup.title and soup.title.text.strip():
        title = soup.title.text.strip()

    if not title and "findbuch.net" in url:
        h1 = soup.find("h1")
        if h1 and h1.text.strip():
            title = h1.text.strip()
        else:
            td = soup.find("td", class_="text2")
            if td and td.text.strip():
                title = td.text.strip()

    if not title:
        title = url.split("/")[-2] if "/" in url else "Unbekanntes_Buch"

    # --- hier neu: Stelle sicher, dass der Titel wirklich UTF-8 ist ---
    try:
        title = title.encode("latin1").decode("utf-8")
    except Exception:
        pass

    return safe_name(title)


def extract_image_urls(book_url: str):
    """Extrahiert Bild-URLs aus Matricula oder Findbuch-Seiten. → (image_urls, buch_titel)"""
    try:
        r = requests.get(book_url, headers=HEADERS, timeout=REQ_TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        html_text = r.text

        image_urls = []
        book_title = extract_book_title(soup, book_url)

        # Matricula
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
                encoded_files = re.findall(r'"(/image/[^"]+)"', raw_list)
                for ef in encoded_files:
                    b64 = ef.split("/image/")[-1].strip("/")
                    try:
                        missing_padding = len(b64) % 4
                        if missing_padding:
                            b64 += '=' * (4 - missing_padding)
                        decoded = base64.b64decode(b64).decode("utf-8")
                        if decoded.startswith("http"):
                            image_urls.append(decoded)
                        else:
                            image_urls.append(f"https://img.data.matricula-online.eu{decoded}")
                    except Exception as e:
                        print(f"[!] Fehler beim Dekodieren: {e}")
                        continue
                if image_urls:
                    break

        # Findbuch
        elif "findbuch.net" in book_url:
            possible_imgs = re.findall(r'\/a_pics\/ks\/[^"\']+\.jpg', html_text)
            for img_path in possible_imgs:
                full_url = f"https://www.findbuch.net{img_path}"
                if full_url not in image_urls:
                    image_urls.append(full_url)

            if not image_urls:
                onclick_links = re.findall(r'javascript:m_click\(\d+\)', html_text)
                if onclick_links:
                    base_guess = re.search(r'(/a_pics/ks/[^\s"]+_)\d{3}\.jpg', html_text)
                    if base_guess:
                        base_url = f"https://www.findbuch.net{base_guess.group(1)}"
                        indices = [int(x.split("(")[1].split(")")[0]) for x in onclick_links]
                        for i in indices:
                            img_num = f"{i+3:03d}"
                            image_urls.append(f"{base_url}{img_num}.jpg")

        return sorted(set(image_urls)), book_title

    except Exception as e:
        print(f"[!] Fehler beim Abrufen der Seite: {e}")
        return [], "Unbekanntes_Buch"

def parse_pages(pages_str, total):
    """Gibt eine Liste von Seitenindizes zurück."""
    if not pages_str.strip():
        return list(range(1, total + 1))
    result = []
    for part in pages_str.split(","):
        if "-" in part:
            try:
                a, b = map(int, part.split("-"))
                result.extend(range(a, b + 1))
            except:
                pass
        else:
            try:
                result.append(int(part))
            except:
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
        done = 0
        for idx, b in enumerate(self.books):
            if self.stop_flag():
                self.log("[*] Abgebrochen.")
                break
            url = b["url"]
            outdir = b["outdir"]
            pages_str = b["pages"]

            self.log(f"[+] Lade Buch: {url}")
            image_urls, book_title = extract_image_urls(url)
            if not image_urls:
                self.log(f"[!] Keine Seiten gefunden: {url}")
                self.update(idx, "⚠️")
                continue

            ensure_dir(outdir)
            folder = os.path.join(outdir, book_title)
            ensure_dir(folder)

            pages = parse_pages(pages_str, len(image_urls))
            self.log(f"   → {len(pages)} Seiten ausgewählt ({book_title}).")

            errors = 0
            for i in pages:
                if self.stop_flag():
                    errors += 1
                    break
                img_url = image_urls[i - 1]
                fn = os.path.join(folder, f"{book_title}_{i:03d}.jpg")
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
            self.update(idx, "✅" if errors == 0 else "⚠️")
            done += 1
            self.update("global", done / total * 100)
        self.log("[*] Fertig.")

# ------------------------------------------------------------
# GUI (CustomTkinter)
# ------------------------------------------------------------

class DownloaderGUI:
    def __init__(self, master):
        self.master = master
        self.books = []
        self.stop_flag = False

        # Modernes Aussehen
        ctk.set_appearance_mode("system")  # "light", "dark" oder "system"
        ctk.set_default_color_theme("blue")  # "blue", "dark-blue", "green"

        master.title(TXT["title"])
        master.geometry("1000x900")

        # --- Topbar (Home-Button ganz links) ---
        self.topbar = ctk.CTkFrame(master, corner_radius=0, fg_color=("white", "#1e1f22"))
        self.topbar.pack(fill="x")

        self.btn_home = ctk.CTkButton(self.topbar, text=TXT["open_home"], command=open_homepage, width=120)
        self.btn_home.pack(side="left", padx=12, pady=10)

        # --- Hauptbereich (Eingaben + rechte Buttonspalte) ---
        self.main = ctk.CTkFrame(master, corner_radius=12, fg_color=("white", "#1e1f22"))
        self.main.pack(fill="x", padx=12, pady=(12, 6))

        # Linke Eingabespalte
        self.grid_left = ctk.CTkFrame(self.main, fg_color="transparent")
        self.grid_left.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.main.grid_columnconfigure(0, weight=1)

        # Rechte Buttons
        self.grid_right = ctk.CTkFrame(self.main, fg_color="transparent")
        self.grid_right.grid(row=0, column=1, sticky="ne", padx=12, pady=12)

        # Buch-URL
        self.lbl_url = ctk.CTkLabel(self.grid_left, text=TXT["book_url"], font=ctk.CTkFont(*FONT_DEFAULT))
        self.lbl_url.grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.url = ctk.CTkEntry(self.grid_left, width=700, font=ctk.CTkFont(*FONT_DEFAULT))
        self.url.grid(row=0, column=1, sticky="we", padx=(10, 0), pady=(0, 6))
        self.grid_left.grid_columnconfigure(1, weight=1)

        # Zielordner
        self.lbl_out = ctk.CTkLabel(self.grid_left, text=TXT["target_dir"], font=ctk.CTkFont(*FONT_DEFAULT))
        self.lbl_out.grid(row=1, column=0, sticky="w", pady=(0, 6))
        self.outdir = ctk.CTkEntry(self.grid_left, width=700, font=ctk.CTkFont(*FONT_DEFAULT))
        self.outdir.grid(row=1, column=1, sticky="we", padx=(10, 0), pady=(0, 6))

        self.btn_choose = ctk.CTkButton(self.grid_left, text=TXT["choose_dir"], command=self.choose_dir, width=180, fg_color="#6c757d", hover_color="#5b646b")
        self.btn_choose.grid(row=1, column=2, padx=(10, 0), pady=(0, 6))

        # Seiten
        self.lbl_pages = ctk.CTkLabel(self.grid_left, text=TXT["pages"], font=ctk.CTkFont(*FONT_DEFAULT))
        self.lbl_pages.grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.pages = ctk.CTkEntry(self.grid_left, width=300, font=ctk.CTkFont(*FONT_DEFAULT))
        self.pages.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(0, 2))
        self.lbl_hint = ctk.CTkLabel(
            self.grid_left,
            text=TXT["pages_hint"],
            font=ctk.CTkFont(family="Calibri", size=10, slant="italic"),
            text_color=("gray30", "gray70")
        )

        self.lbl_hint.grid(row=3, column=1, sticky="w", padx=(10, 0), pady=(0, 6))

        # Rechte Buttons (gleich wie original, nur moderner)
        self.btn_add = ctk.CTkButton(self.grid_right, text=TXT["add_book"], command=self.add_book, width=200, fg_color="#007bff", hover_color="#0a68d1")
        self.btn_add.pack(pady=4)
        self.btn_del = ctk.CTkButton(self.grid_right, text=TXT["delete_book"], command=self.delete_book, width=200, fg_color="#dc3545", hover_color="#b52a38")
        self.btn_del.pack(pady=4)
        self.btn_imp = ctk.CTkButton(self.grid_right, text=TXT["import_list"], command=self.import_list, width=200, fg_color="#ffc107", text_color="black", hover_color="#e0ad06")
        self.btn_imp.pack(pady=4)
        self.btn_exp = ctk.CTkButton(self.grid_right, text=TXT["export_list"], command=self.export_list, width=200, fg_color="#17a2b8", hover_color="#148fa0")
        self.btn_exp.pack(pady=4)

        # --- Download Buttonzeile ---
        self.downbar = ctk.CTkFrame(master, corner_radius=12, fg_color=("white", "#1e1f22"))
        self.downbar.pack(fill="x", padx=12, pady=(6, 6))

        self.btn_download = ctk.CTkButton(self.downbar, text=TXT["download"], command=self.start_download, width=200, fg_color="#28a745", hover_color="#218838")
        self.btn_download.pack(side="left", padx=6, pady=10)
        self.btn_stop = ctk.CTkButton(self.downbar, text=TXT["stop"], command=self.stop_download, width=200, fg_color="#dc3545", hover_color="#b52a38")
        self.btn_stop.pack(side="left", padx=6, pady=10)
        self.btn_reset = ctk.CTkButton(self.downbar, text=TXT["reset"], command=self.reset_books, width=200, fg_color="#007bff", hover_color="#0a68d1")
        self.btn_reset.pack(side="left", padx=6, pady=10)
        self.btn_pdf = ctk.CTkButton(self.downbar, text=TXT["pdf"], command=self.create_pdf, width=200, fg_color="#6f42c1", hover_color="#5d37a3")
        self.btn_pdf.pack(side="left", padx=6, pady=10)

        # --- Warteliste ---
        self.section_wait = ctk.CTkFrame(master, corner_radius=12, fg_color=("white", "#1e1f22"))
        self.section_wait.pack(fill="both", expand=False, padx=12, pady=(6, 6))
        self.lbl_wait = ctk.CTkLabel(self.section_wait, text=TXT["waiting_list"], font=ctk.CTkFont(*FONT_DEFAULT))
        self.lbl_wait.pack(anchor="w", padx=10, pady=(10, 0))

        # Container für Treeview (ttk in CTk-Frame)
        self.tree_container = ctk.CTkFrame(self.section_wait, fg_color=("white", "#1e1f22"))
        self.tree_container.pack(fill="both", expand=True, padx=10, pady=10)

        # ttk Styling für Treeview (modern & kompakt)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Treeview", rowheight=28, font=("Calibri", 11), background="#ffffff", fieldbackground="#ffffff", foreground="#222222")
        style.configure("Treeview.Heading", font=("Calibri", 12, "bold"))
        style.map("Treeview", background=[("selected", "#cce5ff")], foreground=[("selected", "#000000")])

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

        # --- Fortschritt ---
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

        # --- Log ---
        self.section_log = ctk.CTkFrame(master, corner_radius=12, fg_color=("white", "#1e1f22"))
        self.section_log.pack(fill="both", expand=True, padx=12, pady=(6, 12))
        self.log_text = ctk.CTkTextbox(self.section_log, height=180, font=ctk.CTkFont("Consolas", 11))
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)

    # ------------------------------------------------------------
    # GUI-Methoden
    # ------------------------------------------------------------

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
        if not any(x in u for x in ["matricula-online.eu", "findbuch.net"]):
            messagebox.showwarning(TXT["title"], "Nur matricula-online.eu oder findbuch.net werden unterstützt.")
            return
        self.books.append({"url": u, "outdir": self.outdir.get().strip() or os.getcwd(), "pages": self.pages.get().strip()})
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

    # ------------------------------------------------------------
    # IMPORT / EXPORT
    # ------------------------------------------------------------

    def export_list(self):
        if not self.books:
            messagebox.showinfo(TXT["title"], "Keine Einträge zum Exportieren.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON Dateien", "*.json"), ("Textdateien", "*.txt")],
                                            title="Warteliste exportieren")
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
        path = filedialog.askopenfilename(filetypes=[("Unterstützte Dateien", "*.json *.txt")],
                                          title="Warteliste importieren")
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
                            imported.append({
                                "url": parts[0],
                                "outdir": parts[1],
                                "pages": parts[2] if len(parts) > 2 else ""
                            })
            for b in imported:
                self.books.append(b)
                self.tree.insert("", "end", values=(b["url"], b["pages"], "⏳"))
            self.log(f"[+] {len(imported)} Bücher importiert.")
        except Exception as e:
            messagebox.showerror(TXT["title"], f"Fehler beim Importieren:\n{e}")

    # ------------------------------------------------------------
    # DOWNLOAD UND LOG
    # ------------------------------------------------------------

    def log(self, msg):
        line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")

    def update(self, idx, val):
        if idx == "global":
            # CTkProgressBar erwartet 0.0–1.0
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
        images = sorted([os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".jpg")])
        if not images:
            messagebox.showwarning(TXT["title"], "Keine Bilder im gewählten Ordner gefunden.")
            return
        title = os.path.basename(folder)
        save_path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"{title}.pdf",
                                                filetypes=[("PDF Dateien", "*.pdf")])
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
