# -*- coding: utf-8 -*-
"""灵动思考弹窗渲染器：弹性入场 + 持续浮动 + 呼吸光晕 + 思考点 + 知识点逐条弹入。"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
GOLD = (240, 205, 130)
TEAL = (150, 226, 216)
CREAM = (238, 234, 224)
GRAY = (150, 160, 172)

PW = 872          # 气泡宽度
G = 40            # 光晕外扩
RADIUS = 34
TAIL_H = 78       # 尾巴（思考点）占用高度


def F(sz):
    return ImageFont.truetype(FONT, sz, index=0)


def clamp01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def ease_out_back(t, s=1.7):
    t = clamp01(t)
    return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2


def _grad(w, h, top, bottom):
    img = Image.new("RGB", (1, h))
    px = img.load()
    for y in range(h):
        k = y / max(1, h - 1)
        px[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3))
    return img.resize((w, h), Image.Resampling.BILINEAR)


class Popup:
    """一个可逐帧渲染的思考弹窗。

    rows: [(编号, 术语, 说明, 结论, 配色)]，术语说话时才弹入。
    """

    def __init__(self, title, sub, tag, rows):
        self.title, self.sub, self.tag, self.rows = title, sub, tag, rows
        self.is_image = False
        self.pw = PW
        self.head_h = 156
        self.row_h = 100
        self.gap = 14
        self.pad_b = 30
        n = max(1, len(rows))
        self.ph = self.head_h + n * self.row_h + (n - 1) * self.gap + self.pad_b
        self.bh = self.ph + TAIL_H
        self.iw = self.pw - 72
        self.body = self._build_body()
        self.row_imgs = [self._build_row(r) for r in rows]
        self.cw, self.ch = self.pw + 2 * G, self.bh + 2 * G
        self.glow = self._build_glow()
        self.reg_w, self.reg_h = self.cw + 80, self.ch + 118

    @classmethod
    def from_image(cls, path, width=PW):
        """整张静态卡片（如排盘表）也套上同一套弹性/浮动/光晕动效。"""
        obj = cls.__new__(cls)
        img = Image.open(path).convert("RGBA")
        sc = width / img.width
        img = img.resize((width, max(1, int(img.height * sc))), Image.Resampling.LANCZOS)
        obj.title = obj.sub = obj.tag = ""
        obj.rows = []
        obj.is_image = True
        obj.pw = width
        obj.ph = img.height
        obj.bh = obj.ph
        obj.head_h = obj.row_h = obj.gap = obj.pad_b = 0
        obj.iw = width
        obj.body = img
        obj.row_imgs = []
        obj.cw, obj.ch = obj.pw + 2 * G, obj.bh + 2 * G
        obj.glow = obj._build_glow()
        obj.reg_w, obj.reg_h = obj.cw + 80, obj.ch + 118
        return obj

    # ---------- 静态部件 ----------
    def _build_body(self):
        w, h = self.pw, self.ph
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=RADIUS, fill=255)

        grad = _grad(w, h, (30, 39, 49), (16, 22, 29)).convert("RGBA")
        # 顶部高光
        hl = Image.new("RGBA", (w, 130), (255, 255, 255, 0))
        hd = ImageDraw.Draw(hl)
        for i in range(130):
            hd.line([(0, i), (w, i)], fill=(255, 250, 236, int(16 * (1 - i / 130))))
        body = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        body.paste(grad, (0, 0), mask)
        body.alpha_composite(Image.composite(hl, Image.new("RGBA", (w, 130), (0, 0, 0, 0)), mask.crop((0, 0, w, 130))))

        d = ImageDraw.Draw(body)
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=RADIUS, outline=(232, 197, 132, 168), width=2)
        d.line([2, 1.5, w - 3, 1.5], fill=(255, 246, 226, 90), width=1)

        # 标题
        d.text((146, 54), self.title, font=F(42), fill=(246, 224, 178), anchor="lm")
        # 标签
        if self.tag:
            tw = d.textlength(self.tag, font=F(21))
            bx1 = w - 34
            bx0 = bx1 - tw - 34
            d.rounded_rectangle([bx0, 33, bx1, 75], radius=12,
                                fill=(52, 44, 27, 235), outline=(210, 176, 104, 200), width=1)
            d.text(((bx0 + bx1) / 2, 54), self.tag, font=F(21), fill=(238, 202, 126), anchor="mm")
        # 副标题
        d.text((36, 108), self.sub, font=F(25), fill=(170, 180, 192), anchor="lm")
        # 分隔线（平滑渐变，两端淡出）
        x0, x1 = 36, w - 36
        n = x1 - x0
        xs = np.linspace(0.0, 1.0, n)
        aa = (np.sin(np.pi * xs) ** 0.55 * 215).astype(np.uint8)
        line = Image.new("RGBA", (n, 2), (230, 196, 126, 255))
        line.putalpha(Image.fromarray(np.repeat(aa[None, :], 2, axis=0), "L"))
        body.alpha_composite(line, (x0, 147))
        return body

    def _build_glow(self):
        w, h = self.cw, self.ch
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).rounded_rectangle([G, G, G + self.pw, G + self.ph], radius=RADIUS, fill=225)
        m2 = m.filter(ImageFilter.GaussianBlur(18))
        m3 = m.filter(ImageFilter.GaussianBlur(44))
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        glow.paste(Image.new("RGBA", (w, h), (255, 214, 148) + (255,)), (0, 0), m2)
        glow.paste(Image.new("RGBA", (w, h), (232, 176, 88) + (255,)), (0, 0), m3.point(lambda v: v * 3 // 5))
        return glow

    def _build_row(self, row):
        no, term, detail, result, color = row
        w, h = self.iw, self.row_h
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        cy = h // 2
        # 编号徽章
        d.rounded_rectangle([0, cy - 29, 58, cy + 29], radius=19,
                            fill=color + (26,), outline=color + (210,), width=2)
        d.text((29, cy), no, font=F(30), fill=color + (255,), anchor="mm")
        # 术语
        tx = 78
        d.text((tx, cy - 2), term, font=F(38), fill=color + (255,), anchor="lm")
        tw = d.textlength(term, font=F(38))
        # 说明
        d.text((tx + tw + 16, cy + 1), "· " + detail, font=F(25), fill=GRAY + (255,), anchor="lm")
        # 结论 chips
        cw_ = d.textlength(result, font=F(24)) + 36
        cx1 = w
        d.rounded_rectangle([cx1 - cw_, cy - 24, cx1, cy + 24], radius=14,
                            fill=color + (24,), outline=color + (150,), width=1)
        d.text((cx1 - cw_ / 2, cy), result, font=F(24), fill=(242, 238, 228, 255), anchor="mm")
        return img

    # ---------- 逐帧 ----------
    def row_y(self, k):
        return self.head_h + k * (self.row_h + self.gap)

    def frame(self, t, row_times, appear=0.22):
        # 整体弹性入场
        dt = t - appear
        p = ease_out_back(min(1.0, dt / 0.70), 1.45)
        scale = 0.64 + 0.36 * p
        rot = -4.2 * (1 - p)
        alpha = clamp01(dt / 0.30)

        # 每条知识点出现时给整体一个轻微回弹
        for tk in row_times:
            u = t - tk
            if 0 < u < 1.2:
                scale *= 1 + 0.016 * math.exp(-u * 5.2) * math.sin(u * 24)
        bob = 3.4 * math.sin(2 * math.pi * 0.32 * t) if dt > 0.8 else 0.0

        content = Image.new("RGBA", (self.cw, self.ch), (0, 0, 0, 0))
        # 呼吸光晕
        ga = int(96 + 34 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.45 * t)))
        glow = self.glow.copy()
        glow.putalpha(glow.split()[3].point(lambda v: v * ga // 255))
        content.alpha_composite(glow)
        if not self.is_image:
            self._draw_tail(content, t)
        content.alpha_composite(self.body, (G, G))

        # 思考点（三个跳动的点）
        if not self.is_image:
            self._draw_dots(content, t, row_times[0] if row_times else 1e9)

        # 未说到的知识点：留一个呼吸占位，避免大片空白像缺内容
        for k in range(len(self.row_imgs)):
            if k < len(row_times) and t > row_times[k]:
                continue
            self._draw_pending(content, k, t)

        # 知识点逐条弹入
        for k, img in enumerate(self.row_imgs):
            if k >= len(row_times):
                break
            dtt = t - row_times[k]
            if dtt <= 0:
                continue
            pp = ease_out_back(min(1.0, dtt / 0.42), 2.6)
            sc = 0.82 + 0.18 * pp
            a = clamp01(dtt / 0.14)
            w = max(1, int(self.iw * sc))
            h = max(1, int(self.row_h * sc))
            rr = img.resize((w, h), Image.Resampling.LANCZOS)
            if dtt < 0.62:  # 扫光
                rr = self._sweep(rr, dtt / 0.62)
            rr.putalpha(rr.split()[3].point(lambda v: int(v * a)))
            x = G + 36 + (self.iw - w) // 2
            y = G + self.row_y(k) + int(12 * (1 - pp)) + (self.row_h - h) // 2
            content.alpha_composite(rr, (x, y))

        # 变换（缩放 + 旋转）
        bsz = (max(1, int(self.cw * scale)), max(1, int(self.ch * scale)))
        big = content.resize(bsz, Image.Resampling.LANCZOS)
        if abs(rot) > 0.05:
            big = big.rotate(rot, resample=Image.Resampling.BICUBIC, expand=True)
        if alpha < 1.0:
            big.putalpha(big.split()[3].point(lambda v: int(v * alpha)))

        out = Image.new("RGBA", (self.reg_w, self.reg_h), (0, 0, 0, 0))
        out.alpha_composite(big, ((self.reg_w - big.width) // 2,
                                 (self.reg_h - big.height) // 2 + int(bob)))
        return out

    def _draw_pending(self, canvas, k, t):
        """等待中的知识点占位：淡框 + 呼吸三点。"""
        color = self.rows[k][4] if k < len(self.rows) else GOLD
        cy = G + self.row_y(k) + self.row_h // 2
        x = G + 36
        w = self.iw
        a = 42 + 26 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.8 * t))
        d = ImageDraw.Draw(canvas)
        d.rounded_rectangle([x, cy - 30, x + w, cy + 30], radius=16,
                            outline=color + (int(a),), width=2)
        for i in range(3):
            ax = x + w / 2 - 28 + i * 28
            ph = 0.5 + 0.5 * math.sin(2 * math.pi * 1.1 * t - i * 0.6)
            r = 4 + 1.6 * ph
            d.ellipse([ax - r, cy - r, ax + r, cy + r],
                      fill=color + (int(min(255, a + 60 + 60 * ph)),))

    def _draw_tail(self, canvas, t):
        """气泡尾巴：三个依次脉冲的小圆点，像念头往上冒。"""
        specs = [(148, 18, 13.0), (124, 44, 9.5), (104, 64, 7.0)]
        for i, (x, dy, r) in enumerate(specs):
            ph = 2 * math.pi * 0.72 * t - i * 1.15
            a = int(150 + 95 * (0.5 + 0.5 * math.sin(ph)))
            rr = r * (1.0 + 0.10 * math.sin(ph))
            d = ImageDraw.Draw(canvas)
            cx, cy = G + x, G + self.ph + dy
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                      fill=(26, 33, 42, min(255, a)), outline=(226, 192, 126, min(255, a)), width=2)

    def _draw_dots(self, canvas, t, first_row_t):
        cy = G + 54
        x0 = G + 52
        waiting = t < first_row_t
        for i in range(3):
            phase = 1.9 * t + i * 0.24
            if waiting:
                dy = -6.5 * abs(math.sin(math.pi * phase))
                a = 235
            else:
                dy = -2.0 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.4 * t + i * 0.5))
                a = int(150 + 60 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.5 * t + i * 0.4)))
            r = 7
            canvas.alpha_composite(
                self._circle(r, GOLD + (a,)), (int(x0 + i * 22 - r), int(cy + dy - r)))

    @staticmethod
    def _circle(r, color):
        img = Image.new("RGBA", (2 * r + 2, 2 * r + 2), (0, 0, 0, 0))
        ImageDraw.Draw(img).ellipse([1, 1, 2 * r, 2 * r], fill=color)
        return img

    @staticmethod
    def _sweep(img, prog):
        arr = np.asarray(img).astype(np.float32)
        w = arr.shape[1]
        cx = -0.35 * w + 1.7 * w * prog
        sigma = w * 0.13
        x = np.arange(w, dtype=np.float32)
        band = (np.exp(-((x - cx) ** 2) / (2 * sigma ** 2)) * 42 * math.sin(math.pi * prog))
        arr[:, :, :3] = np.clip(arr[:, :, :3] + band[None, :, None], 0, 255)
        return Image.fromarray(arr.astype(np.uint8), "RGBA")


def render_sequence(popup, row_times, total, out_dir, fps=25, prefix="pop"):
    import os
    os.makedirs(out_dir, exist_ok=True)
    n = int(math.ceil(total * fps)) + 3
    for i in range(n):
        t = i / fps
        popup.frame(t, row_times).save(os.path.join(out_dir, "%s_%04d.png" % (prefix, i + 1)))
    return n
