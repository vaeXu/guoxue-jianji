import os
import sys
import asyncio
import subprocess
import wave
import shutil
import imageio_ffmpeg
import edge_tts
from PIL import Image, ImageDraw, ImageFont

BASE = "/Users/xujiahua/WorkBuddy/2026-11-11-17-16-57/assets"
TMP = "/tmp/wb_lip"
OUT = os.path.join(BASE, "sample-lipsync.mp4")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
W, H = 1080, 1920
GOLD = (240, 205, 130, 255)
TEAL = (165, 232, 222, 255)
CREAM = (240, 236, 225, 255)

VM = os.path.join(BASE, "videos", "master.mp4")
VV = os.path.join(BASE, "videos", "visitor.mp4")
VT = os.path.join(BASE, "videos", "two.mp4")
VIDEO_MAP = {"MASTER": VM, "VISITOR": VV, "TWO": VT}

W2L_DIR = os.path.join(BASE, "wav2lip")
CKPT = os.path.join(W2L_DIR, "checkpoints", "wav2lip_gan.pth")
TMPBIN = os.path.join(BASE, "tmpbin")

# box: (y1, y2, x1, x2) per Wav2Lip --box order
BOX = {
    "M": (390, 575, 210, 370),    # master 老先生
    "V": (370, 625, 390, 555),    # visitor 命主
    "T2M": (195, 360, 205, 335),  # two 中的老先生
    "T2V": (200, 355, 515, 630),  # two 中的命主
}

VOICE_MASTER = "zh-CN-YunjianNeural"
VOICE_VISITOR = "zh-CN-YunxiNeural"

# (role, text, video_key, box_key, rate, layers)
SEGMENTS = [
    ("命主", "先生，我抄了张老八字，您给看看？", "TWO", "T2V", "+2%", []),
    ("老先生", "不急着断吉凶。书里这一页，讲的是一个词——多途径做功。", "MASTER", "M", "-8%",
     [("c2-word.png", "多途径做功", True)]),
    ("老先生", "戊申、己未、癸巳……日主癸水，不靠一条路使劲。", "MASTER", "M", "-8%",
     [("card-01-bazi.png", None, True)]),
    ("命主", "不靠一条路？", "VISITOR", "V", "+2%", []),
    ("老先生", "你看，癸水合年干戊土正官，古籍叫合用——求的是名分、位置。", "MASTER", "M", "-8%",
     [("c2-base.png", None, True), ("c2-row1.png", "合用", True)]),
    ("老先生", "同时，日支巳火财星合制申金劫财，这叫制用——靠团队和手艺拿实在资源。", "MASTER", "M", "-8%",
     [("c2-base.png", None, False), ("c2-row1.png", None, False), ("c2-row2.png", "制用", True)]),
    ("老先生", "一个管名，一个管利，两条线一起走。古籍说这种人心性复杂、舞台广，不肯只待在一个角色里。", "MASTER", "M", "-8%",
     [("c2-base.png", None, False), ("c2-row1.png", None, False), ("c2-row2.png", None, False)]),
    ("命主", "那……还有别的走法吗？", "VISITOR", "V", "+2%", []),
    ("老先生", "有。书里另举一位数学家：亥水食神暗合午火官星，叫制官；两个亥水又入辰土印库，叫墓用。", "MASTER", "M", "-8%",
     [("c3-base.png", None, True), ("c3-row1.png", "制官", True), ("c3-row2.png", "墓用", True)]),
    ("老先生", "先以思想取得荣誉，再把成果汇进学术机构。先拿本事，再建体系。", "MASTER", "M", "-8%",
     [("c3-base.png", None, False), ("c3-row1.png", None, False), ("c3-row2.png", None, False)]),
    ("命主", "所以这页书……", "TWO", "T2V", "+2%", []),
    ("老先生", "所以最妙的不是算准了什么，是把人怎么调动资源、怎么把才华沉淀下来，画成了一张图。", "TWO", "T2M", "-8%", []),
]


def font(size):
    return ImageFont.truetype(FONT, size, index=0)


def wrap(text, n=19):
    return [text[i:i + n] for i in range(0, len(text), n)]


async def _edge_tts(text, voice, rate, mp3_path):
    await edge_tts.Communicate(text, voice, rate=rate).save(mp3_path)


