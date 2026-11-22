#!/usr/bin/env python3
"""
micromosaic.py — 只在 AI 生成人物的「眼睛」與「嘴巴」打微馬賽克。

用途：Lenmu / Seedream 生成的虛構寫實人物，送 Seedance 時被判定為真人臉而被拒，
      先把眼、嘴打成很小的馬賽克，再在影片提示詞要求還原清楚的眼睛與嘴巴。
限制：只能用在 AI 生成的虛構人物。不可用在任何真實人物的照片上。

需求：pip install opencv-python numpy
模型：OpenCV Zoo 的 YuNet（face_detection_yunet_2023mar.onnx, MIT License）
      https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet

用法：
  python3 micromosaic.py in.png out.jpg --model face_detection_yunet_2023mar.onnx
  可選：--score 0.72（偵測門檻）  --div 14（方塊大小＝臉寬／div）  --preview preview.jpg
"""
import argparse
import sys

import cv2
import numpy as np


def detect_faces(img, model_path, score_thr, max_side=1600):
    h, w = img.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    small = cv2.resize(img, (int(w * scale), int(h * scale))) if scale < 1 else img
    sh, sw = small.shape[:2]
    det = cv2.FaceDetectorYN.create(model_path, "", (sw, sh), score_thr, 0.3, 5000)
    _, faces = det.detect(small)
    if faces is None:
        return []
    out = []
    for f in faces:
        vals = f[:14] / scale
        out.append((vals, float(f[14])))
    return out


def pixelate(img, x0, y0, x1, y1, block):
    h, w = img.shape[:2]
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(w, int(x1)), min(h, int(y1))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    roi = img[y0:y1, x0:x1]
    rw, rh = max(1, (x1 - x0) // block), max(1, (y1 - y0) // block)
    small = cv2.resize(roi, (rw, rh), interpolation=cv2.INTER_AREA)
    img[y0:y1, x0:x1] = cv2.resize(small, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
    return (x0, y0, x1, y1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--model", required=True, help="YuNet .onnx 路徑")
    ap.add_argument("--score", type=float, default=0.72, help="偵測門檻，太低會把散景亮點當成臉")
    ap.add_argument("--div", type=float, default=14.0, help="馬賽克方塊＝臉寬／div")
    ap.add_argument("--preview", help="另存一張標出偵測框的預覽圖")
    a = ap.parse_args()

    img = cv2.imread(a.src, cv2.IMREAD_COLOR)
    if img is None:
        sys.exit(f"讀不到圖片：{a.src}")
    faces = detect_faces(img, a.model, a.score)
    boxes = []
    for vals, score in faces:
        x, y, fw, fh = vals[:4]
        rex, rey, lex, ley = vals[4:8]
        rmx, rmy, lmx, lmy = vals[10:14]
        block = max(2, int(round(fw / a.div)))
        ew, eh = 0.30 * fw, 0.17 * fw
        for ex, ey in ((rex, rey), (lex, ley)):
            b = pixelate(img, ex - ew / 2, ey - eh / 2, ex + ew / 2, ey + eh / 2, block)
            if b:
                boxes.append(b)
        mx0, mx1 = min(rmx, lmx) - 0.08 * fw, max(rmx, lmx) + 0.08 * fw
        mcy = (rmy + lmy) / 2
        b = pixelate(img, mx0, mcy - 0.11 * fw, mx1, mcy + 0.11 * fw, block)
        if b:
            boxes.append(b)
        print(f"臉 x={x:.0f} y={y:.0f} 寬={fw:.0f} 分數={score:.2f} 方塊={block}px")

    cv2.imwrite(a.dst, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if a.preview:
        pv = img.copy()
        for x0, y0, x1, y1 in boxes:
            cv2.rectangle(pv, (x0, y0), (x1, y1), (0, 0, 255), 2)
        cv2.imwrite(a.preview, pv)
    print(f"共 {len(faces)} 張臉，輸出：{a.dst}")
    if not faces:
        print("沒有偵測到臉：可以把 --score 調低一點再試（例如 0.6），或確認臉不是太小。")


if __name__ == "__main__":
    main()
