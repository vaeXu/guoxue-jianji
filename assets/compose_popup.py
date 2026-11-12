# -*- coding: utf-8 -*-
"""用「灵动思考弹窗」重做单段：配音 → 对口型 → 逐帧弹窗渲染 → 合成。"""
import os
import sys
import json
import asyncio
import hashlib
import subprocess
import wave
import imageio_ffmpeg
import edge_tts
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from popup import Popup, GOLD, TEAL, render_sequence

BASE = "/Users/xujiahua/WorkBuddy/2026-11-11-17-16-57/assets"
TMP = "/tmp/wb_pop"
CACHE = os.path.join(TMP, "cache")
OUT = os.path.join(BASE, "sample-popup-test.mp4")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
W, H = 1080, 1920
CREAM = (240, 236, 225, 255)
GOLD4 = (240, 205, 130, 255)
TEAL4 = (165, 232, 222, 255)

VM = os.path.join(BASE, "videos", "master.mp4")
VV = os.path.join(BASE, "videos", "visitor.mp4")
VT = os.path.join(BASE, "videos", "two.mp4")
VIDEO_MAP = {"MASTER": VM, "VISITOR": VV, "TWO": VT}
BOX = {"M": (390, 575, 210, 370), "V": (370, 625, 390, 555),
       "T2M": (195, 360, 205, 335), "T2V": (200, 355, 515, 630)}

W2L_DIR = os.path.join(BASE, "wav2lip")
CKPT = os.path.join(W2L_DIR, "checkpoints", "wav2lip_gan.pth")
TMPBIN = os.path.join(BASE, "tmpbin")

VOICE_MASTER = "zh-CN-YunjianNeural"
VOICE_VISITOR = "zh-CN-YunxiNeural"

# 本次试做：第 5 段（老先生讲「合用」）
SEG = {
    "idx": 5,
    "role": "老先生",
    "text": "你看，癸水合年干戊土正官，古籍叫合用——求的是名分、位置。",
    "video": "MASTER",
    "box": "M",
    "rate": "-8%",
}
POPUP_SPEC = dict(
    title="多途径做功",
    sub="戊申 己未 癸巳 丙辰 ｜ 同一个日主，两条路线",
    tag="古籍断例 ②",
    rows=[("①", "合用", "癸水合年干戊土正官", "名 / 位置", GOLD)],
)
ROW_TIMES = [("合用", 0)]


def font(size):
    return ImageFont.truetype(FONT, size, index=0)


def wrap(text, n=19):
    return [text[i:i + n] for i in range(0, len(text), n)]


def calc_time(text, term, dur):
    if not term:
        return 0.0
    idx = text.find(term)
    if idx < 0:
        return 0.0

    def wt(ch):
        if ch in "，。、；：？！…—,.;:!?":
            return 2.0
        if ch.isspace():
            return 0.0
        return 1.0

    total = sum(wt(c) for c in text)
    return dur * sum(wt(c) for c in text[:idx]) / total


async def _edge_tts(text, voice, rate, mp3):
    await edge_tts.Communicate(text, voice, rate=rate).save(mp3)


