# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 — 机标结构化修改器

用法：
    pip install pyinstaller
    pyinstaller build.spec

输出：
    macOS: dist/机标结构化修改器.app
    Windows: dist/机标结构化修改器.exe
"""

import sys
import platform
from pathlib import Path

BLOCK_CIPHER_KEY = None

system = platform.system()
is_darwin = system == "Darwin"
is_win = system == "Windows"

# 应用名称
app_name = "机标结构化修改器"

# 图标（如果存在则使用）
icon_path = None
for ext in (".icns", ".ico", ".png"):
    p = Path(__file__).parent / f"assets/app_icon{ext}"
    if p.exists():
        icon_path = str(p)
        break

# 数据文件：docs 目录
datas = [
    ("docs", "docs"),
]

# 排除不需要的库
excludes = [
    "PyQt5", "PyQt6", "PySide2", "PySide6",
    "matplotlib", "numpy", "pandas",
    "Crypto", "cryptography",
    "PIL", "Pillow",
    "scipy", "sklearn",
    "tensorflow", "torch",
    "notebook", "jupyter",
    "bokeh", "plotly",
    "django", "flask",
    "sphinx",
]

if is_darwin:
    # macOS: 打包为 .app 并设置 Info.plist
    bundle_identifier = "com.mtycloud.caption-editor"
    info_plist = {
        "CFBundleName": app_name,
        "CFBundleDisplayName": app_name,
        "CFBundleIdentifier": bundle_identifier,
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleExecutable": app_name,
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
    }

    a = Analysis(
        ["main.py"],
        pathex=[],
        binaries=[],
        datas=datas,
        hiddenimports=["tkinter", "tkinter.filedialog", "tkinter.messagebox"],
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=excludes,
        noarchive=False,
    )
    pyz = PYZ(a.pure)

    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=app_name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
    )

    app = BUNDLE(
        exe,
        name=f"{app_name}.app",
        icon=icon_path,
        bundle_identifier=bundle_identifier,
        info_plist=info_plist,
        version="1.0.0",
    )

elif is_win:
    # Windows: 打包为单文件 .exe
    a = Analysis(
        ["main.py"],
        pathex=[],
        binaries=[],
        datas=datas,
        hiddenimports=["tkinter", "tkinter.filedialog", "tkinter.messagebox"],
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=excludes,
        noarchive=False,
    )
    pyz = PYZ(a.pure)

    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=f"{app_name}",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
    )
else:
    # Linux: 打包为单文件
    a = Analysis(
        ["main.py"],
        pathex=[],
        binaries=[],
        datas=datas,
        hiddenimports=["tkinter", "tkinter.filedialog", "tkinter.messagebox"],
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=excludes,
        noarchive=False,
    )
    pyz = PYZ(a.pure)

    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=app_name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
    )
