# MatriculaDownloader


Downloader für Matricula Online 🇩🇪 🇦🇹 🇵🇱 🇷🇸 🇱🇺 🇧🇦 🇸🇮 🇮🇹 

# Folgende Webseiten werden seit dem Update 1.3 unterstützt:

-> matricula-online.eu

-> dfg-viewer.de

-> findbuch.net

-> archiviodiocesanoreggiobova.it


![alt text](https://github.com/Testatost/Matricula-Downloader/blob/main/Matricula%20Downloader.png?raw=true)

# 🇩🇪 Deutsch

## 🔑 Hauptaufgabe

•	Du kannst URLs von Kirchenbüchern, Archivalien oder Dokumenten von **matricula-online.eu** oder **findbuch.net** eingeben.
•	Das Programm durchsucht die Seite automatisch nach den eingebetteten Bildlinks (z. B. Base64-kodierte oder JavaScript-Links).
•	Daraus erzeugt es **direkte Download-Links zu hochauflösenden JPEG-Seiten**.
•	Die Scans werden als Einzelseiten (z. B. *Taufbuch_Musterstadt_001.jpg, Taufbuch_Musterstadt_002.jpg, …*) in einen Zielordner heruntergeladen.
•	Mehrere Bücher können in eine **Warteliste** aufgenommen und nacheinander heruntergeladen werden.

---

## 🛠️ Funktionen

### 1.	📚 Buchverwaltung

•	URL, Zielordner und gewünschte Seiten angeben.
•	Seitenbereiche im Format `1,3,5-10` möglich (leer = alle Seiten).
•	Mehrere Bücher können hinzugefügt, gelöscht oder geändert werden.
•	Wartelisten lassen sich als **JSON** oder **Textdatei** exportieren und wieder importieren.

### 2.	⬇️ Download

•	Bilder werden automatisch seitenweise heruntergeladen.
•	Status je Buch (`✅`, `⚠️`, `❌`) wird in der Tabelle angezeigt.
•	Gesamtfortschritt wird über eine Fortschrittsleiste angezeigt.
•	Abbruch (Stop-Button) jederzeit möglich.
•	Nach einem Neustart kann mit importierter Liste weitergemacht werden.

### 3.	📄 PDF-Erstellung

•	Heruntergeladene Seiten können zu einem **einzigen PDF-Dokument** zusammengefügt werden.
•	Dateiname = Buchname (z. B. *Taufbuch_Musterstadt.pdf*).
•	PDF-Erstellung erfolgt direkt über die Benutzeroberfläche.

### 4.	🧾 Logging

•	Alle Aktionen (z. B. „Buch hinzugefügt“, „Download gestartet“, „Seite gespeichert“) erscheinen im Logfenster.
•	Logs werden mit Uhrzeit angezeigt und automatisch bis zum Ende gescrollt.
•	Log enthält Unicode und unterstützt Umlaute vollständig (ä, ö, ü, ß).

### 5.	🖥️ Benutzeroberfläche (Tkinter)

•	Intuitive GUI mit **Tabellenansicht** der Warteliste.
•	Spalten: Buch / ID – Seiten – Status.
•	Buttons für *Download starten*, *Stoppen*, *Zurücksetzen* und *Als PDF speichern*.
•	Home-Button zur direkten Öffnung der Matricula-Startseite.
•	Fortschrittsanzeige in Prozent sowie globaler Balken.

### 6.	💾 Unicode & Kompatibilität

•	Vollständig kompatibel mit **Linux Mint**, **Windows** und **macOS**.
•	Datei- und Ordnernamen werden automatisch **Unicode-normalisiert (NFC)**.
•	Alle Umlaute funktionieren korrekt in Pfaden, Dateinamen und Logs.
•	Für die Anzeige wird die Schriftart **DejaVu Sans** verwendet.

---

## 🧩 Installation & Nutzung

1️⃣ **Python 3 installieren** (unter Linux meist schon vorhanden).
2️⃣ Erforderliche Pakete installieren (einmalig):

```bash
pip install requests beautifulsoup4 pillow
```

3️⃣ Den Code als Datei speichern (z. B. `matricula_downloader.py`).
4️⃣ Starten über:

```bash
python3 matricula_downloader.py
```

5️⃣ Im Programm:

* URL von Matricula oder Findbuch eingeben,
* Zielordner wählen,
* Seiten optional angeben,
* *➕ Hinzufügen*, dann *⬇️ Herunterladen*.

---

## 🧠 Hinweise

•	Das Programm lädt nur öffentlich verfügbare Scans (keine geschützten Inhalte).
•	Der Download erfolgt direkt von den Servern der jeweiligen Archive.
•	Die Nutzung unterliegt den **Nutzungsbedingungen von Matricula** bzw. **Findbuch.net**.
•	Bei Archiven mit vielen Seiten kann der Vorgang mehrere Minuten dauern.

---

## 🧰 Update 1.2

* Vollständige **Umlautunterstützung** (Linux Mint getestet).
* **Unicode-normalisierte Pfade (NFC)** für alle Ordner und Dateien.
* Verbesserte Fehlerbehandlung beim Download.
* **Home-Button** zur Matricula-Startseite hinzugefügt.
* GUI überarbeitet und auf **DejaVu Sans**-Fonts umgestellt.
* Wartelistenexport jetzt auch im UTF-8-Textformat.

## 🧰 Update 1.3

* Download-Möglichkeit hinzugefügt:

  -> dfg-viewer.de
  
  -> archiviodiocesanoreggiobova.it

---

## ⚠️ Haftungsausschluss

Dieses Programm dient ausschließlich zu Forschungs- und Archivzwecken.
Die bereitgestellten Funktionen greifen nur auf **öffentlich zugängliche** Inhalte zu.
Es besteht **keine Verbindung** zu den Betreibern von Matricula Online oder Findbuch.net.

---

**Bearbeitet mit ChatGPT 5.1 **

