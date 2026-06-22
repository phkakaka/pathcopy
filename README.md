# PathCopy

Windows 桌面小工具：快速收集文件 / 文件夹路径，按指定格式拼好后一键复制到剪贴板，方便粘贴给 AI 助手（Cursor、Cline、Claude 等）使用。

## 功能

- **多槽位路径收集**：默认 3 个槽位 `code` / `elf` / `map`，可双击改名、可增删，最多 5 个。
- **每个槽位独立历史**：最近 10 条，跨会话保留，下拉直接复用。
- **灵活的输出格式**：绝对路径 / 正斜杠 / `@` 前缀 / 加引号 / 仅文件名 / 仅目录。
- **可选分隔符**：换行 / 空格 / 逗号 / 空行；含空格路径可自动加引号。
- **拖拽加入**：把文件 / 文件夹直接拖进输出框即可加入。
- **可编辑输出框**：所见即所复制，随时手工修改。
- **快捷方式解析**：拖入 / 选择的 `.lnk` 会自动解析到真实目标路径（通过系统 WScript.Shell，无需额外依赖）。
- **窗口置顶**、**单实例**、**窗口尺寸记忆**。

## 界面

```
┌─ PathCopy ───────────────────────── □ × ├
│ 📌 PathCopy              [☑置顶][清除全部历史]│
│ ── 路径槽位 ─────────────────────────── │
│ code [下拉...▾][…][Add][✕]              │
│ elf  [下拉...▾][…][Add][✕]              │
│ map  [下拉...▾][…][Add][✕]              │
│                              [+ 添加槽位] │
│ ── 输出格式 ─────────────────────────── │
│ 格式:[绝对路径▾]  分隔:[换行▾]  ☑含空格加引号│
│ ── 输出（可直接编辑）────────────────── │
│ ┌──────────────────────────────────┐   │
│ │ D:\...\a.txt                     │   │
│ │ D:\...\b.cs                      │   │
│ └──────────────────────────────────┘   │
│  拖拽文件到此也可加入    [清空][复制 📋]   │
└──────────────────────────────────────────┘
```

## 构建

运行根目录的 `build.bat`（需本机已安装 Python 3.10+，脚本会自动 `pip install` 依赖并打包）：

```bat
build.bat
```

产物：
- `dist\PathCopy.exe` —— PyInstaller 默认输出
- **`PathCopy.exe`（根目录）** —— 同时拷贝一份到根目录，即最终交付的单文件 exe

也可手动构建：

```powershell
python -m pip install -r requirements.txt
python -m PyInstaller --clean --noconfirm PathCopy.spec
Copy-Item dist\PathCopy.exe PathCopy.exe -Force
```

> PyInstaller 打包后是 **self-contained 单文件**（Python 解释器已内嵌），拷到任何 Win10/11 双击即跑，**无需目标机器装 Python**。体积约 60–90MB（PySide6 带来的体积）。

## 直接运行（开发期，不打包）

```powershell
python -m pip install -r requirements.txt
python pathcopy.py
```

## 配置

配置与历史保存在：

```
%AppData%\PathCopy\settings.json
```

删除该文件即可恢复默认设置（3 个槽位 code / elf / map）。

## 技术栈

- Python 3.10+
- PySide6 (Qt6) —— GUI、拖拽、剪贴板
- PyInstaller —— 打包成单文件 exe

## License

MIT
