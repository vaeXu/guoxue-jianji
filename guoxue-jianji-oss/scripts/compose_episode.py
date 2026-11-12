#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""国学剪辑 · 情景演绎成片主脚本

流程：edge-tts 配音 → Wav2Lip 固定人脸框对口型 → 灵动思考弹窗逐帧渲染 → 字幕叠加 → 拼接成片。

用法：
    python3 compose_episode.py <spec.json> [--only N] [--out PATH] [--no-lipsync] [--keep-frames]

spec.json 结构见 references/pipeline.md，或直接用 assets/episode-spec.example.json。
"""
import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import uuid
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import edge_tts
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

from popup import Popup, GOLD, TEAL

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(SKILL, "assets")
SHOTS = os.path.join(ASSETS, "shots")
CARDS = os.path.join(ASSETS, "cards")
VENDOR = os.path.join(SKILL, "vendor")
W2L = os.path.join(VENDOR, "wav2lip")
CKPT = os.path.join(W2L, "checkpoints", "wav2lip_gan.pth")
BIN = os.path.join(VENDOR, "bin")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

TMP = "/tmp/gxjj"
CACHE = os.path.join(TMP, "cache")

FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
W, H = 1080, 1920
GOLD4 = (240, 205, 130, 255)
BADGE = "古籍情景演绎 · 非真人测算"
TEAL4 = (165, 232, 222, 255)
CREAM = (240, 236, 225, 255)

VOICE = {"老先生": "zh-CN-YunjianNeural", "命主": "zh-CN-YunxiNeural"}
DEFAULT_RATE = {"老先生": "-8%", "命主": "+2%"}
SHOT_FILE = {"MASTER": "master.mp4", "VISITOR": "visitor.mp4", "TWO": "two.mp4"}
# Wav2Lip --box 顺序：y1 y2 x1 x2（像素，基于 768x1152 原始动态素材）
BOX = {"M": (390, 575, 210, 370), "V": (370, 625, 390, 555),
       "T2M": (195, 360, 205, 335), "T2V": (200, 355, 515, 630)}
COLORS = {"gold": GOLD, "teal": TEAL, "GOLD": GOLD, "TEAL": TEAL}

# 弹窗底部不超过这条线，避免压住人物脸（MASTER 头顶约 y=690）
POPUP_MAX_BOTTOM = 655


def font(size):
    return ImageFont.truetype(FONT, size, index=0)


def wrap(text, n=19):
    """按字数断行，但不允许标点悬挂在行首（中文排版忌讳）。"""
    parts = [text[i:i + n] for i in range(0, len(text), n)]
    no_start = set("，。、；：？！…）》」』,.;:!?)]}")
    out = []
    for p in parts:
        if out and p and p[0] in no_start:
            k = 0
            while k < len(p) and p[k] in no_start:
                out[-1] += p[k]
                k += 1
            p = p[k:]
        if p:
            out.append(p)
    return out


def calc_time(text, term, dur):
    """用术语在句中的加权字符位置估算出现时刻（edge-tts 无词级时间戳）。"""
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


# ---------------------------------------------------------------- 配音
async def _edge_tts(text, voice, rate, mp3):
    await edge_tts.Communicate(text, voice, rate=rate).save(mp3)


def tts(text, role, rate, wav_path, tag, use_cache=True):
    mp3 = os.path.join(CACHE, "v_%s.mp3" % tag)
    raw = os.path.join(CACHE, "v_%s.wav" % tag)
    if not (use_cache and os.path.exists(raw)):
        asyncio.run(_edge_tts(text, VOICE[role], rate, mp3))
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", mp3,
                        "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", raw], check=True)
    with wave.open(raw, "rb") as f:
        frames = f.readframes(f.getnframes())
    if len(frames) < 22050:
        raise RuntimeError("TTS 输出为空")
    pad = 14700
    with wave.open(wav_path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(frames + b"\x00\x00" * pad)
    net = (len(frames) / 2) / 44100
    return net, (len(frames) / 2 + pad) / 44100


# ---------------------------------------------------------------- 对口型
def wav_duration(path):
    with wave.open(path, "rb") as f:
        return f.getnframes() / float(f.getframerate())


def prepare_loop_video(shot, needed, out_path):
    """把镜头素材延展到台词长度。

    优先使用技能自带的固化 loop 素材（assets/shots/<shot>_loop.mp4，约 15.5s、
    全 I 帧、已验证 cv2 可完整读取）——避免运行时 ffmpeg 动态生成长视频偶发被
    Wav2Lip 内部的 cv2 在 ~5s 处截断，导致长台词被截成 4.9s。固化素材时长不足
    时才回退到动态生成。
    """
    import re as _re
    solid = os.path.join(ASSETS, "shots", "%s_loop.mp4" % shot.lower())
    if os.path.exists(solid):
        _p = subprocess.run([FFMPEG, "-i", solid], capture_output=True, text=True)
        _m = _re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", _p.stderr)
        _dur = float(_m.group(1)) * 3600 + float(_m.group(2)) * 60 + float(_m.group(3)) if _m else 0
        if _dur >= needed + 0.5:
            return solid
    src = os.path.join(SHOTS, SHOT_FILE[shot])
    x264 = ["-x264-params", "keyint=1:scenecut=0:bframes=0", "-g", "1"]
    probe = subprocess.run([FFMPEG, "-i", src], capture_output=True, text=True)
    m = _re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", probe.stderr)
    orig = float(m.group(1)) * 3600 + float(m.group(2)) * 60 + float(m.group(3)) if m else 5.17
    repeat = int((needed + 1.0) / orig) + 2
    inputs, parts = [], []
    for i in range(repeat):
        inputs += ["-i", src]
        parts.append("[%d:v]" % i)
    fc = "".join(parts) + "concat=n=%d:v=1:a=0,setpts=N/FRAME_RATE/TB[v]" % repeat
    subprocess.run([FFMPEG, "-y", "-loglevel", "error"] + inputs +
                   ["-filter_complex", fc, "-map", "[v]", "-an",
                    "-c:v", "libx264", "-preset", "veryfast"] + x264 +
                   ["-pix_fmt", "yuv420p", out_path], check=True)
    trimmed = out_path + ".trim.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", out_path,
                    "-t", "%.3f" % (needed + 0.5), "-an",
                    "-c:v", "libx264", "-preset", "veryfast"] + x264 +
                   ["-pix_fmt", "yuv420p", trimmed], check=True)
    os.replace(trimmed, out_path)
    return out_path


def video_duration(path):
    import re as _re
    try:
        o = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True).stderr
        m = _re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", o)
        if m:
            return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass
    return 0.0


def lipsync(shot, wav, box_key, out_path, use_cache=True):
    needed = wav_duration(wav)
    # 缓存命中检查：已存在且时长与音频匹配
    if use_cache and os.path.exists(out_path) and os.path.getsize(out_path) > 100000:
        d = video_duration(out_path)
        if d >= needed - 0.3:
            return
    env = os.environ.copy()
    env["PATH"] = BIN + ":" + env.get("PATH", "")
    looped = os.path.join(CACHE, "loop_%s.mp4" % shot)
    video = prepare_loop_video(shot, needed + 0.5, looped)
    ravi = os.path.join(W2L, "temp", "result.avi")
    last_err = ""
    for attempt in range(4):
        # 连续推理之间留一点资源回收时间：本机偶发「上一段刚结束、下一段 rc=1」
        if attempt:
            import time
            time.sleep(1.5 * attempt)
        # 清掉上一轮的残留结果，避免读到陈旧文件
        try:
            if os.path.exists(ravi):
                os.remove(ravi)
        except OSError:
            pass
        r = subprocess.run([sys.executable, "inference.py",
                            "--checkpoint_path", CKPT, "--face", video,
                            "--audio", wav, "--outfile", os.path.join(CACHE, "dummy.mp4"),
                            "--box", str(BOX[box_key][0]), str(BOX[box_key][1]),
                            str(BOX[box_key][2]), str(BOX[box_key][3])],
                           cwd=W2L, env=env, capture_output=True, text=True)
        if r.returncode != 0:
            last_err = "Wav2Lip rc=%d\nSTDOUT:\n%s\nSTDERR:\n%s" % (
                r.returncode, r.stdout[-1200:], r.stderr[-1200:])
            print("  [retry %d] %s" % (attempt + 1, last_err), flush=True)
            continue
        if not os.path.exists(ravi):
            last_err = "Wav2Lip 未产出 result.avi"
            print("  [retry %d] %s" % (attempt + 1, last_err), flush=True)
            continue
        dur = video_duration(ravi)
        # 校验：对口型结果时长必须与音频基本齐平，否则视为上轮残留/截断
        if dur < needed - 0.6:
            last_err = "Wav2Lip 结果过短 %.2fs（需 %.2fs）" % (dur, needed)
            print("  [retry %d] %s" % (attempt + 1, last_err), flush=True)
            continue
        break
    else:
        raise RuntimeError("Wav2Lip 连续失败：%s" % last_err)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", ravi, "-i", wav,
                    "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                    "-shortest", out_path], check=True)


# ---------------------------------------------------------------- 字幕层
def gen_sub(role, text, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((W - 56, 66), BADGE, font=font(24),
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


# ---------------------------------------------------------------- 弹窗
def build_popup(spec, seg_text, net):
    """返回 (Popup 实例, 行出现时刻列表)。"""
    if not spec:
        return None, []
    if spec.get("image") and spec.get("mode") != "static":
        p = spec["image"]
        path = p if os.path.isabs(p) else os.path.join(ASSETS, p)
        return Popup.from_image(path, width=spec.get("width", 872)), []
    rows = []
    times = []
    for r in spec.get("rows", []):
        color = COLORS.get(r.get("color", "gold"), GOLD)
        rows.append((r.get("no", "·"), r.get("term", ""), r.get("detail", ""),
                     r.get("result", ""), color))
        if "at_sec" in r:
            times.append(float(r["at_sec"]))
        else:
            times.append(calc_time(seg_text, r.get("at", r.get("term", "")), net))
    pop = Popup(spec.get("title", ""), spec.get("sub", ""), spec.get("tag", ""), rows)
    return pop, times


def popup_y(pop, spec):
    """弹窗纵向位置。

    spec 显式给 y 时完全尊重（用于双人镜头把弹窗移到下半部空白，
    避开人物头部）；未给时按默认 176 并用 POPUP_MAX_BOTTOM 兜底不压脸。
    """
    y = spec.get("y")
    if y is not None:
        return max(72, int(y))
    y = 176
    bottom = y + 40 + pop.ph
    if bottom > POPUP_MAX_BOTTOM:
        y = POPUP_MAX_BOTTOM - 40 - pop.ph
    return max(120, y)


# ---------------------------------------------------------------- 尾板
def end_frame(cfg, path):
    img = Image.new("RGBA", (W, H), (16, 21, 28, 255))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([80, 620, 1000, 1300], radius=28, fill=(26, 32, 40, 255),
                        outline=(217, 180, 74, 255), width=3)
    gl = cfg.get("gold_lines", [])
    cl = cfg.get("cream_lines", [])
    for i, t in enumerate(gl):
        d.text((540, 790 + i * 100), t, font=font(64), fill=GOLD4, anchor="mm")
    for i, t in enumerate(cl):
        d.text((540, 1030 + i * 80), t, font=font(42), fill=CREAM, anchor="mm")
    if cfg.get("cta"):
        d.text((540, 1420), cfg["cta"], font=font(36), fill=(200, 205, 210, 255), anchor="mm")
    for i, t in enumerate(cfg.get("disclaimer", [])):
        d.text((540, 1660 + i * 45), t, font=font(26), fill=(150, 158, 168, 255), anchor="mm")
    img.convert("RGB").save(path)


def silence(path, seconds=3.5):
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(b"\x00\x00" * int(44100 * seconds))


# ---------------------------------------------------------------- 主流程
def main():
    global BADGE
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--only", type=int, help="只跑第 N 段（调试用）")
    ap.add_argument("--out", help="输出路径（覆盖 spec.output）")
    ap.add_argument("--no-lipsync", action="store_true", help="跳过对口型（调试用）")
    ap.add_argument("--no-cache", action="store_true", help="忽略配音/对口型缓存")
    ap.add_argument("--fps", type=int, default=25)
    args = ap.parse_args()

    spec = json.load(open(args.spec, encoding="utf-8"))
    BADGE = spec.get("badge", BADGE)
    out_path = args.out or spec.get("output") or os.path.join(TMP, "episode.mp4")
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(BIN, exist_ok=True)
    if not os.path.exists(os.path.join(BIN, "ffmpeg")):
        os.symlink(FFMPEG, os.path.join(BIN, "ffmpeg"))

    segs = spec["segments"]
    if args.only:
        segs = [segs[args.only - 1]]

    run_dir = os.path.join(TMP, "run_%s" % uuid.uuid4().hex[:8])
    os.makedirs(run_dir, exist_ok=True)
    seg_files, total_s = [], 0.0

    for i, seg in enumerate(segs, 1):
        role = seg["role"]
        text = seg["text"]
        shot = seg.get("shot", "MASTER")
        box = seg.get("box", "M")
        rate = seg.get("rate") or DEFAULT_RATE.get(role, "-8%")
        tag = hashlib.md5(("%s|%s|%s" % (text, role, rate)).encode()).hexdigest()[:12]

        wav = os.path.join(run_dir, "a%02d.wav" % i)
        sub = os.path.join(run_dir, "s%02d.png" % i)
        lip = os.path.join(CACHE, "lip_%s.mp4" % tag)
        mp4 = os.path.join(run_dir, "x%02d.mp4" % i)
        composed = os.path.join(run_dir, "y%02d.mp4" % i)

        net, total = tts(text, role, rate, wav, tag, use_cache=not args.no_cache)
        gen_sub(role, text, sub)
        if args.no_lipsync:
            src = prepare_loop_video(shot, total + 0.5, os.path.join(run_dir, "loop%02d.mp4" % i))
            subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                            "-i", src, "-i", wav, "-c:v", "libx264", "-preset", "veryfast",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                            "-ar", "44100", "-ac", "2", "-shortest", mp4], check=True)
        else:
            lipsync(shot, wav, box, lip, use_cache=not args.no_cache)
            shutil_copy(lip, mp4)

        pop, times = build_popup(seg.get("popup"), text, net)
        popup_spec = seg.get("popup") or {}
        static = popup_spec.get("mode") == "static"
        if pop is not None and not static:
            frames_dir = os.path.join(run_dir, "pop%02d" % i)
            os.makedirs(frames_dir, exist_ok=True)
            n = int(total * args.fps) + 3
            for k in range(n):
                pop.frame(k / args.fps, times).save(
                    os.path.join(frames_dir, "pop_%04d.png" % (k + 1)))
            x0 = (W - pop.reg_w) // 2
            y0 = popup_y(pop, popup_spec)
            fc = ("[0:v]delogo=x=6:y=6:w=150:h=54,"
                  "scale=1080:1620:force_original_aspect_ratio=decrease,"
                  "pad=1080:1920:0:150:color=black[bg];"
                  "[2:v]format=rgba[pop];"
                  "[bg][pop]overlay=%d:%d:eof_action=pass[wp];"
                  "[wp][1:v]overlay=0:0[final]") % (x0, y0)
            inp = [FFMPEG, "-y", "-loglevel", "error", "-i", mp4, "-loop", "1", "-i", sub,
                   "-framerate", str(args.fps), "-i", os.path.join(frames_dir, "pop_%04d.png")]
        elif static:
            card = popup_spec["image"]
            card = card if os.path.isabs(card) else os.path.join(ASSETS, card)
            cw = int(popup_spec.get("width", 760))
            cy = int(popup_spec.get("y", 130))
            ct = float(popup_spec.get("at", 0.25))
            fc = ("[0:v]delogo=x=6:y=6:w=150:h=54,"
                  "scale=1080:1620:force_original_aspect_ratio=decrease,"
                  "pad=1080:1920:0:150:color=black[bg];"
                  "[2:v]scale=%d:-1,format=rgba,fade=in:st=%.2f:d=0.35:alpha=1[card];"
                  "[bg][card]overlay=130:%d:enable='gte(t,%.2f)'[wp];"
                  "[wp][1:v]overlay=0:0[final]") % (cw, ct, cy, ct)
            inp = [FFMPEG, "-y", "-loglevel", "error", "-i", mp4, "-loop", "1", "-i", sub,
                   "-loop", "1", "-i", card]
        else:
            fc = ("[0:v]delogo=x=6:y=6:w=150:h=54,"
                  "scale=1080:1620:force_original_aspect_ratio=decrease,"
                  "pad=1080:1920:0:150:color=black[bg];"
                  "[bg][1:v]overlay=0:0[final]")
            inp = [FFMPEG, "-y", "-loglevel", "error", "-i", mp4, "-loop", "1", "-i", sub]

        inp += ["-filter_complex", fc, "-map", "[final]", "-map", "0:a",
                "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                "-r", str(args.fps), "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                "-ac", "2", "-shortest", composed]
        subprocess.run(inp, check=True)
        seg_files.append(composed)
        total_s += total
        extra = ""
        if pop is not None:
            extra = " popup[%s]@%s" % (len(times), ",".join("%.2f" % t for t in times))
        print("seg %02d  %5.2fs  %-4s %-8s%s" % (i, total, role, shot, extra), flush=True)

    if not args.only:
        wav = os.path.join(run_dir, "a99.wav")
        png = os.path.join(run_dir, "f99.png")
        mp4 = os.path.join(run_dir, "x99.mp4")
        silence(wav)
        end_frame(spec.get("end_card", {}), png)
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-loop", "1", "-framerate", "25",
                        "-i", png, "-i", wav, "-c:v", "libx264", "-preset", "veryfast",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                        "-ar", "44100", "-ac", "2", "-shortest", mp4], check=True)
        seg_files.append(mp4)
        total_s += 3.5

    lst = os.path.join(run_dir, "list.txt")
    with open(lst, "w") as f:
        for p in seg_files:
            f.write("file '%s'\n" % p)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", out_path], check=True)
    print("DONE %s  %.1fs  %.1fMB" % (out_path, total_s,
                                      os.path.getsize(out_path) / 1048576), flush=True)
    if args.only:
        print("TEST", os.path.join(run_dir, "y%02d.mp4" % args.only))


def shutil_copy(src, dst):
    import shutil
    shutil.copyfile(src, dst)


if __name__ == "__main__":
    main()
