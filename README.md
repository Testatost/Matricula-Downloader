# Matricula Downloader

<p align="center">
  <img src="logo.png" alt="Matricula Downloader Logo" width="260"> <br>
</p>

Matricula Downloader is a desktop application for downloading scans from **matricula-online.eu** and related supported sources.

The current source code is based on a modular package in `matriculadownloader/` and is now aligned with the updated desktop-style structure used in the newer downloader projects.

![Screenshot](splash.png)

## Overview

The application can:

- open URLs from `matricula-online.eu`
- support additional sources such as `dfg-viewer.de`, `findbuch.net`, `archiviodiocesanoreggiobova.it`, and NetX-based archive portals
- detect scan/image sources on the page
- generate direct JPEG download links
- download all pages or selected page ranges
- queue multiple entries in a waiting list
- save and load waiting lists as JSON
- export downloaded JPG folders to PDF
- show a live log and save the log manually to a text file
- switch between multiple interface languages
- remember the selected language and theme

## Requirements

- Python 3.10+
- PySide6
- requests
- beautifulsoup4
- Pillow
- selenium
- webdriver-manager
- pyinstaller

## Installation

### Windows / PyCharm / virtual environment

```bash
python -m pip install --upgrade pip
pip install PySide6 requests beautifulsoup4 Pillow selenium webdriver-manager pyinstaller
```

### Linux Mint / Ubuntu

```bash
sudo apt update
sudo apt install python3-pip
python3 -m pip install --upgrade pip
pip install PySide6 requests beautifulsoup4 Pillow selenium webdriver-manager pyinstaller
```

## Usage

1. Start the program.
2. Enter a supported archive URL.
3. Choose the target directory.
4. Optionally enter page ranges such as `1,5,8-10`.
5. Add one or more entries to the waiting list.
6. Start the download.

## Main features

### Download queue

- multiple books, registers, or archive items can be added to a waiting list
- entries can be deleted again
- page ranges can be changed later
- double-click on a row opens the original URL in the browser

### Download logic

- the application searches the page for image, preview, or document-related sources
- direct JPEG download URLs are generated automatically whenever possible
- pages are downloaded one by one
- the overall progress is shown in a progress bar
- each queue item gets a status symbol: `⏳`, `✅`, `⚠️`, `❌`

### Supported sources

The current code is intended to work with:

- `matricula-online.eu`
- `dfg-viewer.de`
- `findbuch.net`
- `archiviodiocesanoreggiobova.it`
- `netx.bistum-essen.de`

### Folder naming

The current code creates folders based on extracted metadata and groups downloads into a readable structure.

```text
Target folder/
└── Place/
    └── Title or Record Type (Years)/
        ├── Title or Record Type_001.jpg
        ├── Title or Record Type_002.jpg
        └── Title or Record Type (Years).pdf
```

For some sources, the exact folder structure depends on the metadata that can be extracted from the page.

### PDF export

Downloaded JPG files can be converted into a PDF per folder.

### Logging

- messages are shown in the log window inside the application
- the log can be shown or hidden
- the log can be saved manually to a chosen `.txt` file

### Interface

- multi-language interface
- selected language is stored with `QSettings`
- dark mode / light mode is available
- selected theme is stored with `QSettings`
- splash screen and application icon can be bundled for packaged builds

## Source code structure

The source code is split into modules inside `matriculadownloader/`.

### Module summary

- `main.py` – application entry point
- `app_constants.py` – application name, settings keys, supported domains, headers
- `i18n.py` – UI texts and language labels
- `icons.py` – application icon handling and Windows AppUserModelID setup
- `main_window.py` – full GUI and user interactions
- `metadata_parser.py` – metadata extraction helpers
- `models.py` – data models such as `BookEntry`
- `network.py` – HTTP loading, NetX handling, and download helpers
- `pdf_utils.py` – PDF export from JPG folders
- `styles.py` – light and dark Qt stylesheets
- `text_utils.py` – helper functions for folders, filenames, and page ranges
- `worker.py` – threaded downloader logic

## Notes

- Page ranges can be entered in formats such as `1,2,5-9`.
- Waiting lists are stored as `.json`.
- Some supported sources require Selenium/browser-assisted loading because the page content is generated dynamically.
- For packaged Windows builds, `icon.ico`, `logo.png`, and `splash.png` can be included through the PyInstaller spec file.

## Disclaimer

This project was created with support from ChatGPT 5.
