"""Series-specific reel scenes (added 2026-11-25).

Each series gets its own look instead of the shared navy page:
  receipt   -> The Season Ledger: thermal receipt printing line by line on paper, running
               SEASON TO DATE counter that carries across episodes.
  dashboard -> 4 AM Club: night windshield + road, glowing dashboard clock that ticks to
               each timestamp, log of the morning stacking above.
  split     -> Debate Night: two-column split (red vs blue), points land alternately.
  fieldguide-> Rink Field Guide: cream naturalist card on topo-green, drawn icon, entries + FIELD NOTE stamp (2026-11-26).

Usage: python3 scenes.py spec.json outdir
Everything is drawn programmatically (PIL); music is original (lib.make_music).
"""
import os, sys, json, math, random, subprocess, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from lib import *

W, H, FPS = 1080, 1920, 30
X = 96
COVER_SECS = 0.4
INK = (34, 30, 28)
PAPER = (246, 242, 232)
BLUE = (58, 120, 214)
TEAL = (110, 236, 214)


# ---------------------------------------------------------------- helpers
def vgrad(w, h, top, bot):
    y = np.linspace(0, 1, h)[:, None, None]
    a = np.array(top, float)[None, None, :]
    b = np.array(bot, float)[None, None, :]
    arr = (a + (b - a) * y) * np.ones((1, w, 1))
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGB")


def noise_overlay(img, amount=10, seed=0):
    rnd = np.random.default_rng(seed)
    arr = np.asarray(img).astype(np.int16)
    n = rnd.normal(0, amount, arr.shape[:2])[..., None]
    return Image.fromarray((arr + n).clip(0, 255).astype(np.uint8), "RGB")


def fit_size(fpath, lines, maxw, start, minimum):
    size = start
    while size > minimum and max(font(fpath, size).getlength(s) for s in lines) > maxw:
        size -= 4
    return size


