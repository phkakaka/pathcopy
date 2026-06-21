"""PathCopy —— 快速收集文件/文件夹路径，按格式拼好一键复制。

技术栈：Python + PySide6 (Qt6)。
单文件应用，配置持久化到 %AppData%/PathCopy/settings.json。
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# ───────────────────── 常量 ─────────────────────

APP_NAME = "PathCopy"
APP_VERSION = "1.0.0"

CONFIG_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
CONFIG_PATH = CONFIG_DIR / "settings.json"

MAX_SLOTS = 5
MIN_SLOTS = 1
MAX_HISTORY = 10

# 内置固定槽位名：首次配置或旧配置迁移时，名字在此集合中的槽位视为固定。
FIXED_SLOT_NAMES = {"code", "elf", "map"}


def is_fixed_slot(slot: Slot) -> bool:
    """固定槽位不可删除。判定依据是 slot.fixed 标志位（持久化），
    而非名字——这样即使重命名 code，它仍然固定。"""
    return bool(slot.fixed)

# 格式：(显示名, 格式化函数标记)。顺序即下拉顺序。
FORMATS = ["绝对路径", "正斜杠", "@前缀", "加引号", "仅文件名", "仅目录"]
SEPARATORS = ["换行", "空格", "逗号", "空行"]

FMT_ABSOLUTE = 0
FMT_FORWARDSLASH = 1
FMT_ATPREFIX = 2
FMT_QUOTED = 3
FMT_FILENAME = 4
FMT_DIRECTORY = 5

SEP_NEWLINE = 0
SEP_SPACE = 1
SEP_COMMA = 2
SEP_BLANKLINE = 3


# ───────────────────── 配置模型 ─────────────────────

@dataclass
class Slot:
    """一个路径槽位：名称 + 最近使用历史（最近在前，最多 MAX_HISTORY 条）。

    fixed=True 表示内置固定槽位（默认 code/elf/map），不显示删除按钮、
    防止误删，且即使重命名也保持固定。用户新增的槽位 fixed=False。
    """
    name: str = "slot"
    history: List[str] = field(default_factory=list)
    fixed: bool = False


@dataclass
class Settings:
    slots: List[Slot] = field(default_factory=list)
    path_format: int = FMT_ABSOLUTE
    separator: int = SEP_NEWLINE
    auto_quote_spaces: bool = True
    always_on_top: bool = False
    window_width: int = 660
    window_height: int = 580

    @staticmethod
    def default() -> "Settings":
        return Settings(slots=[Slot("code", fixed=True), Slot("elf", fixed=True), Slot("map", fixed=True)])

    def normalize(self) -> None:
        """保证数据合法：槽位数/历史条数/名称。"""
        if not self.slots:
            self.slots = Settings.default().slots
        if len(self.slots) > MAX_SLOTS:
            self.slots = self.slots[:MAX_SLOTS]
        for s in self.slots:
            if not s.name or not s.name.strip():
                s.name = "slot"
            s.history = s.history[:MAX_HISTORY]


def _slot_from_dict(d: dict) -> Slot:
    """从配置 dict 构造 Slot。兼容旧配置（无 fixed 字段）：
    缺失时按名字推断——名字在 FIXED_SLOT_NAMES 中即视为固定。"""
    name = d.get("name", "slot")
    history = list(d.get("history", []))
    if "fixed" in d:
        fixed = bool(d["fixed"])
    else:
        fixed = name in FIXED_SLOT_NAMES
    return Slot(name=name, history=history, fixed=fixed)


def load_settings() -> Settings:
    try:
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            s = Settings(
                slots=[_slot_from_dict(slot) for slot in data.get("slots", [])],
                path_format=int(data.get("path_format", FMT_ABSOLUTE)),
                separator=int(data.get("separator", SEP_NEWLINE)),
                auto_quote_spaces=bool(data.get("auto_quote_spaces", True)),
                always_on_top=bool(data.get("always_on_top", False)),
                window_width=int(data.get("window_width", 660)),
                window_height=int(data.get("window_height", 580)),
            )
            s.normalize()
            return s
    except Exception:
        pass  # 读取失败回退默认，避免无法启动
    return Settings.default()


def save_settings(s: Settings) -> None:
    try:
        s.normalize()
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "slots": [{"name": sl.name, "history": sl.history, "fixed": sl.fixed} for sl in s.slots],
            "path_format": s.path_format,
            "separator": s.separator,
            "auto_quote_spaces": s.auto_quote_spaces,
            "always_on_top": s.always_on_top,
            "window_width": s.window_width,
            "window_height": s.window_height,
        }
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass  # 写入失败静默处理（如只读环境），不影响主流程


# ───────────────────── 路径格式化 ─────────────────────

def format_path(raw: str, fmt: int, auto_quote: bool) -> str:
    """把原始路径按指定格式处理。失败时回退原值。"""
    p = raw
    try:
        if fmt == FMT_FORWARDSLASH:
            p = p.replace("\\", "/")
        elif fmt == FMT_ATPREFIX:
            p = "@" + p
        elif fmt == FMT_QUOTED:
            p = '"' + p.strip('"') + '"'
        elif fmt == FMT_FILENAME:
            p = os.path.basename(p.rstrip("\\/"))
        elif fmt == FMT_DIRECTORY:
            # 是文件取其目录；是目录则保持并确保尾随分隔符
            d = p
            if os.path.isfile(p):
                d = os.path.dirname(p) or p
            if not (d.endswith("\\") or d.endswith("/")):
                d += "\\"
            p = d
        # FMT_ABSOLUTE：原样
    except Exception:
        pass

    # 含空格自动加引号（仅当格式非 Quoted、非 @前缀、非仅文件名）
    if auto_quote and fmt not in (FMT_QUOTED, FMT_ATPREFIX, FMT_FILENAME):
        if " " in p and not p.startswith('"'):
            p = '"' + p + '"'
    return p


def separator_string(sep: int) -> str:
    return {
        SEP_SPACE: " ",
        SEP_COMMA: ", ",
        SEP_BLANKLINE: "\n\n",
        SEP_NEWLINE: "\n",
    }[sep]


# ───────────────────── 槽位行组件 ─────────────────────

class SlotRow(QWidget):
    """单行槽位：可重命名标签 + 带历史下拉的路径输入 + Browse + Add + 删除。"""

    def __init__(self, slot: Slot, parent_window: "MainWindow"):
        super().__init__()
        self.slot = slot
        self.win = parent_window

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        # 可重命名的槽位名（双击进入编辑）
        self.name_edit = QLineEdit(slot.name)
        self.name_edit.setReadOnly(True)
        self.name_edit.setFixedWidth(72)
        self.name_edit.setStyleSheet("font-weight: 600; border: none;")
        self.name_edit.setToolTip("双击重命名")
        self.name_edit.mouseDoubleClickEvent = self._on_name_double_click  # type: ignore
        self.name_edit.editingFinished.connect(self._on_name_finished)

        # 带历史的路径下拉（可手输）
        self.path_combo = QComboBox()
        self.path_combo.setEditable(True)
        self.path_combo.addItems(slot.history)
        self.path_combo.setToolTip("从历史选，或直接输入/粘贴路径")

        browse_btn = QPushButton("…")
        browse_btn.setFixedWidth(28)
        browse_btn.setToolTip("浏览文件 / 文件夹")
        browse_btn.clicked.connect(self._on_browse)

        add_btn = QPushButton("Add")
        add_btn.setToolTip("把当前路径加入下方输出框")
        add_btn.clicked.connect(self._on_add)

        layout.addWidget(self.name_edit)
        layout.addWidget(self.path_combo, stretch=1)
        layout.addWidget(browse_btn)
        layout.addWidget(add_btn)

        # 仅非固定槽位（用户自添加的）显示删除按钮，防止误删 code/elf/map。
        if not is_fixed_slot(slot):
            remove_btn = QPushButton("✕")
            remove_btn.setFixedWidth(28)
            remove_btn.setToolTip("删除该槽位")
            remove_btn.clicked.connect(lambda: self.win.remove_slot(self))
            layout.addWidget(remove_btn)

    # ── 重命名 ──
    def _on_name_double_click(self, _event):
        self.name_edit.setReadOnly(False)
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def _on_name_finished(self):
        raw = self.name_edit.text().strip()
        if not raw:
            raw = self.slot.name
        # 去重命名
        dup = sum(1 for s in self.win.settings.slots if s is not self.slot and s.name == raw)
        if dup > 0:
            raw = f"{raw}_{dup + 1}"
        self.slot.name = raw
        self.name_edit.setText(raw)
        self.name_edit.setReadOnly(True)

    # ── Browse ──
    def _on_browse(self):
        # 用非原生 QFileDialog：一次操作即可选中文件或文件夹（双击进入目录，
        # 选中目录后点"选择"即返回该目录路径）。避免"选文件还是文件夹"的二次确认。
        dlg = QFileDialog(self, "选择文件或文件夹")
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        # ExistingFile 允许选中已存在的文件；非原生模式下也能选中目录（点"选择"返回目录）。
        dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, False)
        if not dlg.exec():
            return
        files = dlg.selectedFiles()
        if not files:
            return
        path = resolve_shortcut(files[0])
        self.path_combo.setEditText(path)

    # ── Add ──
    def current_path(self) -> str:
        return self.path_combo.currentText().strip()

    def _on_add(self):
        path = self.current_path()
        if not path:
            QMessageBox.information(self, APP_NAME, "请先选择或输入一个路径。")
            return
        # 以槽位名作为标签前缀，输出形如 'code: <path>'。
        self.win.add_path_to_output(path, label=self.slot.name)
        self.push_history(path)

    def push_history(self, path: str) -> None:
        h = self.slot.history
        if path in h:
            h.remove(path)
        h.insert(0, path)
        if len(h) > MAX_HISTORY:
            del h[MAX_HISTORY:]
        # 同步到下拉
        self.path_combo.clear()
        self.path_combo.addItems(h)


# ───────────────────── 快捷方式(.lnk)解析 ─────────────────────

def resolve_shortcut(path: str) -> str:
    """解析 .lnk 到真实目标路径；非 .lnk 或失败则原样返回。

    使用 PowerShell + WScript.Shell COM（系统自带），不依赖 pywin32，
    避免 PyInstaller 打包时 hidden import 的麻烦。
    """
    if not path.lower().endswith(".lnk"):
        return path
    try:
        import subprocess
        # 单引号转义：PowerShell here-string 内用单引号，路径中的单引号翻倍
        safe = path.replace("'", "''")
        ps = (
            "$ErrorActionPreference='SilentlyContinue';"
            "$s=New-Object -ComObject WScript.Shell;"
            "$t=$s.CreateShortcut('" + safe + "').TargetPath;"
            "Write-Output $t"
        )
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=5,
        )
        target = out.stdout.strip()
        return target or path
    except Exception:
        return path


# ───────────────────── 主窗口 ─────────────────────

class OutputEdit(QPlainTextEdit):
    """输出框：支持文件拖拽加入；标记用户手动编辑。"""

    def __init__(self, win: "MainWindow"):
        super().__init__()
        self.win = win
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):  # type: ignore[override]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):  # type: ignore[override]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):  # type: ignore[override]
        if not event.mimeData().hasUrls():
            return
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local:
                self.win.add_path_to_output(resolve_shortcut(local))
        event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.raw_entries: list = []           # 元素为 (label:str, raw_path:str)
        self.user_edited = False              # 用户是否手动编辑过输出框
        self.suppress_change = False          # 重绘输出框期间抑制编辑判定
        self.slot_rows: List[SlotRow] = []

        self.setWindowTitle(APP_NAME)
        self.resize(settings.window_width, settings.window_height)
        self.setMinimumSize(560, 480)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ── 顶栏 ──
        top = QHBoxLayout()
        title = QLabel(f"📌 {APP_NAME}")
        title.setStyleSheet("font-weight: bold;")
        top.addWidget(title)
        top.addStretch(1)
        self.on_top_check = QCheckBox("置顶")
        self.on_top_check.setChecked(settings.always_on_top)
        self.on_top_check.toggled.connect(self._on_top_toggled)
        top.addWidget(self.on_top_check)
        clear_hist_btn = QPushButton("清除全部历史")
        clear_hist_btn.clicked.connect(self._on_clear_all_history)
        top.addWidget(clear_hist_btn)
        root.addLayout(top)

        # ── 槽位区 ──
        self.slot_group = QGroupBox("路径槽位（双击名称重命名 · 拖文件到下方输出框也可加入）")
        self.slot_layout = QVBoxLayout(self.slot_group)
        self.slot_layout.setContentsMargins(8, 12, 8, 8)
        root.addWidget(self.slot_group)

        self.add_slot_btn = QPushButton("+ 添加槽位")
        self.add_slot_btn.clicked.connect(self._on_add_slot)
        self.slot_layout.addWidget(self.add_slot_btn)

        # ── 配置区 ──
        cfg = QGroupBox("输出格式")
        cl = QGridLayout(cfg)
        cl.addWidget(QLabel("格式:"), 0, 0)
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(FORMATS)
        self.fmt_combo.setCurrentIndex(settings.path_format)
        self.fmt_combo.currentIndexChanged.connect(self._on_format_changed)
        cl.addWidget(self.fmt_combo, 0, 1)
        cl.addWidget(QLabel("分隔:"), 0, 2)
        self.sep_combo = QComboBox()
        self.sep_combo.addItems(SEPARATORS)
        self.sep_combo.setCurrentIndex(settings.separator)
        self.sep_combo.currentIndexChanged.connect(self._on_sep_changed)
        cl.addWidget(self.sep_combo, 0, 3)
        self.auto_quote_check = QCheckBox("含空格自动加引号")
        self.auto_quote_check.setChecked(settings.auto_quote_spaces)
        self.auto_quote_check.toggled.connect(self._on_auto_quote_changed)
        cl.addWidget(self.auto_quote_check, 0, 4)
        cl.setColumnStretch(1, 1)
        root.addWidget(cfg)

        # ── 输出区 ──
        out = QGroupBox("输出（可直接编辑 · 复制内容即此框全部文本）")
        ol = QVBoxLayout(out)
        self.output = OutputEdit(self)
        self.output.setPlaceholderText("拖拽文件/文件夹到此，或用上方槽位的 Add 加入路径…")
        f = self.output.font()
        f.setFamily("Consolas")
        self.output.setFont(f)
        self.output.textChanged.connect(self._on_output_changed)
        ol.addWidget(self.output)
        root.addWidget(out, stretch=1)

        # ── 操作按钮行 ──
        bottom = QHBoxLayout()
        hint = QLabel("拖拽文件到此也可加入")
        hint.setStyleSheet("color: #888; font-style: italic;")
        bottom.addWidget(hint)
        bottom.addStretch(1)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._on_clear_output)
        bottom.addWidget(clear_btn)
        self.copy_btn = QPushButton("复制 📋")
        self.copy_btn.setStyleSheet("font-weight: 600;")
        self.copy_btn.clicked.connect(self._on_copy)
        bottom.addWidget(self.copy_btn)
        root.addLayout(bottom)

        # 构建槽位行
        self._rebuild_slot_rows()
        self._refresh_add_slot_button()
        # 注：置顶在首次 showEvent 时应用（winId 此时才可用）。

    def showEvent(self, event):  # type: ignore[override]
        super().showEvent(event)
        # 首次显示后应用置顶状态（winId 此时已建立）。
        self._apply_on_top()

    # ───────── 槽位管理 ─────────
    def _rebuild_slot_rows(self):
        # 清空旧行
        for row in self.slot_rows:
            row.setParent(None)
            row.deleteLater()
        self.slot_rows = []
        # 重建（add 按钮是 slot_layout 的最后一个 widget，插入到它之前）
        for slot in self.settings.slots:
            row = SlotRow(slot, self)
            self.slot_layout.insertWidget(self.slot_layout.count() - 1, row)
            self.slot_rows.append(row)

    def _on_add_slot(self):
        if len(self.settings.slots) >= MAX_SLOTS:
            return
        base = "slot"
        name = base
        n = 2
        while any(s.name == name for s in self.settings.slots):
            name = f"{base}{n}"
            n += 1
        self.settings.slots.append(Slot(name))
        self._rebuild_slot_rows()
        self._refresh_add_slot_button()

    def remove_slot(self, row: SlotRow):
        if is_fixed_slot(row.slot):
            # 固定槽位不可删除（删除按钮本就不显示，此处为防御性保护）。
            return
        if len(self.settings.slots) <= MIN_SLOTS:
            QMessageBox.information(self, APP_NAME, "至少需要保留 1 个槽位。")
            return
        if row.slot in self.settings.slots:
            self.settings.slots.remove(row.slot)
        self._rebuild_slot_rows()
        self._refresh_add_slot_button()

    def _refresh_add_slot_button(self):
        self.add_slot_btn.setEnabled(len(self.settings.slots) < MAX_SLOTS)
        if len(self.settings.slots) >= MAX_SLOTS:
            self.add_slot_btn.setToolTip("已达上限（5 个）")
        else:
            self.add_slot_btn.setToolTip("新增一个槽位（最多 5 个）")

    # ───────── 输出框：拼接 / 重绘 ─────────
    def add_path_to_output(self, raw_path: str, label: str = ""):
        """把一条原始路径加入输出。label 非空时，输出行前缀 'label: '。

        label 一般为槽位名（如 code），让输出清晰归属，例如：
            code: D:/git/pathcopy/build.bat
        """
        self.raw_entries.append((label, raw_path))
        self._render_output_from_raw()
        self.output.moveCursor(Qt.MoveOperation.End)

    def _render_output_from_raw(self):
        if not self.raw_entries:
            self.suppress_change = True
            self.output.setPlainText("")
            self.suppress_change = False
            return
        lines = []
        for label, p in self.raw_entries:
            formatted = format_path(p, self.settings.path_format, self.settings.auto_quote_spaces)
            if label:
                lines.append(f"{label}: {formatted}")
            else:
                lines.append(formatted)
        self.suppress_change = True
        self.output.setPlainText(separator_string(self.settings.separator).join(lines))
        self.suppress_change = False

    def _on_output_changed(self):
        if self.suppress_change:
            return
        self.user_edited = True

    def _on_clear_output(self):
        self.raw_entries.clear()
        self.user_edited = False
        self.suppress_change = True
        self.output.clear()
        self.suppress_change = False

    # ───────── 格式 / 分隔符 / 选项 ─────────
    def _on_format_changed(self, idx: int):
        self.settings.path_format = idx
        self._reflow_output()

    def _on_sep_changed(self, idx: int):
        self.settings.separator = idx
        self._reflow_output()

    def _on_auto_quote_changed(self, checked: bool):
        self.settings.auto_quote_spaces = checked
        self._reflow_output()

    def _reflow_output(self):
        """切换格式/分隔符时：若输出未被手动编辑，基于原始列表整体重排；
        若已被手动编辑，尊重用户修改，新设置仅影响后续加入项。"""
        if self.user_edited:
            return
        self._render_output_from_raw()

    # ───────── 复制 / 历史 / 置顶 ─────────
    def _on_copy(self):
        text = self.output.toPlainText()
        if not text:
            QMessageBox.information(self, APP_NAME, "输出框为空，没有内容可复制。")
            return
        try:
            cb = QApplication.clipboard()
            cb.setText(text)
            self._flash_copy_button()
        except Exception as e:
            QMessageBox.critical(self, APP_NAME, f"复制失败：{e}")

    def _flash_copy_button(self):
        orig = self.copy_btn.text()
        self.copy_btn.setText("已复制 ✓")
        self.copy_btn.setStyleSheet("font-weight: 600; background-color: #90EE90;")
        QTimer_flash(self.copy_btn, orig)

    def _on_clear_all_history(self):
        if QMessageBox.question(
            self, "确认", "确定清空所有槽位的历史记录吗？（不会影响槽位本身）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        for s in self.settings.slots:
            s.history.clear()
        for row in self.slot_rows:
            row.path_combo.clear()

    def _on_top_toggled(self, checked: bool):
        self.settings.always_on_top = checked
        self._apply_on_top()

    def _apply_on_top(self):
        # 切换"始终置顶"。注意：不要用 setWindowFlags()——它会重建窗口，
        # 在某些情况下导致标题栏的关闭/最小化按钮失效变灰。
        # 改用 Win32 SetWindowPos 直接改 HWND_TOPMOST，不重建 Qt 窗口，安全可靠。
        if not self.isVisible():
            return
        try:
            import ctypes
            HWND_TOPMOST = -1
            HWND_NOTOPMOST = -2
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
            hwnd_insert_after = HWND_TOPMOST if self.settings.always_on_top else HWND_NOTOPMOST
            ctypes.windll.user32.SetWindowPos(
                int(self.winId()), hwnd_insert_after, 0, 0, 0, 0, flags
            )
        except Exception:
            # 非 Windows 或调用失败时回退（仅初始化阶段用，运行时已确保可见）
            pass

    # ───────── 关闭持久化 ─────────
    def closeEvent(self, event):
        self.settings.window_width = self.width()
        self.settings.window_height = self.height()
        save_settings(self.settings)
        super().closeEvent(event)


def QTimer_flash(button: QPushButton, orig_text: str):
    """延迟恢复按钮文本/样式（避免为单次延迟引入 QTimer 成员）。"""
    from PySide6.QtCore import QTimer
    QTimer.singleShot(800, lambda: (
        button.setText(orig_text),
        button.setStyleSheet("font-weight: 600;"),
    ))


# ───────────────────── 入口 ─────────────────────

def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # 单实例：第二个实例直接退出
    single = None
    try:
        from PySide6.QtNetwork import QLocalServer, QLocalSocket
        single = SingleInstanceGuard(APP_NAME)
        if not single.try_lock():
            QMessageBox.information(None, APP_NAME, f"{APP_NAME} 已经在运行中。")
            return 0
    except Exception:
        pass  # 单实例失败不阻塞启动

    win = MainWindow(load_settings())
    win.show()
    code = app.exec()
    if single is not None:
        single.release()
    return code


class SingleInstanceGuard:
    """基于 QLocalServer/QLocalSocket 的简易单实例锁。"""

    def __init__(self, name: str):
        self._name = f"{name}_single_instance"
        self._server = None

    def try_lock(self) -> bool:
        from PySide6.QtNetwork import QLocalServer, QLocalSocket
        # 尝试连接已有实例
        sock = QLocalSocket()
        sock.connectToServer(self._name)
        if sock.waitForConnected(200):
            sock.disconnectFromServer()
            return False  # 已有实例
        # 没有则创建本地服务端占位
        QLocalServer.removeServer(self._name)
        self._server = QLocalServer()
        self._server.listen(self._name)
        return True

    def release(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None


if __name__ == "__main__":
    raise SystemExit(main())
