#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检测素材里的人脸框，输出 Wav2Lip --box 需要的 y1 y2 x1 x2。

用法：
    python3 detect_face_box.py <video.mp4> [--two] [--scale W H]

--two 用于双人同框素材：分别检测左右半区，输出两个人脸框。
坐标基于视频原始分辨率（与 BOX 常量一致时可直接填进 spec）。
"""
import argparse
import os
import sys

import cv2
import numpy as np

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL, "vendor", "wav2lip"))


def detect(det, img):
    res = det.get_detections_for_batch(np.array([img]))
    return res[0] if len(res) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--two", action="store_true", help="双人同框：分别检测左右")
    args = ap.parse_args()

    import face_detection
    det = face_detection.FaceAlignment(face_detection.LandmarksType._2D,
                                       flip_input=False, device="cpu")
    cap = cv2.VideoCapture(args.video)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        sys.exit("无法读取视频")
    h, w = frame.shape[:2]
    print("frame %dx%d" % (w, h))
    if args.two:
        left = frame[:, :int(w * 0.55)]
        right = frame[:, int(w * 0.45):]
        b1 = detect(det, left)
        b2 = detect(det, right)
        if b1 is not None:
            print("左侧人脸 (y1 y2 x1 x2): %d %d %d %d" % tuple(b1))
        if b2 is not None:
            print("右侧人脸 (y1 y2 x1 x2): %d %d %d %d" %
                  (b2[0], b2[1], b2[2] + int(w * 0.45), b2[3] + int(w * 0.45)))
    else:
        b = detect(det, frame)
        if b is None:
            sys.exit("未检测到人脸")
        print("人脸 (y1 y2 x1 x2): %d %d %d %d" % tuple(b))


if __name__ == "__main__":
    main()