def cover_card(bg, kicker, lines, sub=None, color=WHITE, kcolor=RED, scolor=SLATE, panel=None):
    """Frame-0 title card (Facebook thumbnail). Optional dark panel for busy backgrounds."""
    img = bg.copy().convert("RGBA")
    size = fit_size(ANTON, lines, W - 2 * X, 190, 110)
    hf = font(ANTON, size)
    lh = int(size * 1.03)
    block = len(lines) * lh
    y0 = (H - block) // 2 - 60
    if panel:
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(ov).rounded_rectangle([50, y0 - 160, W - 50, y0 + block + 190], 36, fill=panel)
        img.alpha_composite(ov)
    d = ImageDraw.Draw(img)
    d.text((W // 2, y0 - 90), kicker, font=font(INTER_B, 44), fill=kcolor, anchor="ma")
    for i, s in enumerate(lines):
        d.text((W // 2, y0 + i * lh), s, font=hf, fill=color, anchor="ma")
    if sub:
        sf = font(INTER_SB, 48)
        y = y0 + block + 50
        for ln in wrap(sf, sub, W - 2 * X):
            d.text((W // 2, y), ln, font=sf, fill=scolor, anchor="ma")
            y += 62
    return img.convert("RGB")


def typed(s, t, start, cps=38):
    """Typewriter reveal of s from time start."""
    n = int(max(0, t - start) * cps)
    return s[:n]


# ---------------------------------------------------------------- RECEIPT (Season Ledger)
def receipt_bg(seed):
    bg = vgrad(W, H, (52, 40, 34), (22, 18, 16))
    # faint counter-top grain
    d = ImageDraw.Draw(bg, "RGBA")
    rnd = random.Random(seed)
    for _ in range(120):
        y = rnd.uniform(0, H)
        d.line([(0, y), (W, y + rnd.uniform(-30, 30))], fill=(255, 220, 180, rnd.randint(3, 9)), width=rnd.randint(1, 3))
    return noise_overlay(bg, 5, seed)


PX0, PX1 = 70, W - 70  # paper edges


def paper_layer(top, bottom, seed):
    """Paper strip with zigzag torn bottom edge and soft shadow."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pts = [(PX0, top), (PX1, top)]
    x = PX1
    zig = 18
    up = True
    while x > PX0:
        x2 = max(PX0, x - zig)
        pts.append((x2, bottom + (0 if up else 14)))
        up = not up
        x = x2
    ImageDraw.Draw(sh).polygon([(px + 10, py + 16) for px, py in pts], fill=(0, 0, 0, 120))
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    ImageDraw.Draw(lay).polygon(pts, fill=PAPER + (255,))
    lay = Image.alpha_composite(sh, lay)
    return lay


def render_receipt(spec, t, bg, paper_cache):
    img = bg.copy().convert("RGBA")
    items = spec["items"]
    t0, step = spec["first"], spec["step"]
    n = len(items)
    # timeline
    sub_t = t0 + n * step                 # subtotal prints
    std_t = sub_t + 1.0                    # season-to-date box
    end_t = std_t + spec.get("hold", 2.6)  # footer
    top = 170
    row = 88
    y_items = top + 290
    y_sub = y_items + n * row + 40
    y_std = y_sub + 120
    full_bottom = y_std + 240
    # paper grows as lines print (feeds out of the printer slot at top)
    # paper feeds out one line at a time, always ahead of the ink
    events = [(t0 - 10, y_items - 10)]
    for i in range(n):
        events.append((t0 + i * step, y_items + (i + 1) * row + 6))
    events.append((sub_t, y_sub + 96))
    events.append((std_t, full_bottom))
    prev, bottom = events[0][1], events[0][1]
    for et, eb in events[1:]:
        if t >= et:
            k = ease((t - et) / 0.25)
            bottom = int(prev + (eb - prev) * k)
            prev = eb
    key = bottom // 6
    if key not in paper_cache:
        paper_cache[key] = paper_layer(top - 40, bottom, spec.get("seed", 1))
    img.alpha_composite(paper_cache[key])
    d = ImageDraw.Draw(img)
    # printer slot
    d.rounded_rectangle([PX0 - 40, top - 70, PX1 + 40, top - 30], 14, fill=(18, 16, 15))
    d.rectangle([PX0 - 10, top - 44, PX1 + 10, top - 36], fill=(5, 5, 5))
    cx = W // 2
    # header on paper
    d.text((cx, top + 6), "THE SEASON LEDGER", font=font(ANTON, 100), fill=INK, anchor="ma")
    d.text((cx, top + 132), spec["episode"], font=font(MONO_M, 36), fill=(110, 100, 92), anchor="ma")
    d.text((cx, top + 196), "-" * 34, font=font(MONO, 36), fill=(150, 140, 130), anchor="ma")
    total = 0.0
    lx, rx = PX0 + 44, PX1 - 44
    for i, it in enumerate(items):
        ti = t0 + i * step
        if t < ti:
            continue
        yy = y_items + i * row
        lab = typed(it["label"], t, ti, cps=60)
        d.text((lx, yy), lab, font=font(MONO_M, 42), fill=INK)
        if t > ti + 0.35:
            d.text((rx, yy), it["price"], font=font(MONO_M, 42), fill=INK, anchor="ra")
            total += it["amt"]
    if t >= sub_t:
        d.text((cx, y_sub - 40), "-" * 34, font=font(MONO, 36), fill=(150, 140, 130), anchor="ma")
        d.text((lx, y_sub + 8), spec["sub_label"], font=font(MONO_M, 44), fill=INK)
        d.text((rx, y_sub), f"${spec['today_total']:,.2f}", font=font(ANTON, 68), fill=INK, anchor="ra")
    if t >= std_t:
        a = ease((t - std_t) / 0.4)
        k = ease((t - std_t - 0.3) / 1.4)
        val = spec["prev_std"] + (spec["new_std"] - spec["prev_std"]) * k
        box = [lx - 10, y_std, rx + 10, y_std + 200]
        d.rectangle(box, outline=RED, width=5)
        d.text((cx, y_std + 18), "SEASON TO DATE", font=font(INTER_B, 38), fill=RED, anchor="ma")
        d.text((cx, y_std + 66), f"${val:,.2f}", font=font(ANTON, 100), fill=RED, anchor="ma")
    # footer (on the counter, below paper)
    if t >= end_t:
        a = ease((t - end_t) / 0.6)
        f = font(INTER_SB, 46)
        y = max(full_bottom + 60, 1500)
        for ln in wrap(f, spec["end"], W - 2 * X):
            draw_text_alpha(img, (X, y), ln, f, WHITE, a, dy=int(16 * (1 - a)))
            y += 60
        a2 = ease((t - end_t - 1.2) / 0.6)
        draw_text_alpha(img, (X, y + 30), spec["follow"], font(INTER_B, 38), RED, a2)
    return img


def receipt_cues(spec):
    items = spec["items"]; t0, step = spec["first"], spec["step"]; n = len(items)
    sub_t = t0 + n * step; std_t = sub_t + 1.0; end_t = std_t + spec.get("hold", 2.6)
    cues = [(0.3, t0 - 0.05, spec["kicker"].title() + ". " + " ".join(spec["head"]).capitalize())]
    for i, it in enumerate(items):
        cues.append((t0 + i * step, t0 + (i + 1) * step, it["cap"]))
    cues.append((sub_t, std_t, f"Today: ${spec['today_total']:,.2f}"))
    cues.append((std_t, end_t, f"Season to date: ${spec['new_std']:,.2f}"))
    cues.append((end_t, spec["duration"] - 0.1, spec["end"]))
    return cues, end_t


# ---------------------------------------------------------------- DASHBOARD (4 AM Club)
def dash_bg(seed):
    img = vgrad(W, H, (6, 9, 20), (20, 26, 48))
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(seed)
    for _ in range(90):
        x, y = rnd.uniform(0, W), rnd.uniform(0, 900)
        r = rnd.choice([1, 1, 1.5, 2])
        d.ellipse([x - r, y - r, x + r, y + r], fill=(220, 230, 255, rnd.randint(60, 180)))
    # horizon glow
    hz = 1010
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([-200, hz - 120, W + 200, hz + 120], fill=(255, 150, 90, 38))
    img = Image.alpha_composite(img.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(40)))
    d = ImageDraw.Draw(img)
    # ground + road
    d.rectangle([0, hz, W, H], fill=(10, 12, 18))
    d.polygon([(W // 2 - 14, hz), (W // 2 + 14, hz), (W + 260, 1420), (-260, 1420)], fill=(30, 32, 40))
    # tree line silhouette
    rnd2 = random.Random(seed + 1)
    x = 0
    pts = [(0, hz)]
    while x < W:
        x += rnd2.uniform(18, 40)
        pts.append((x, hz - rnd2.uniform(8, 46)))
    pts.append((W, hz))
    d.polygon(pts, fill=(8, 10, 16))
    return img.convert("RGB")


def dash_layer():
    """Dashboard panel with clock housing and two gauges (static)."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse([-300, 1330, W + 300, 2500], fill=(16, 16, 20, 255))
    d.rectangle([0, 1520, W, H], fill=(16, 16, 20, 255))
    d.arc([-300, 1330, W + 300, 2500], 190, 350, fill=(48, 48, 56, 255), width=4)
    # clock housing
    d.rounded_rectangle([W // 2 - 250, 1450, W // 2 + 250, 1640], 26, fill=(4, 8, 10, 255), outline=(60, 62, 70, 255), width=3)
    # gauges
    for gx, label in ((170, "OUTSIDE"), (W - 170, "FUEL")):
        d.ellipse([gx - 95, 1470, gx + 95, 1660], outline=(70, 72, 82, 255), width=4)
        d.text((gx, 1625), label, font=font(INTER_B, 20), fill=(120, 124, 138, 255), anchor="ma")
    # fuel needle near E
    cx, cy = W - 170, 1565
    ang = math.radians(215)
    d.line([(cx, cy), (cx + 70 * math.cos(ang), cy - 70 * math.sin(ang))], fill=(236, 90, 60, 255), width=5)
    d.text((cx - 70, 1520), "E", font=font(INTER_B, 24), fill=(236, 90, 60, 255), anchor="ma")
    d.text((cx + 70, 1520), "F", font=font(INTER_B, 24), fill=(140, 140, 150, 255), anchor="ma")
    return lay


def glow_text(img, xy, s, fnt, color, anchor="ma", radius=10):
    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).text(xy, s, font=fnt, fill=color + (200,), anchor=anchor)
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(radius)))
    ImageDraw.Draw(img).text(xy, s, font=fnt, fill=color, anchor=anchor)


def render_dash(spec, t, bg, dash):
    img = bg.copy().convert("RGBA")
    d = ImageDraw.Draw(img)
    # moving road dashes
    hz, bot = 1010, 1420
    speed = 0.9
    for k in range(8):
        p = ((k / 8) + t * speed / 4) % 1.0
        p2 = p + 0.045
        def pt(q):
            q3 = q ** 2.2
            return hz + (bot - hz) * q3, 3 + 18 * q3
        y1, w1 = pt(p); y2, w2 = pt(min(p2, 1))
        d.polygon([(W // 2 - w1, y1), (W // 2 + w1, y1), (W // 2 + w2, y2), (W // 2 - w2, y2)], fill=(210, 190, 120))
    img.alpha_composite(dash)
    items = spec["items"]
    t0, step = spec["first"], spec["step"]
    n = len(items)
    end_t = t0 + n * step
    cur = None
    for i, it in enumerate(items):
        if t >= t0 + i * step:
            cur = i
    clock = items[cur]["time"] if cur is not None else spec["start_clock"]
    if t >= end_t and spec.get("end_clock"):
        clock = spec["end_clock"]
    blink = (t % 1.0) < 0.5
    ck = clock if blink else clock.replace(":", " ")
    glow_text(img, (W // 2, 1478), ck, font(MONO_M, 128), TEAL, radius=12)
    d = ImageDraw.Draw(img)
    d.text((170, 1540), spec.get("temp", "18°F"), font=font(MONO_M, 40), fill=TEAL, anchor="ma")
    # header
    a = ease((t - COVER_SECS) / 0.5)
    draw_text_alpha(img, (X, 120), spec["kicker"], font(INTER_B, 36), RED, a)
    draw_text_alpha(img, (X, 172), spec["title_small"], font(ANTON, 88), WHITE, a)
    # log
    y = 330
    for i, it in enumerate(items):
        ti = t0 + i * step
        if t < ti:
            continue
        aa = ease((t - ti) / 0.4)
        latest = (i == cur) and t < end_t
        dim = 1.0 if latest else 0.55
        if t >= end_t:
            dim = 0.35
        draw_text_alpha(img, (X, y + 4), it["time"], font(MONO_M, 46), TEAL if latest else (150, 170, 190), aa * dim, dy=int(14 * (1 - aa)))
        draw_text_alpha(img, (X + 160, y), it["label"], font(INTER_B, 50), WHITE, aa * dim, dy=int(14 * (1 - aa)))
        if it.get("sub"):
            draw_text_alpha(img, (X + 160, y + 62), it["sub"], font(INTER_M, 38), SLATE, aa * dim, dy=int(14 * (1 - aa)))
        y += 118
    if t >= end_t:
        a = ease((t - end_t) / 0.6)
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(ov).rounded_rectangle([60, y + 6, W - 60, y + 206], 28, fill=(8, 10, 18, int(215 * a)))
        img.alpha_composite(ov)
        f = font(INTER_B, 50)
        yy = y + 40
        for ln in wrap(f, spec["end"], W - 2 * X - 20):
            draw_text_alpha(img, (X, yy), ln, f, WHITE, a, dy=int(16 * (1 - a)))
            yy += 64
        a2 = ease((t - end_t - 1.2) / 0.6)
        draw_text_alpha(img, (W // 2, 1690), spec["follow"], font(INTER_B, 36), RED, a2, anchor="ma")
    return img


def dash_cues(spec):
    items = spec["items"]; t0, step = spec["first"], spec["step"]; n = len(items)
    end_t = t0 + n * step
    cues = [(0.3, t0 - 0.05, spec["kicker"].title() + ". " + " ".join(spec["head"]).capitalize())]
    for i, it in enumerate(items):
        cues.append((t0 + i * step, t0 + (i + 1) * step, it["time"] + ". " + it["cap"]))
    cues.append((end_t, spec["duration"] - 0.1, spec["end"]))
    return cues, end_t


# ---------------------------------------------------------------- SPLIT (Debate Night)
def split_bg(seed):
    left = vgrad(W // 2, H, (70, 18, 24), (28, 8, 12))
    right = vgrad(W - W // 2, H, (16, 34, 74), (8, 14, 32))
    img = Image.new("RGB", (W, H))
    img.paste(left, (0, 0)); img.paste(right, (W // 2, 0))
    img = noise_overlay(img, 4, seed)
    d = ImageDraw.Draw(img)
    d.rectangle([W // 2 - 3, 0, W // 2 + 3, H], fill=(235, 235, 240))
    return img


def render_split(spec, t, bg):
    img = bg.copy().convert("RGBA")
    a = ease((t - COVER_SECS) / 0.5)
    # header band
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle([0, 90, W, 470], fill=(8, 8, 12, 230))
    img.alpha_composite(ov)
    draw_text_alpha(img, (W // 2, 120), spec["kicker"], font(INTER_B, 36), RED, a, anchor="ma")
    size = fit_size(ANTON, spec["question"], W - 2 * 70, 96, 60)
    for i, s in enumerate(spec["question"]):
        draw_text_alpha(img, (W // 2, 180 + i * int(size * 1.05)), s, font(ANTON, size), WHITE, a, anchor="ma")
    colw = W // 2 - 90
    lxs = [60, W // 2 + 30]
    for side, x in enumerate(lxs):
        draw_text_alpha(img, (x + colw // 2, 520), spec["sides"][side], font(ANTON, 72), (255, 255, 255), a, anchor="ma")
    # VS medallion
    d = ImageDraw.Draw(img)
    d.ellipse([W // 2 - 56, 512, W // 2 + 56, 624], fill=(240, 240, 244))
    d.text((W // 2, 538), "VS", font=font(ANTON, 50), fill=(20, 20, 24), anchor="ma")
    t0, step = spec["first"], spec["step"]
    pts = spec["points"]  # list of [side, text]
    ys = [690, 690]
    end_t = t0 + len(pts) * step
    for i, (side, txt) in enumerate(pts):
        ti = t0 + i * step
        if t < ti:
            continue
        aa = ease((t - ti) / 0.45)
        x = lxs[side]
        f = font(INTER_B, 44)
        lines = wrap(f, txt, colw - 10)
        hh = len(lines) * 57 + 40
        card = Image.new("RGBA", img.size, (0, 0, 0, 0))
        col = (255, 255, 255, int(28 * aa))
        ImageDraw.Draw(card).rounded_rectangle([x - 14, ys[side] - 16 + int(20 * (1 - aa)), x + colw + 14, ys[side] + hh - 40 + int(20 * (1 - aa))], 20, fill=col)
        img.alpha_composite(card)
        yy = ys[side]
        for ln in lines:
            draw_text_alpha(img, (x, yy), ln, f, WHITE, aa, dy=int(20 * (1 - aa)))
            yy += 57
        ys[side] += hh + 22
    if t >= end_t:
        a = ease((t - end_t) / 0.6)
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(ov).rectangle([0, 1440, W, 1800], fill=(8, 8, 12, int(235 * a)))
        img.alpha_composite(ov)
        f = font(INTER_SB, 48)
        y = 1490
        for ln in wrap(f, spec["end"], W - 2 * X):
            draw_text_alpha(img, (W // 2, y), ln, f, WHITE, a, dy=int(16 * (1 - a)), anchor="ma")
            y += 62
        a2 = ease((t - end_t - 1.2) / 0.6)
        draw_text_alpha(img, (W // 2, y + 30), spec["follow"], font(INTER_B, 38), RED, a2, anchor="ma")
    return img


def split_cues(spec):
    t0, step = spec["first"], spec["step"]; pts = spec["points"]
    end_t = t0 + len(pts) * step
    cues = [(0.3, t0 - 0.05, spec["kicker"].title() + ". " + " ".join(spec["question"]).capitalize())]
    for i, (side, txt) in enumerate(pts):
        cues.append((t0 + i * step, t0 + (i + 1) * step, spec["sides"][side].title() + ": " + txt))
    cues.append((end_t, spec["duration"] - 0.1, spec["end"]))
    return cues, end_t



# ---------------------------------------------------------------- FIELD GUIDE (Rink Field Guide) — added 2026-11-26
FOREST_T, FOREST_B = (22, 44, 36), (8, 20, 16)
CREAM = (243, 236, 216)
MOSS = (74, 104, 78)
INTER_I = "/usr/share/fonts/opentype/inter/Inter-Italic.otf"


def field_bg(seed):
    """Deep forest green with faint original topo contour lines."""
    img = vgrad(W, H, FOREST_T, FOREST_B).convert("RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rnd = random.Random(seed)
    for c in range(3):
        cx, cy = rnd.uniform(100, W - 100), rnd.uniform(200, H - 200)
        for r in range(60, 1400, 46):
            pts = []
            ph = rnd.uniform(0, 6.28)
            for k in range(73):
                a = k / 72 * 2 * math.pi
                rr = r * (1 + 0.12 * math.sin(3 * a + ph) + 0.05 * math.sin(7 * a + ph * 2))
                pts.append((cx + rr * math.cos(a), cy + rr * 0.8 * math.sin(a)))
            d.line(pts, fill=(160, 200, 170, 14), width=2)
    img.alpha_composite(lay)
    return noise_overlay(img.convert("RGB"), 4, seed)


CARD = (54, 120, W - 54, 1800)


def card_layer(seed):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x0, y0, x1, y1 = CARD
    ImageDraw.Draw(sh).rounded_rectangle([x0 + 8, y0 + 18, x1 + 8, y1 + 18], 30, fill=(0, 0, 0, 140))
    sh = sh.filter(ImageFilter.GaussianBlur(16))
    paper = noise_overlay(vgrad(x1 - x0, y1 - y0, CREAM, (232, 222, 196)), 6, seed)
    mask = Image.new("L", paper.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, paper.size[0] - 1, paper.size[1] - 1], 30, fill=255)
    lay.paste(paper, (x0, y0), mask)
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x0 + 22, y0 + 22, x1 - 22, y1 - 22], 20, outline=MOSS, width=3)
    d.rounded_rectangle([x0 + 32, y0 + 32, x1 - 32, y1 - 32], 16, outline=MOSS + (90,), width=1)
    return Image.alpha_composite(sh, lay)


def draw_toque(size=300, main=(196, 44, 52), band=(240, 232, 214), stripe=(28, 44, 78)):
    """Original illustration: knit winter hat with pom-pom (drawn 3x then downsampled)."""
    S = size * 3
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = S // 2
    # dome
    d.chord([S * 0.16, S * 0.26, S * 0.84, S * 1.02], 180, 360, fill=main)
    # knit ribs on dome
    for k in range(-4, 5):
        x = cx + k * S * 0.07
        d.line([(x, S * 0.64), (cx + k * S * 0.03, S * 0.33)], fill=tuple(int(c * 0.82) for c in main), width=int(S * 0.012))
    # stripe across dome
    d.rectangle([S * 0.17, S * 0.52, S * 0.83, S * 0.58], fill=stripe)
    # cuff
    d.rounded_rectangle([S * 0.12, S * 0.62, S * 0.88, S * 0.80], int(S * 0.04), fill=band)
    for k in range(17):
        x = S * 0.15 + k * S * 0.043
        d.line([(x, S * 0.64), (x, S * 0.78)], fill=(205, 194, 170), width=int(S * 0.01))
    # pom-pom with fuzz
    rnd = random.Random(4)
    pr = S * 0.13
    py = S * 0.22
    d.ellipse([cx - pr, py - pr, cx + pr, py + pr], fill=band)
    for _ in range(140):
        a = rnd.uniform(0, 6.28); r = rnd.uniform(pr * 0.6, pr * 1.08); rr = S * 0.012
        x, y = cx + r * math.cos(a), py + r * math.sin(a)
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=rnd.choice([band, (225, 214, 190), (250, 246, 236)]))
    return im.resize((size, size), Image.LANCZOS)


def render_field(spec, t, bg, card, icon):
    img = bg.copy().convert("RGBA")
    img.alpha_composite(card)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = CARD
    cx = W // 2
    a = ease((t - COVER_SECS) / 0.5)
    draw_text_alpha(img, (cx, y0 + 62), spec["kicker"], font(INTER_B, 34), RED, a, anchor="ma")
    # icon plate
    py = y0 + 270
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.ellipse([cx - 150, py - 150, cx + 150, py + 150], fill=(214, 224, 200, int(255 * a)), outline=MOSS + (int(255 * a),), width=4)
    for k in range(48):
        ang = k / 48 * 2 * math.pi
        rx, ry = cx + 166 * math.cos(ang), py + 166 * math.sin(ang)
        od.ellipse([rx - 3, ry - 3, rx + 3, ry + 3], fill=MOSS + (int(200 * a),))
    img.alpha_composite(ov)
    bob = int(6 * math.sin(t * 2.2))
    ic = icon.copy()
    if a < 1:
        ic.putalpha(ic.getchannel("A").point(lambda v: int(v * a)))
    img.alpha_composite(ic, (cx - icon.size[0] // 2, py - icon.size[1] // 2 + 10 + bob))
    # name
    names = spec["head"]
    size = fit_size(ANTON, names, x1 - x0 - 140, 104, 70)
    y = py + 190
    for s_ in names:
        draw_text_alpha(img, (cx, y), s_, font(ANTON, size), INK, a, anchor="ma")
        y += int(size * 1.02)
    draw_text_alpha(img, (cx, y + 24), spec["latin"], font(INTER_I, 38), MOSS, a, anchor="ma")
    y += 96
    d = ImageDraw.Draw(img)
    d.line([(x0 + 90, y), (x1 - 90, y)], fill=MOSS, width=2)
    y += 34
    # entries
    t0, step = spec["first"], spec["step"]
    ents = spec["entries"]
    end_t = t0 + len(ents) * step
    fade = 1.0 if t < end_t else 1 - ease((t - end_t) / 0.5)  # entries clear for the FIELD NOTE
    tf = font(INTER_SB, 42)
    for i, e in enumerate(ents):
        ti = t0 + i * step
        if t < ti:
            continue
        aa = ease((t - ti) / 0.45) * fade
        draw_text_alpha(img, (x0 + 90, y), e["label"], font(INTER_B, 28), RED, aa, dy=int(12 * (1 - aa)))
        yy = y + 42
        for ln in wrap(tf, e["text"], x1 - x0 - 180):
            draw_text_alpha(img, (x0 + 90, yy), ln, tf, INK, aa, dy=int(12 * (1 - aa)))
            yy += 54
        y = yy + 22
    # field note stamp
    if t >= end_t:
        a2 = ease((t - end_t) / 0.5)
        box_top = 1180
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        od.rounded_rectangle([x0 + 60, box_top, x1 - 60, box_top + 330], 22, fill=(30, 52, 42, int(240 * a2)), outline=RED + (int(255 * a2),), width=5)
        img.alpha_composite(ov)
        draw_text_alpha(img, (x0 + 100, box_top + 36), "FIELD NOTE", font(INTER_B, 32), (255, 120, 110), a2)
        f = font(INTER_B, 48)
        yy = box_top + 90
        for ln in wrap(f, spec["end"], x1 - x0 - 200):
            draw_text_alpha(img, (x0 + 100, yy), ln, f, WHITE, a2, dy=int(12 * (1 - a2)))
            yy += 62
        a3 = ease((t - end_t - 1.2) / 0.6)
        draw_text_alpha(img, (cx, y1 - 110), spec["follow"], font(INTER_B, 38), RED, a3, anchor="ma")
    return img


def field_cues(spec):
    t0, step = spec["first"], spec["step"]; ents = spec["entries"]
    end_t = t0 + len(ents) * step
    cues = [(0.3, t0 - 0.05, "Rink Field Guide. " + " ".join(spec["head"]).title() + ".")]
    for i, e in enumerate(ents):
        cues.append((t0 + i * step, t0 + (i + 1) * step, e["label"].title() + ": " + e["text"]))
    cues.append((end_t, spec["duration"] - 0.1, "Field note: " + spec["end"]))
    return cues, end_t


# ---------------------------------------------------------------- driver
def build(spec, outdir):
    name = spec["name"]
    kind = spec["layout"]
    seed = spec.get("seed", 3)
    tmp = f"/tmp/frames_{name}"
    shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    dur = spec["duration"]
    if kind == "receipt":
        bg = receipt_bg(seed); cache = {}
        render = lambda t: render_receipt(spec, t, bg, cache)
        cues, end_t = receipt_cues(spec)
        cov = cover_card(bg, spec["kicker"], spec["head"], spec.get("cover_sub"), kcolor=(255, 120, 110), scolor=(220, 200, 180))
    elif kind == "dashboard":
        bg = dash_bg(seed); dash = dash_layer()
        render = lambda t: render_dash(spec, t, bg, dash)
        cues, end_t = dash_cues(spec)
        base = bg.copy().convert("RGBA"); base.alpha_composite(dash)
        glow_text(base, (W // 2, 1478), spec["start_clock"], font(MONO_M, 128), TEAL, radius=12)
        cov = cover_card(base.convert("RGB"), spec["kicker"], spec["head"], spec.get("cover_sub"), kcolor=TEAL, panel=(4, 6, 14, 190))
    elif kind == "split":
        bg = split_bg(seed)
        render = lambda t: render_split(spec, t, bg)
        cues, end_t = split_cues(spec)
        cov = cover_card(bg, spec["kicker"], spec["head"], spec.get("cover_sub"), scolor=(225, 225, 235), panel=(6, 6, 10, 200))
    elif kind == "fieldguide":
        bg = field_bg(seed); card = card_layer(seed); icon = draw_toque(250)
        render = lambda t: render_field(spec, t, bg, card, icon)
        cues, end_t = field_cues(spec)
        cov = cover_card(bg, spec["kicker"], spec["head"], spec.get("cover_sub"), kcolor=(255, 120, 110), scolor=(220, 230, 210), panel=(6, 18, 14, 170))
    else:
        raise SystemExit("unknown layout " + kind)
    cues.append((end_t + 1.2, dur, spec["follow"]))
    write_srt(os.path.join(outdir, name + ".srt"), cues)
    cov.save(os.path.join(outdir, name + "-cover.jpg"), quality=92)
    for fi in range(int(dur * FPS)):
        t = fi / FPS
        if t < COVER_SECS:
            cov.save(f"{tmp}/{fi:05}.png", compress_level=1)
            continue
        render(t).convert("RGB").save(f"{tmp}/{fi:05}.png", compress_level=1)
    wav = f"/tmp/{name}.wav"
    m = spec.get("music", {})
    make_music(wav, dur, bpm=m.get("bpm", 78), seed=m.get("seed", seed), prog=m.get("prog", "am_f_c_g"),
               drums=m.get("drums", True), arp_density=m.get("arp_density", 0.85), lead=m.get("lead", "keys"))
    out = os.path.join(outdir, name + ".mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{tmp}/%05d.png", "-i", wav,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print(out)


if __name__ == "__main__":
    build(json.load(open(sys.argv[1])), sys.argv[2])
