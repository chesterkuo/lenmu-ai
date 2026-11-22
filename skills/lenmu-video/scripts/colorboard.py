#!/usr/bin/env python3
"""
colorboard.py — 用色塊草圖檢查分鏡構圖與配色（畫任何圖之前做）。

讀一個 JSON 分鏡規格，為每個鏡頭畫一張 1920x1080 色塊草圖：
  - 背景色、主要物件（人物、道具）用色塊表示
  - 標出畫面寬 38% 與 62% 的直線（人的頭或眼睛應落在附近）
  - 鏡號、時間、說明
然後輸出：
  - 每鏡一張 PNG
  - 彩色總表 board.png、黑白總表 board_gray.png
  - 明暗對比報告：每個 subject 和它周圍背景的亮度差（CIE L*），太小就提醒

需求：pip install pillow numpy
用法：python3 colorboard.py spec.json outdir/

spec.json 範例：
{
  "font": "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
  "palette": {
    "雨夜": {"bg": "#1b2433", "mid": "#33415c", "light": "#e9e4d4", "accent": "#d9772b", "skin": "#c99a7a"}
  },
  "shots": [
    {"id": "S01", "scene": "雨夜", "time": "0:00-0:03", "note": "大遠景，便利商店是唯一亮點",
     "bg": "bg",
     "elements": [
       {"name": "店面", "color": "light", "box": [0.55, 0.40, 0.30, 0.35]},
       {"name": "阿哲", "color": "mid", "box": [0.34, 0.55, 0.06, 0.30], "subject": true, "shape": "person"}
     ]}
  ]
}
box 是 [x, y, w, h]，皆為畫面寬高的比例，原點左上。color 可以寫 palette 裡的名稱或 #hex。
shape: rect（預設）、ellipse、person（頭＋身體）。
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
MIN_DL = 20.0  # subject 與周圍背景 L* 差小於這個值就提醒


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def srgb_to_lab_L(rgb):
    c = np.asarray(rgb, dtype=np.float64) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    y = 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]
    return np.where(y > 216 / 24389, 116 * np.cbrt(y) - 16, y * 24389 / 27)


def resolve(color, palette):
    if color.startswith("#"):
        return hex2rgb(color)
    if color not in palette:
        sys.exit(f"palette 裡沒有顏色 {color}")
    return hex2rgb(palette[color])


def draw_shape(d, shape, box, rgb):
    x, y, w, h = box
    x0, y0, x1, y1 = x * W, y * H, (x + w) * W, (y + h) * H
    if shape == "ellipse":
        d.ellipse([x0, y0, x1, y1], fill=rgb)
    elif shape == "person":
        head = min(x1 - x0, (y1 - y0) * 0.22)
        cx = (x0 + x1) / 2
        d.ellipse([cx - head / 2, y0, cx + head / 2, y0 + head], fill=rgb)
        d.rounded_rectangle([x0, y0 + head * 1.05, x1, y1], radius=int(head * 0.35), fill=rgb)
    else:
        d.rectangle([x0, y0, x1, y1], fill=rgb)
    return [int(x0), int(y0), int(x1), int(y1)]


def render_shot(shot, palette, font, small):
    scene_pal = palette.get(shot.get("scene"), {})
    pal = {**{k: v for p in palette.values() for k, v in p.items()}, **scene_pal}
    img = Image.new("RGB", (W, H), resolve(shot.get("bg", "bg"), pal))
    d = ImageDraw.Draw(img)
    rects = []
    for el in shot.get("elements", []):
        rgb = resolve(el["color"], pal)
        r = draw_shape(d, el.get("shape", "rect"), el["box"], rgb)
        rects.append((el, r))
    plain = img.copy()
    for frac in (0.38, 0.62):
        x = int(W * frac)
        for yy in range(0, H, 24):
            d.line([x, yy, x, yy + 12], fill=(255, 64, 64), width=3)
        d.text((x + 6, 8), f"{int(frac * 100)}%", fill=(255, 64, 64), font=small)
    for el, (x0, y0, x1, y1) in rects:
        d.text((x0 + 6, max(0, y0 - 34)), el["name"], fill=(255, 255, 255), font=small,
               stroke_width=3, stroke_fill=(0, 0, 0))
    title = f'{shot["id"]}  {shot.get("time", "")}  {shot.get("note", "")}'
    d.rectangle([0, H - 64, W, H], fill=(0, 0, 0))
    d.text((20, H - 56), title, fill=(255, 255, 255), font=font)
    return img, plain, rects


def contrast_report(shot, plain, rects):
    arr = np.asarray(plain)
    L = srgb_to_lab_L(arr)
    out = []
    for el, (x0, y0, x1, y1) in rects:
        if not el.get("subject"):
            continue
        pad = int(max(x1 - x0, y1 - y0) * 0.35) + 10
        X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
        ring = np.ones((Y1 - Y0, X1 - X0), bool)
        ring[(y0 - Y0):(y1 - Y0), (x0 - X0):(x1 - X0)] = False
        inner = L[y0:y1, x0:x1]
        outer = L[Y0:Y1, X0:X1][ring]
        if inner.size == 0 or outer.size == 0:
            continue
        dl = abs(float(np.median(inner)) - float(np.median(outer)))
        cx = ((x0 + x1) / 2) / W
        out.append({"shot": shot["id"], "subject": el["name"], "dL": round(dl, 1), "x": round(cx, 3),
                    "ok_contrast": dl >= MIN_DL,
                    "near_38_62": min(abs(cx - 0.38), abs(cx - 0.62)) <= 0.06})
    return out


def contact(images, cols=3, tile_w=640):
    tile_h = int(tile_w * H / W)
    rows = math.ceil(len(images) / cols)
    sheet = Image.new("RGB", (cols * tile_w + (cols + 1) * 12, rows * tile_h + (rows + 1) * 12), (30, 30, 30))
    for i, im in enumerate(images):
        r, c = divmod(i, cols)
        sheet.paste(im.resize((tile_w, tile_h), Image.LANCZOS), (12 + c * (tile_w + 12), 12 + r * (tile_h + 12)))
    return sheet


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    candidates = [spec.get("font")] if spec.get("font") else []
    candidates += [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",            # Linux
        "/System/Library/Fonts/PingFang.ttc",                              # macOS
        "/System/Library/Fonts/STHeiti Medium.ttc",                        # macOS 舊版
        "C:/Windows/Fonts/msjh.ttc",                                       # Windows 微軟正黑體
    ]
    font = small = None
    for fpath in candidates:
        try:
            font, small = ImageFont.truetype(fpath, 40), ImageFont.truetype(fpath, 30)
            break
        except OSError:
            continue
    if font is None:
        print("找不到中文字型，標籤可能顯示成方塊；可在 spec.json 用 \"font\" 指定字型路徑。")
        font = small = ImageFont.load_default()
    palette = spec["palette"]
    shots_img, report = [], []
    for shot in spec["shots"]:
        img, plain, rects = render_shot(shot, palette, font, small)
        img.save(os.path.join(outdir, f'{shot["id"]}.png'))
        shots_img.append(img)
        report += contrast_report(shot, plain, rects)
    board = contact(shots_img)
    board.save(os.path.join(outdir, "board.png"))
    board.convert("L").convert("RGB").save(os.path.join(outdir, "board_gray.png"))
    json.dump(report, open(os.path.join(outdir, "contrast.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    for r in report:
        flags = []
        if not r["ok_contrast"]:
            flags.append(f"明暗差太小（ΔL*={r['dL']}，建議 ≥ {MIN_DL:.0f}）")
        if not r["near_38_62"]:
            flags.append(f"位置 {r['x']:.0%} 離 38%/62% 太遠")
        print(f'{r["shot"]} {r["subject"]}: ' + ("；".join(flags) if flags else "OK"))
    print(f"輸出：{outdir}/board.png、board_gray.png、contrast.json")


if __name__ == "__main__":
    main()