def tts(text, role, rate, wav_path, i):
    voice = VOICE_MASTER if role == "老先生" else VOICE_VISITOR
    mp3 = os.path.join(TMP, "v%02d.mp3" % i)
    asyncio.run(_edge_tts(text, voice, rate, mp3))
    raw = os.path.join(TMP, "v%02d.raw.wav" % i)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", mp3,
                    "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", raw], check=True)
    with wave.open(raw, "rb") as f:
        frames = f.readframes(f.getnframes())
    if len(frames) < 22050:
        raise RuntimeError("empty TTS at seg %d" % i)
    pad = 14700
    with wave.open(wav_path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(frames + b"\x00\x00" * pad)
    net = (len(frames) / 2) / 44100
    total = (len(frames) / 2 + pad) / 44100
    return net, total


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
    before = sum(wt(c) for c in text[:idx])
    return dur * before / total


def gen_sub(role, text, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((W - 56, 66), "古籍情景演绎 · 非真人测算", font=font(24),
           fill=(178, 182, 188, 230), anchor="ra")
    lines = wrap(text, 19)[:4]
    box_h = 130 + len(lines) * 66
    top = 1840 - box_h
    d.rounded_rectangle([40, top, 1040, 1840], radius=20, fill=(10, 14, 20, 232))
    accent = GOLD if role == "老先生" else TEAL
    d.rounded_rectangle([70, top + 28, 210, top + 76], radius=8, fill=(38, 44, 54, 255))
    d.text((140, top + 52), role, font=font(26), fill=accent, anchor="mm")
    for i, line in enumerate(lines):
        d.text((70, top + 112 + i * 66), line, font=font(44), fill=CREAM, anchor="lm")
    img.save(path)


def lipsync(video, wav, box, out_path):
    env = os.environ.copy()
    env["PATH"] = TMPBIN + ":" + env.get("PATH", "")
    dummy = os.path.join(TMP, "dummy_out.mp4")
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


def build_filter(text, layers, net):
    parts = ["[0:v]delogo=x=6:y=6:w=150:h=54,"
             "scale=1080:1620:force_original_aspect_ratio=decrease,"
             "pad=1080:1920:0:150:color=black[bg]"]
    cur = "bg"
    for k, (png, term, fade) in enumerate(layers):
        inidx = 2 + k
        T = calc_time(text, term, net)
        lbl = "L%d" % k
        if fade:
            parts.append("[%d:v]scale=820:-1,format=rgba,fade=in:st=%.2f:d=0.35:alpha=1[%s]"
                         % (inidx, T, lbl))
        else:
            parts.append("[%d:v]scale=820:-1,format=rgba[%s]" % (inidx, lbl))
        nxt = "o%d" % (k + 1)
        en = ":enable='gte(t,%.2f)'" % T if T > 0 else ""
        parts.append("[%s][%s]overlay=130:140%s[%s]" % (cur, lbl, en, nxt))
        cur = nxt
    parts.append("[%s][1:v]overlay=0:0[final]" % cur)
    return ";".join(parts)


def end_frame(path):
    img = Image.new("RGBA", (W, H), (16, 21, 28, 255))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([80, 620, 1000, 1300], radius=28, fill=(26, 32, 40, 255),
                        outline=(217, 180, 74, 255), width=3)
    d.text((540, 790), "古籍最有意思的", font=font(64), fill=GOLD, anchor="mm")
    d.text((540, 890), "不是「算准了什么」", font=font(64), fill=GOLD, anchor="mm")
    d.text((540, 1030), "是把才华怎么沉淀成体系", font=font(42), fill=CREAM, anchor="mm")
    d.text((540, 1110), "画成了一张图", font=font(42), fill=CREAM, anchor="mm")
    d.text((540, 1420), "想看更多老断例，评论区告诉我", font=font(36), fill=(200, 205, 210, 255), anchor="mm")
    d.text((540, 1660), "本视频为古籍文本情景演绎，仅作传统文化讨论", font=font(26),
           fill=(150, 158, 168, 255), anchor="mm")
    d.text((540, 1705), "不构成任何人生预测或建议", font=font(26),
           fill=(150, 158, 168, 255), anchor="mm")
    img.convert("RGB").save(path)


def silence(path, seconds=3.5):
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(b"\x00\x00" * int(44100 * seconds))


def main():
    only = os.environ.get("SEG_ONLY")
    if os.path.exists(TMP):
        shutil.rmtree(TMP)
    os.makedirs(TMP)
    os.makedirs(TMPBIN, exist_ok=True)
    fr = os.path.join(TMPBIN, "ffmpeg")
    if not os.path.exists(fr):
        os.symlink(FFMPEG, fr)

    segs = SEGMENTS
    if only:
        segs = [SEGMENTS[int(only) - 1]]
    seg_files = []
    total_s = 0.0
    for i, (role, text, vk, bk, rate, layers) in enumerate(segs, 1):
        wav = os.path.join(TMP, "a%02d.wav" % i)
        sub = os.path.join(TMP, "s%02d.png" % i)
        lip = os.path.join(TMP, "lip%02d.mp4" % i)
        mp4 = os.path.join(TMP, "x%02d.mp4" % i)
        net, total = tts(text, role, rate, wav, i)
        gen_sub(role, text, sub)
        lipsync(VIDEO_MAP[vk], wav, BOX[bk], lip)
        fc = build_filter(text, layers, net)
        inp = [FFMPEG, "-y", "-loglevel", "error", "-i", lip, "-i", sub]
        for png, _t, _f in layers:
            inp += ["-loop", "1", "-i", os.path.join(BASE, png)]
        inp += ["-filter_complex", fc, "-map", "[final]", "-map", "0:a",
                "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                "-r", "25", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                "-shortest", mp4]
        subprocess.run(inp, check=True)
        seg_files.append(mp4)
        total_s += total
        print("seg %02d %5.2fs %s lip=%s" % (i, total, role, os.path.basename(vk)), flush=True)

    if only:
        shutil.copy(seg_files[0], os.path.join(TMP, "test.mp4"))
        print("TEST", os.path.join(TMP, "test.mp4"))
        return

    wav = os.path.join(TMP, "a99.wav")
    png = os.path.join(TMP, "f99.png")
    mp4 = os.path.join(TMP, "x99.mp4")
    silence(wav)
    end_frame(png)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-loop", "1", "-framerate", "25",
                    "-i", png, "-i", wav, "-c:v", "libx264", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                    "-ar", "44100", "-ac", "2", "-shortest", mp4], check=True)
    seg_files.append(mp4)
    total_s += 3.5

    lst = os.path.join(TMP, "list.txt")
    with open(lst, "w") as f:
        for p in seg_files:
            f.write("file '%s'\n" % p)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", OUT], check=True)
    print("DONE", OUT, "approx %.1fs" % total_s, os.path.getsize(OUT), "bytes", flush=True)


if __name__ == "__main__":
    main()
