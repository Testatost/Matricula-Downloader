from __future__ import annotations

from PySide6.QtGui import QFont

APP_DISPLAY_NAME = "Matricula Downloader"
APP_TITLE = f" {APP_DISPLAY_NAME}"
APP_HOME_LABEL = "🏠 Matricula"
SETTINGS_ORG = "MatriculaDownloader"
SETTINGS_APP = "MatriculaDownloader"
APP_FONT = QFont("Segoe UI", 10)

APP_VERSION = "2.1"
APP_AUTHOR = "Sebastian (Testatost)"
APP_ID = "Sebastian.Testatost.MatriculaDownloader.2.1"

REQ_TIMEOUT = 25
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0",
    "Referer": "https://data.matricula-online.eu/",
}
SUPPORTED_DOMAINS = [
    "matricula-online.eu",
    "dfg-viewer.de",
    "findbuch.net",
    "archiviodiocesanoreggiobova.it",
    "netx.bistum-essen.de",
]
