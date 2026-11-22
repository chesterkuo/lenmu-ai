#!/usr/bin/env python3
"""
framecheck.py — 送影片前檢查首幀與尾幀。

輸出（都存成新檔，不改原圖）：
  overlay.jpg   首尾幀 50% 疊圖：看錯位、多出來或消失的東西
  diff.jpg      差異熱圖（放大顯示）：不該變的地方（牆、桌面、背景）應該是黑的
  grid.txt      3x3 格子的平均差異，數字大的格子要放大看
  phone.jpg     首尾幀並排縮到手機寬（約 390 px）：遠處的人看不看得清楚
  zoom_*.jpg    首幀切成 3x3、每格放大 2 倍：找多餘的東西、怪線、多出來的手指

需求：pip install pillow numpy
用法：python3 framecheck.py first.png last.png outdir/
"""
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageOps


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    a_path, b_path, outdir = sys.argv[1:]
    os.makedirs(outdir, exist_ok=True)
    a = Image.open(a_path).convert("RGB")
    b = Image.open(b_path).convert("RGB")
    if a.size != b.size:
        print(f"注意：首尾幀尺寸不同 {a.size} vs {b.size}，已把尾幀縮放到首幀尺寸比對。尺寸不同本身就要修。")
        b = b.resize(a.size, Image.LANCZOS)
    w, h = a.size

    Image.blend(a, b, 0.5).save(os.path.join(outdir, "overlay.jpg"), quality=92)

    diff = np.asarray(ImageChops.difference(a, b).convert("L"), dtype=np.float32)
    amp = np.clip(diff * 4, 0, 255).astype(np.uint8)
    ImageOps.colorize(Image.fromarray(amp), black="black", white="red", mid="yellow").save(
        os.path.join(outdir, "diff.jpg"), quality=92)

    lines = ["3x3 平均差異（0–255；背景、牆面這種不該變的格子最好 < 8）"]
    for r in range(3):
        row = []
        for c in range(3):
            cell = diff[r * h // 3:(r + 1) * h // 3, c * w // 3:(c + 1) * w // 3]
            row.append(f"{cell.mean():6.1f}")
        lines.append(" ".join(row))
    ma = np.asarray(a, dtype=np.float32).reshape(-1, 3).mean(0)
    mb = np.asarray(b, dtype=np.float32).reshape(-1, 3).mean(0)
    lines.append(f"整體平均色 首幀 RGB {[round(float(x), 1) for x in ma]}  尾幀 RGB {[round(float(x), 1) for x in mb]}")
    if np.abs(ma - mb).max() > 6:
        lines.append("提醒：整體色調差太多，影片裡可能會慢慢變色。")
    open(os.path.join(outdir, "grid.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))

    pw = 390
    ph = int(h * pw / w)
    phone = Image.new("RGB", (pw * 2 + 10, ph), (0, 0, 0))
    phone.paste(a.resize((pw, ph), Image.LANCZOS), (0, 0))
    phone.paste(b.resize((pw, ph), Image.LANCZOS), (pw + 10, 0))
    phone.save(os.path.join(outdir, "phone.jpg"), quality=92)

    for r in range(3):
        for c in range(3):
            box = (c * w // 3, r * h // 3, (c + 1) * w // 3, (r + 1) * h // 3)
            tile = a.crop(box)
            tile.resize((tile.width * 2, tile.height * 2), Image.LANCZOS).save(
                os.path.join(outdir, f"zoom_r{r + 1}c{c + 1}.jpg"), quality=92)
    print(f"輸出：{outdir}/overlay.jpg、diff.jpg、grid.txt、phone.jpg、zoom_r*c*.jpg")


if __name__ == "__main__":
    main()
