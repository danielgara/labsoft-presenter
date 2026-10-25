# -*- mode: python ; coding: utf-8 -*-
"""Package Presenter as Presenter.app on macOS, Presenter.exe on Windows, and dist/Presenter on Linux."""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

root = Path(SPECPATH)
icon = None
if sys.platform == "darwin":
    candidate = root / "packaging" / "Presenter.icns"
    if candidate.exists():
        icon = str(candidate)
elif sys.platform == "win32":
    candidate = root / "packaging" / "Presenter.ico"
    if candidate.exists():
        icon = str(candidate)

hidden = collect_submodules("presenter")
datas: list = []
binaries: list = []
if sys.platform == "darwin":
    hidden += [
        "pynput.keyboard._darwin",
        "pynput.mouse._darwin",
        "Quartz",
        "AppKit",
        "ApplicationServices",
        "HIServices",
        "CoreText",
        "objc",
    ]
    for package in ("ApplicationServices", "HIServices", "CoreText"):
        package_datas, package_binaries, package_hidden = collect_all(package)
        datas += package_datas
        binaries += package_binaries
        hidden += package_hidden
elif sys.platform == "win32":
    hidden += [
        "pynput.keyboard._win32",
        "pynput.mouse._win32",
    ]
else:
    # pynput picks its backend at import time, which fails without a display.
    hidden += [
        "pynput.keyboard._xorg",
        "pynput.mouse._xorg",
    ]
    hidden += collect_submodules("Xlib")

a = Analysis(
    [str(root / "packaging" / "entry.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

onefile = sys.platform != "darwin"
exe = EXE(
    pyz,
    a.scripts,
    a.binaries if onefile else [],
    a.datas if onefile else [],
    exclude_binaries=not onefile,
    name="Presenter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

if not onefile:
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name="Presenter",
    )
    if sys.platform == "darwin":
        app = BUNDLE(
            coll,
            name="Presenter.app",
            icon=icon,
            bundle_identifier="com.labsoft.presenter",
            info_plist={
                "CFBundleName": "Presenter",
                "CFBundleDisplayName": "Presenter",
                "CFBundleShortVersionString": "1.0.0",
                "CFBundleVersion": "1.0.0",
                "NSHighResolutionCapable": True,
                "NSScreenCaptureUsageDescription": "Presenter captura la pantalla para ampliar lo que estás presentando.",
                "NSAccessibilityUsageDescription": "Presenter usa Accesibilidad para los atajos y para enmarcar mientras presentas.",
            },
        )
