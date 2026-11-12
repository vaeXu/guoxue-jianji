from PIL import Image, ImageDraw, ImageFont
import math
import os

FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
OUT = "/Users/xujiahua/WorkBuddy/2026-11-11-17-16-57/assets"

GOLD = (217, 180, 74, 255)
TEAL = (111, 211, 199, 255)
CREAM = (240, 234, 220, 255)
GRAY = (150, 160, 172, 255)
PANEL = (18, 24, 31, 246)
ROW = (32, 41, 52, 255)
DIV = (80, 70, 45, 255)


def f(size):
    return ImageFont.truetype(FONT, size, index=0)


def base(w, h, title, sub, tag):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([16, 16, w - 16, h - 16], radius=28, fill=PANEL, outline=GOLD, width=3)
    d.text((w // 2, 66), title, font=f(48), fill=GOLD, anchor="mm")
    if sub:
        d.text((w // 2, 116), sub, font=f(26), fill=GRAY, anchor="mm")
    d.line([56, 146, w - 56, 146], fill=DIV, width=2)
    d.rounded_rectangle([w - 190, 30, w - 40, 68], radius=10, fill=(40, 34, 22, 255), outline=GOLD, width=1)
    d.text((w - 115, 49), tag, font=f(22), fill=GOLD, anchor="mm")
    return img, d


def chip(d, x, y, w, h, text, accent, size=30, fg=CREAM):
    d.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=ROW, outline=accent, width=2)
    d.text((x + w // 2, y + h // 2), text, font=f(size), fill=fg, anchor="mm")


def arrow(d, x1, y1, x2, y2, color, label=None):
    d.line([x1, y1, x2, y2], fill=color, width=4)
    a = math.atan2(y2 - y1, x2 - x1)
    L = 13
    p1 = (x2 - L * math.cos(a - 0.5), y2 - L * math.sin(a - 0.5))
    p2 = (x2 - L * math.cos(a + 0.5), y2 - L * math.sin(a + 0.5))
    d.polygon([(x2, y2), p1, p2], fill=color)
    if label:
        d.text(((x1 + x2) / 2, y1 - 26), label, font=f(24), fill=color, anchor="mm")


def flow_row(d, y, no, left, rel, mid, right, accent):
    d.text((56, y - 38), no, font=f(30), fill=accent, anchor="lm")
    chip(d, 56, y, 240, 90, left, accent)
    arrow(d, 306, y + 45, 386, y + 45, accent, rel)
    chip(d, 396, y, 270, 90, mid, accent)
    arrow(d, 676, y + 45, 756, y + 45, accent)
    chip(d, 766, y, 258, 90, right, accent, size=27)


# ---------- card 1: 八字排盘 ----------
w, h = 1080, 760
img, d = base(w, h, "乾造 · 1908-08-06", "时象台命盘口径 · 八字（节气口径）", "古籍断例 ①")
cols = [(165, "年柱", "戊", "申"), (405, "月柱", "己", "未"),
        (645, "日柱", "癸", "巳"), (885, "时柱", "丙", "辰")]
for cx, name, gan, zhi in cols:
    d.rounded_rectangle([cx - 100, 190, cx + 100, 480], radius=16, fill=ROW, outline=(70, 84, 98, 255), width=2)
    d.text((cx, 224), name, font=f(28), fill=TEAL if name == "日柱" else GRAY, anchor="mm")
    d.line([cx - 62, 250, cx + 62, 250], fill=(70, 84, 98, 255), width=1)
    d.text((cx, 315), gan, font=f(74), fill=TEAL if name == "日柱" else CREAM, anchor="mm")
    d.text((cx, 415), zhi, font=f(74), fill=CREAM, anchor="mm")
d.rounded_rectangle([56, 530, 1024, 620], radius=16, fill=(30, 38, 48, 255), outline=GOLD, width=2)
d.text((540, 575), "日主 癸水 · 通过多种途径做功", font=f(38), fill=GOLD, anchor="mm")
d.text((540, 680), "排盘取自素材图 1；做功关系只涉年干、日主、日支、年支，不涉时柱", font=f(23), fill=GRAY, anchor="mm")
img.save(os.path.join(OUT, "card-01-bazi.png"))

# ---------- card 2: 本例做功流向 ----------
w, h = 1080, 900
img, d = base(w, h, "多途径做功 · 本例", "戊申 己未 癸巳 丙辰 ｜ 合用 + 制用", "古籍断例 ②")
flow_row(d, 230, "① 合用 · 求名分与位置", "癸水 · 日主", "合", "戊土 · 正官", "合用：名 / 位置", GOLD)
flow_row(d, 450, "② 制用 · 拿实际资源", "巳火 · 财星", "合制", "申金 · 劫财", "制用：利 / 资源", TEAL)
d.line([56, 590, 1024, 590], fill=DIV, width=2)
d.text((540, 626), "一个管名，一个管利 · 两条线同时走", font=f(30), fill=GRAY, anchor="mm")
d.rounded_rectangle([240, 666, 840, 776], radius=18, fill=(40, 34, 22, 255), outline=GOLD, width=2)
d.text((540, 721), "多 途 径 做 功", font=f(52), fill=GOLD, anchor="mm")
d.text((540, 830), "古籍说法：心性复杂、能力全面，不满足于单一角色或领域", font=f(24), fill=GRAY, anchor="mm")
img.save(os.path.join(OUT, "card-02-liuxiang.png"))

# ---------- card 3: 制用 + 墓用 ----------
w, h = 1080, 880
img, d = base(w, h, "另一种复合 · 制用 + 墓用", "案例 壬午 辛亥 庚辰 丁亥 ｜ 作者解读：数学家", "古籍断例 ③")
flow_row(d, 225, "① 制官 · 以思想取荣誉", "亥水 · 食神", "暗合", "午火 · 官星", "制官：荣誉", GOLD)
flow_row(d, 445, "② 墓用 · 成果沉淀", "亥水 · 食神", "入", "辰土 · 印库", "墓用：体系", TEAL)
d.line([56, 585, 1024, 585], fill=DIV, width=2)
d.rounded_rectangle([180, 620, 900, 730], radius=18, fill=(40, 34, 22, 255), outline=GOLD, width=2)
d.text((540, 675), "先拿本事，再建体系", font=f(48), fill=GOLD, anchor="mm")
d.text((540, 790), "以思想获取荣誉，其思想成果汇于学术机构", font=f(26), fill=GRAY, anchor="mm")
img.save(os.path.join(OUT, "card-03-muyong.png"))

print("cards written to", OUT)
