from __future__ import annotations


def light_stylesheet() -> str:
    return """
    QMainWindow, QWidget {
        background: #f5f7fb;
        color: #1f2937;
    }
    QGroupBox {
        background: #ffffff;
        border: 1px solid #dbe2ea;
        border-radius: 14px;
        margin-top: 8px;
        font-weight: 600;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }
    QLabel {
        color: #334155;
        background: transparent;
    }
    QLabel#hintLabel {
        color: #64748b;
        font-style: italic;
    }
    QLineEdit, QTextEdit, QTableWidget {
        background: #ffffff;
        color: #1f2937;
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        padding: 8px;
    }
    QTableWidget {
        gridline-color: #e2e8f0;
        alternate-background-color: #f8fafc;
    }
    QHeaderView::section {
        background: #eef2f7;
        color: #334155;
        border: none;
        border-bottom: 1px solid #dbe2ea;
        padding: 10px;
        font-weight: 600;
    }
    QPushButton {
        background: #e9eef6;
        color: #1f2937;
        border: 1px solid #d4dce7;
        border-radius: 12px;
        padding: 10px 14px;
        font-weight: 600;
        text-align: center;
    }
    QPushButton:hover { background: #dde6f3; }
    QPushButton:pressed { background: #d5dfef; }
    QPushButton:disabled {
        color: #94a3b8;
        background: #eef2f7;
    }
    QPushButton#addBookButton {
        background: #facc15;
        color: #1f2937;
        border: 1px solid #eab308;
    }
    QPushButton#addBookButton:hover { background: #eab308; }
    QPushButton#addBookButton:pressed {
        background: #ca8a04;
        color: white;
    }
    QPushButton#deleteBookButton {
        background: #f97316;
        color: white;
        border: 1px solid #ea580c;
    }
    QPushButton#deleteBookButton:hover { background: #ea580c; }
    QPushButton#deleteBookButton:pressed { background: #c2410c; }
    QPushButton#changePagesButton {
        background: #a855f7;
        color: white;
        border: 1px solid #9333ea;
    }
    QPushButton#changePagesButton:hover { background: #9333ea; }
    QPushButton#changePagesButton:pressed { background: #7e22ce; }
    QPushButton#downloadButton {
        background: #22c55e;
        color: white;
        border: 1px solid #16a34a;
    }
    QPushButton#downloadButton:hover { background: #16a34a; }
    QPushButton#downloadButton:pressed { background: #15803d; }
    QPushButton#downloadButton:disabled {
        background: #86efac;
        color: white;
        border: 1px solid #4ade80;
    }
    QPushButton#stopButton {
        background: #ef4444;
        color: white;
        border: 1px solid #dc2626;
    }
    QPushButton#stopButton:hover { background: #dc2626; }
    QPushButton#stopButton:pressed { background: #b91c1c; }
    QPushButton#stopButton:disabled {
        background: #fca5a5;
        color: white;
        border: 1px solid #f87171;
    }
    QPushButton#resetButton {
        background: #0ea5e9;
        color: white;
        border: 1px solid #0284c7;
    }
    QPushButton#resetButton:hover { background: #0284c7; }
    QPushButton#resetButton:pressed { background: #0369a1; }
    QProgressBar {
        background: #e2e8f0;
        border: 1px solid #cbd5e1;
        border-radius: 9px;
        text-align: center;
        min-height: 22px;
    }
    QProgressBar::chunk {
        background: #3b82f6;
        border-radius: 8px;
    }
    QStatusBar {
        background: #e9eef6;
        color: #334155;
        border-top: 1px solid #dbe2ea;
    }
    QRadioButton { padding: 2px 6px; }
    """


def dark_stylesheet() -> str:
    return """
    QMainWindow, QWidget {
        background: #121826;
        color: #e5e7eb;
    }
    QGroupBox {
        background: #1b2435;
        border: 1px solid #2d3748;
        border-radius: 14px;
        margin-top: 8px;
        font-weight: 600;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: #cbd5e1;
    }
    QLabel {
        color: #e5e7eb;
        background: transparent;
    }
    QLabel#hintLabel {
        color: #94a3b8;
        font-style: italic;
    }
    QLineEdit, QTextEdit, QTableWidget {
        background: #0f172a;
        color: #e5e7eb;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 8px;
    }
    QTableWidget {
        gridline-color: #1e293b;
        alternate-background-color: #111b2d;
    }
    QHeaderView::section {
        background: #1e293b;
        color: #e2e8f0;
        border: none;
        border-bottom: 1px solid #334155;
        padding: 10px;
        font-weight: 600;
    }
    QPushButton {
        background: #243045;
        color: #e5e7eb;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 10px 14px;
        font-weight: 600;
        text-align: center;
    }
    QPushButton:hover { background: #334155; }
    QPushButton:pressed { background: #3f4d63; }
    QPushButton:disabled {
        color: #94a3b8;
        background: #1e293b;
    }
    QPushButton#addBookButton { background: #f59e0b; color: #111827; border: 1px solid #d97706; }
    QPushButton#addBookButton:hover { background: #d97706; color: white; }
    QPushButton#deleteBookButton { background: #f97316; color: white; border: 1px solid #ea580c; }
    QPushButton#deleteBookButton:hover { background: #ea580c; }
    QPushButton#changePagesButton { background: #a855f7; color: white; border: 1px solid #9333ea; }
    QPushButton#changePagesButton:hover { background: #9333ea; }
    QPushButton#downloadButton { background: #22c55e; color: white; border: 1px solid #16a34a; }
    QPushButton#downloadButton:hover { background: #16a34a; }
    QPushButton#stopButton { background: #ef4444; color: white; border: 1px solid #dc2626; }
    QPushButton#stopButton:hover { background: #dc2626; }
    QPushButton#resetButton { background: #0ea5e9; color: white; border: 1px solid #0284c7; }
    QPushButton#resetButton:hover { background: #0284c7; }
    QProgressBar {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 9px;
        text-align: center;
        min-height: 22px;
        color: #e5e7eb;
    }
    QProgressBar::chunk {
        background: #60a5fa;
        border-radius: 8px;
    }
    QStatusBar {
        background: #1e293b;
        color: #cbd5e1;
        border-top: 1px solid #334155;
    }
    QRadioButton { padding: 2px 6px; }
    """
