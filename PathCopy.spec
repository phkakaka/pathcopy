# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for PathCopy —— 单文件 windowed exe
from pathlib import Path

project_root = Path(SPECPATH).resolve()

a = Analysis(
    ["pathcopy.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PathCopy",
    icon=None,                 # 暂无图标；如需可放 assets/pathcopy.ico 后改为 str(project_root/"assets"/"pathcopy.ico")
    version=str(project_root / "version_info.txt"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                  # 若本机装了 UPX 则压缩，没装也无所谓
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,             # 窗口程序，无控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
