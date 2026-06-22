"""生成 PathCopy 应用图标 assets/pathcopy.ico。

用 PIL 程序化绘制：圆角方框背景 + 路径折线 + 文件夹剪影，
寓意"收集路径"。输出多尺寸 .ico（Windows 任务栏/标题栏/资源管理器）。

用法：  python scripts/make_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT_ICO = Path(__file__).resolve().parent.parent / "assets" / "pathcopy.ico"
OUT_PNG = OUT_ICO.with_suffix(".png")  # 顺带输出 256 png，方便预览/嵌入

# 配色（现代、克制）：深蓝青底 + 暖橙强调
BG_TOP = (30, 115, 190)       # #1E73BE
BG_BOT = (20, 84, 139)        # #14548B
PATH_COLOR = (255, 255, 255)  # 白色路径折线
ACCENT = (255, 176, 59)       # #FFB03B 橙色节点
FOLDER = (255, 220, 130)      # 浅黄文件夹剪影

SIZES = [16, 24, 32, 48, 64, 128, 256]


def _vgrad(size: int, top, bot) -> Image.Image:
    """垂直渐变填充。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    for y in range(size):
        t = y / max(size - 1, 1)
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        for x in range(size):
            px[x, y] = (r, g, b, 255)
    return img


def draw(size: int) -> Image.Image:
    """在 size×size 画布上绘制图标。"""
    s = float(size)
    # 用 4x 超采样再缩放，得到锐利的抗锯齿边缘（小尺寸尤其受益）。
    m = 4
    big = int(s * m)
    img = _vgrad(big, BG_TOP, BG_BOT)
    d = ImageDraw.Draw(img)

    # 圆角遮罩
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, big - 1, big - 1], radius=int(0.22 * big), fill=255
    )
    rounded = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    rounded.paste(img, (0, 0), mask)
    img = rounded
    d = ImageDraw.Draw(img)

    # ── 路径折线（白色）：左下 → 中上节点 → 右下，节点为橙色圆点 ──
    lw = max(int(big * 0.045), 2)
    p1 = (big * 0.18, big * 0.74)
    p2 = (big * 0.50, big * 0.34)
    p3 = (big * 0.82, big * 0.62)
    d.line([p1, p2, p3], fill=PATH_COLOR, width=lw, joint="curve")
    nd = max(int(big * 0.055), 3)
    for p in (p1, p2, p3):
        d.ellipse([p[0] - nd, p[1] - nd, p[0] + nd, p[1] + nd], fill=ACCENT)

    # ── 右下角文件夹剪影：强调"收集/复制文件"语义 ──
    fw, fh = big * 0.42, big * 0.30
    fx = big - fw - big * 0.10
    fy = big - fh - big * 0.12
    # 文件夹主体
    d.rounded_rectangle(
        [fx, fy + fh * 0.22, fx + fw, fy + fh],
        radius=int(fh * 0.16),
        fill=FOLDER,
    )
    # 文件夹"耳朵"
    tab_w, tab_h = fw * 0.38, fh * 0.26
    d.polygon(
        [(fx, fy + fh * 0.22),
         (fx + tab_w, fy + fh * 0.22),
         (fx + tab_w + tab_h * 0.6, fy),
         (fx, fy)],
        fill=FOLDER,
    )
    # 加一点描边分隔（深色），增强层次
    edge = (BG_TOP[0] // 2, BG_TOP[1] // 2, BG_TOP[2] // 2, 220)
    d.rounded_rectangle(
        [fx, fy + fh * 0.22, fx + fw, fy + fh],
        radius=int(fh * 0.16), outline=edge, width=max(int(big * 0.012), 1),
    )

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT_ICO.parent.mkdir(parents=True, exist_ok=True)
    # PIL 的 ICO 写入器从单张"主图"出发，按 sizes 列表缩放生成各尺寸帧。
    # 因此传一张 256 主图 + 完整 sizes 列表即可，无需手工预生成多张。
    master = draw(256)
    master.save(OUT_ICO, format="ICO", sizes=[(n, n) for n in SIZES])
    master.save(OUT_PNG, format="PNG")
    print(f"icon -> {OUT_ICO} ({len(SIZES)} sizes)")
    print(f"png  -> {OUT_PNG}")


if __name__ == "__main__":
    main()
