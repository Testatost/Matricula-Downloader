# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("matriculadownloader")

datas = []
for candidate in (
    "icon.ico",
    "icon.png",
    "logo.png",
    "banner.png",
    "splash.png",
):
    try:
        with open(candidate, "rb"):
            datas.append((candidate, "."))
    except FileNotFoundError:
        pass

from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo,
    FixedFileInfo,
    StringFileInfo,
    StringTable,
    StringStruct,
    VarFileInfo,
    VarStruct,
)

version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(1, 5, 0, 0),
        prodvers=(1, 5, 0, 0),
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("CompanyName", "Sebastian (Testatost)"),
                        StringStruct("FileDescription", "Matricula Downloader"),
                        StringStruct("FileVersion", "1.5.0"),
                        StringStruct("InternalName", "Matricula Downloader"),
                        StringStruct("OriginalFilename", "Matricula Downloader.exe"),
                        StringStruct("ProductName", "Matricula Downloader"),
                        StringStruct("ProductVersion", "1.5.0"),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe_kwargs = dict(
    name="Matricula Downloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=version_info,
)

try:
    with open("icon.ico", "rb"):
        exe_kwargs["icon"] = "icon.ico"
except FileNotFoundError:
    pass

try:
    with open("splash.png", "rb"):
        exe_kwargs["splash"] = "splash.png"
except FileNotFoundError:
    pass

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    **exe_kwargs,
)