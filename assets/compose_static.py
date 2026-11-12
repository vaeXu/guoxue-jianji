import os
import asyncio
import subprocess
import wave
import shutil
import imageio_ffmpeg
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageOps

VOICE_MASTER = "zh-CN-YunjianNeural"   # 老先生
VOICE_VISITOR = "zh-CN-YunxiNeural"    # 命主

BASE = "/Users/xujiahua/WorkBuddy/2026-11-11-17-16-57/assets"
TMP = "/tmp/wb_compose"
OUT = os.path.join(BASE, "sample-static.mp4")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
W, H = 1080, 1920
GOLD = (240, 205, 130, 255)
TEAL = (165, 232, 222, 255)
CREAM = (240, 236, 225, 255)

MASTER = "char-01-master-clean.png"
VISITOR = "char-02-visitor-clean.png"
TWO = "scene-03-two-shot-clean.png"

SEGMENTS = [
    ("命主", "先生，我抄了张老八字，您给看看？", TWO, None, "+2%"),
    ("老先生", "不急着断吉凶。书里这一页，讲的是一个词——多途径做功。", MASTER, None, "-8%"),
    ("老先生", "戊申、己未、癸巳……日主癸水，不靠一条路使劲。", MASTER, "card-01-bazi.png", "-8%"),
    ("命主", "不靠一条路？", VISITOR, None, "+2%"),
    ("老先生", "你看，癸水合年干戊土正官，古籍叫合用——求的是名分、位置。", MASTER, "card-02-liuxiang.png", "-8%"),
    ("老先生", "同时，日支巳火财星合制申金劫财，这叫制用——靠团队和手艺拿实在资源。", MASTER, "card-02-liuxiang.png", "-8%"),
    ("老先生", "一个管名，一个管利，两条线一起走。古籍说这种人心性复杂、舞台广，不肯只待在一个角色里。", MASTER, None, "-8%"),
    ("命主", "那……还有别的走法吗？", VISITOR, None, "+2%"),
    ("老先生", "有。书里另举一位数学家：亥水食神暗合午火官星，叫制官；两个亥水又入辰土印库，叫墓用。", MASTER, "card-03-muyong.png", "-8%"),
    ("老先生", "先以思想取得荣誉，再把成果汇进学术机构。先拿本事，再建体系。", MASTER, "card-03-muyong.png", "-8%"),
    ("命主", "所以这页书……", TWO, None, "+2%"),
    ("老先生", "所以最妙的不是算准了什么，是把人怎么调动资源、怎么把才华沉淀下来，画成了一张图。", TWO, None, "-8%"),
]


def font(size):
    return ImageFont.truetype(FONT, size, index=0)


def wrap(text, n=19):
    return [text[i:i + n] for i in range(0, len(text), n)]


async def _edge_tts(text, voice, rate, mp3_path):
    c = edge_tts.Communicate(text, voice, rate=rate)
    await c.save(mp3_path)


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
        raise RuntimeError("empty TTS output at segment %d" % i)
    pad = b"\x00\x00" * 14700
    with wave.open(wav_path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(frames + pad)
    return (len(frames + pad) / 2) / 44100


def make_frame(role, text, img_name, card_name, path):
    bg = Image.open(os.path.join(BASE, img_name)).convert("RGB")
    bg = ImageOps.fit(bg, (W, H), method=Image.Resampling.LANCZOS)
    if card_name:
        shifted = Image.new("RGBA", (W, H), (14, 18, 24, 255))
        shifted.paste(bg.convert("RGBA"), (0, 130))
        bg = shifted
    veil = Image.new("RGBA", (W, H), (6, 9, 14, 95))
    bg = Image.alpha_composite(bg.convert("RGBA"), veil)
    d = ImageDraw.Draw(bg)
    d.text((W - 56, 66), "古籍情景演绎 · 非真人测算", font=font(24),
           fill=(178, 182, 188, 230), anchor="ra")
    if card_name:
        card = Image.open(os.path.join(BASE, card_name)).convert("RGBA")
        cw = 820
        ch = int(card.height * cw / card.width)
        card = card.resize((cw, ch), Image.Resampling.LANCZOS)
        bg.alpha_composite(card, ((W - cw) // 2, 140))
    lines = wrap(text, 19)[:4]
    box_h = 130 + len(lines) * 66
    top = 1840 - box_h
    d.rounded_rectangle([40, top, 1040, 1840], radius=20, fill=(10, 14, 20, 232))
    accent = GOLD if role == "老先生" else TEAL
    d.rounded_rectangle([70, top + 28, 210, top + 76], radius=8, fill=(38, 44, 54, 255))
    d.text((140, top + 52), role, font=font(26), fill=accent, anchor="mm")
    for i, line in enumerate(lines):
        d.text((70, top + 112 + i * 66), line, font=font(44), fill=CREAM, anchor="lm")
    bg.convert("RGB").save(path)


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
    frames = b"\x00\x00" * int(44100 * seconds)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(frames)


def main():
    if os.path.exists(TMP):
        shutil.rmtree(TMP)
    os.makedirs(TMP)
    seg_files = []
    total = 0.0
    for i, (role, text, img_name, card_name, rate) in enumerate(SEGMENTS, 1):
        wav = os.path.join(TMP, "a%02d.wav" % i)
        png = os.path.join(TMP, "f%02d.png" % i)
        mp4 = os.path.join(TMP, "s%02d.mp4" % i)
        dur = tts(text, role, rate, wav, i)
        make_frame(role, text, img_name, card_name, png)
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-loop", "1", "-framerate", "25",
                        "-i", png, "-i", wav, "-c:v", "libx264", "-preset", "veryfast",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                        "-ar", "44100", "-ac", "2", "-shortest", mp4], check=True)
        seg_files.append(mp4)
        total += dur
        print("seg %02d  %5.2fs  %s" % (i, dur, role), flush=True)

    wav = os.path.join(TMP, "a99.wav")
    png = os.path.join(TMP, "f99.png")
    mp4 = os.path.join(TMP, "s99.mp4")
    silence(wav)
    end_frame(png)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-loop", "1", "-framerate", "25",
                    "-i", png, "-i", wav, "-c:v", "libx264", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                    "-ar", "44100", "-ac", "2", "-shortest", mp4], check=True)
    seg_files.append(mp4)
    total += 3.5

    lst = os.path.join(TMP, "list.txt")
    with open(lst, "w") as f:
        for p in seg_files:
            f.write("file '%s'\n" % p)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", OUT], check=True)
    print("DONE", OUT, "approx %.1fs" % total, os.path.getsize(OUT), "bytes", flush=True)


if __name__ == "__main__":
    main()
