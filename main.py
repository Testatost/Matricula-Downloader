from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen, QStyleFactory

from matriculadownloader.app_constants import APP_DISPLAY_NAME
from matriculadownloader.icons import get_app_icon, resource_path, set_windows_app_id
from matriculadownloader.main_window import MainWindow


def create_splash() -> QSplashScreen | None:
    splash_path = resource_path("splash.png")
    pixmap = QPixmap(splash_path)
    if pixmap.isNull():
        return None

    splash = QSplashScreen(pixmap)
    splash.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    splash.setEnabled(False)
    app_icon = get_app_icon()
    if not app_icon.isNull():
        splash.setWindowIcon(app_icon)
    splash.show()
    splash.showMessage("Starting Matricula Downloader…", Qt.AlignBottom | Qt.AlignHCenter, Qt.white)
    QGuiApplication.processEvents()
    return splash


def main() -> int:
    set_windows_app_id()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setStyle(QStyleFactory.create("Fusion"))

    app_icon = get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    splash = create_splash()

    window = MainWindow()
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)
    window.show()

    if splash is not None:
        splash.finish(window)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