def tts(text, role, rate, wav_path, tag):
    voice = VOICE_MASTER if role == "老先生" else VOICE_VISITOR
    mp3 = os.path.join(CACHE, "v_%s.mp3" % tag)
    asyncio.run(_edge_tts(text, voice, rate, mp3))
    raw = os.path.join(CACHE, "v_%s.wav" % tag)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", mp3,
                    "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", raw], check=True)
    with wave.open(raw, "rb") as f:
        frames = f.readframes(f.getnframes())
    pad = 14700
    with wave.open(wav_path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(frames + b"\x00\x00" * pad)
    return (len(frames) / 2) / 44100, (len(frames) / 2 + pad) / 44100


def gen_sub(role, text, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((W - 56, 66), "古籍情景演绎 · 非真人测算", font=font(24),
           fill=(178, 182, 188, 230), anchor="ra")
    lines = wrap(text, 19)[:4]
    box_h = 130 + len(lines) * 66
    top = 1840 - box_h
    d.rounded_rectangle([40, top, 1040, 1840], radius=20, fill=(10, 14, 20, 232))
    accent = GOLD4 if role == "老先生" else TEAL4
    d.rounded_rectangle([70, top + 28, 210, top + 76], radius=8, fill=(38, 44, 54, 255))
    d.text((140, top + 52), role, font=font(26), fill=accent, anchor="mm")
    for i, line in enumerate(lines):
        d.text((70, top + 112 + i * 66), line, font=font(44), fill=CREAM, anchor="lm")
    img.save(path)


def lipsync(video, wav, box, out_path):
    env = os.environ.copy()
    env["PATH"] = TMPBIN + ":" + env.get("PATH", "")
    dummy = os.path.join(CACHE, "dummy.mp4")
    subprocess.run([sys.executable, "inference.py",
                    "--checkpoint_path", CKPT, "--face", video,
                    "--audio", wav, "--outfile", dummy,
                    "--box", str(box[0]), str(box[1]), str(box[2]), str(box[3])],
                   cwd=W2L_DIR, env=env, capture_output=True)
    ravi = os.path.join(W2L_DIR, "temp", "result.avi")
    if not os.path.exists(ravi):
        raise RuntimeError("Wav2Lip result.avi missing")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", ravi, "-i", wav,
                    "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                    "-shortest", out_path], check=True)


def main():
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(TMPBIN, exist_ok=True)
    fr = os.path.join(TMPBIN, "ffmpeg")
    if not os.path.exists(fr):
        os.symlink(FFMPEG, fr)

    text = SEG["text"]
    tag = hashlib.md5((text + SEG["role"] + SEG["rate"]).encode()).hexdigest()[:10]
    wav = os.path.join(CACHE, "a_%s.wav" % tag)
    lip = os.path.join(CACHE, "lip_%s.mp4" % tag)
    meta = os.path.join(CACHE, "m_%s.json" % tag)

    if os.path.exists(meta) and os.path.exists(lip):
        d = json.load(open(meta))
        net, total = d["net"], d["total"]
        print("cache hit", tag, "net=%.2f total=%.2f" % (net, total), flush=True)
    else:
        net, total = tts(text, SEG["role"], SEG["rate"], wav, tag)
        print("tts net=%.2f total=%.2f" % (net, total), flush=True)
        lipsync(VIDEO_MAP[SEG["video"]], wav, BOX[SEG["box"]], lip)
        json.dump({"net": net, "total": total}, open(meta, "w"))
        print("lipsync done", flush=True)

    pop = Popup(POPUP_SPEC["title"], POPUP_SPEC["sub"], POPUP_SPEC["tag"], POPUP_SPEC["rows"])
    times = [calc_time(text, term, net) for term, _ in ROW_TIMES]
    print("row times", ["%.2f" % x for x in times], flush=True)

    fdir = os.path.join(TMP, "frames_%s" % tag)
    n = render_sequence(pop, times, total, fdir, fps=25)
    print("frames", n, flush=True)

    sub = os.path.join(CACHE, "s_%s.png" % tag)
    gen_sub(SEG["role"], text, sub)

    x0 = (W - pop.reg_w) // 2
    y0 = 176
    fc = ("[0:v]delogo=x=6:y=6:w=150:h=54,"
          "scale=1080:1620:force_original_aspect_ratio=decrease,"
          "pad=1080:1920:0:150:color=black[bg];"
          "[2:v]format=rgba[pop];"
          "[bg][pop]overlay=%d:%d:eof_action=pass[wp];"
          "[wp][1:v]overlay=0:0[final]") % (x0, y0)
    cmd = [FFMPEG, "-y", "-loglevel", "error",
           "-i", lip, "-i", sub,
           "-framerate", "25", "-i", os.path.join(fdir, "pop_%04d.png"),
           "-filter_complex", fc, "-map", "[final]", "-map", "0:a",
           "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-r", "25", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
           "-shortest", OUT]
    subprocess.run(cmd, check=True)
    print("DONE", OUT, os.path.getsize(OUT), "bytes", flush=True)


if __name__ == "__main__":
    main()
