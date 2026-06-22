# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for PathCopy —— 单文件 windowed exe
from pathlib import Path

project_root = Path(SPECPATH).resolve()
icon_file = str(project_root / "assets" / "pathcopy.ico")
assets_dir = str(project_root / "assets")

a = Analysis(
    ["pathcopy.py"],
    pathex=[str(project_root)],
    binaries=[],
    # 把 assets 目录打入 exe，运行时由 sys._MEIPASS 解出；
    # 目标路径 "assets" 与 pathcopy.py 中 _resource_path("assets/pathcopy.ico") 对应。
    datas=[(assets_dir, "assets")],
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
    icon=icon_file,            # 嵌入 exe 资源（资源管理器/任务栏显示此图标）
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
