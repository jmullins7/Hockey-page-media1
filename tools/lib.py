import math, random, wave, struct, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ANTON = "/usr/share/fonts/truetype/google-fonts/ofl/anton/Anton-Regular.ttf"
INTER_SB = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
INTER_B = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
INTER_M = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
MONO = os.path.expanduser("~/fonts/jbm/fonts/ttf/JetBrainsMono-Regular.ttf")
MONO_M = os.path.expanduser("~/fonts/jbm/fonts/ttf/JetBrainsMono-Medium.ttf")

WHITE = (240, 243, 247)
RED = (226, 54, 66)
SLATE = (138, 154, 176)
DIM = (120, 130, 145)

_fc = {}
def font(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]


def background(w, h, seed=7, rink_lines=True):
    """Dark navy gradient with faint ice-scratch texture."""
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(0, 1, w)[None, :]
    r = 16 - 6 * y + 2 * (1 - abs(x - 0.5))
    g = 26 - 8 * y + 3 * (1 - abs(x - 0.5))
    b = 40 - 12 * y + 4 * (1 - abs(x - 0.5))
    arr = np.stack([r + 0 * x, g + 0 * x, b + 0 * x], -1).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGB")
    tex = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(tex)
    rnd = random.Random(seed)
    for _ in range(70):
        x0, y0 = rnd.uniform(-100, w), rnd.uniform(0, h)
        pts = [(x0, y0)]
        ang = rnd.uniform(-0.4, 0.4)
        for _ in range(rnd.randint(6, 16)):
            x0 += rnd.uniform(15, 45)
            y0 += math.tan(ang) * 25 + rnd.uniform(-18, 18)
            pts.append((x0, y0))
        d.line(pts, fill=rnd.randint(10, 22), width=2)
    tex = tex.filter(ImageFilter.GaussianBlur(0.8))
    light = Image.new("RGB", (w, h), (90, 110, 140))
    img = Image.composite(light, img, tex)
    if rink_lines:
        d2 = ImageDraw.Draw(img, "RGBA")
        d2.rectangle([0, int(h * 0.094), w, int(h * 0.112)], fill=(40, 80, 140, 40))
        d2.rectangle([0, int(h * 0.854), w, int(h * 0.86)], fill=(200, 40, 50, 30))
    return img


def text_w(fnt, s):
    return fnt.getlength(s)


def wrap(fnt, s, maxw):
    words, lines, cur = s.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if text_w(fnt, t) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def draw_text_alpha(base, xy, s, fnt, fill, alpha, dy=0, anchor="la"):
    if alpha <= 0:
        return
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((xy[0], xy[1] + dy), s, font=fnt, fill=fill + (int(255 * alpha),), anchor=anchor)
    base.alpha_composite(layer)


# ---------------- music ----------------
SR = 44100

def _note(f, dur, sr=SR, kind="keys"):
    t = np.arange(int(dur * sr)) / sr
    if kind == "keys":
        sig = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t))
        env = np.exp(-t * 2.2) * (1 - np.exp(-t * 200))
    elif kind == "pluck":  # added 2026-11-26: brighter, shorter, guitar-ish
        sig = sum((0.6 ** h) * np.sin(2 * np.pi * f * (h + 1) * t) * np.exp(-t * (3 + 4 * h)) for h in range(5))
        env = (1 - np.exp(-t * 400))
    else:  # pad
        sig = sum(np.sin(2 * np.pi * f * (1 + dt) * t) for dt in (-0.003, 0, 0.004)) / 3
        a = np.minimum(1, t / 0.6)
        r = np.minimum(1, (dur - t) / 0.8).clip(0, 1)
        env = a * r
    return sig * env


def midi(n):
    return 440 * 2 ** ((n - 69) / 12)


PROGS = {
    "am_f_c_g": [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]],
    "f_c_dm_bb": [[53, 57, 60], [48, 52, 55], [50, 53, 57], [46, 50, 53]],
    "dm_bb_f_c": [[50, 53, 57], [46, 50, 53], [53, 57, 60], [48, 52, 55]],
    "c_g_am_f": [[48, 52, 55], [55, 59, 62], [57, 60, 64], [53, 57, 60]],
    "em_c_g_d": [[52, 55, 59], [48, 52, 55], [55, 59, 62], [50, 54, 57]],
    # added 2026-11-26
    "g_d_em_c": [[55, 59, 62], [50, 54, 57], [52, 55, 59], [48, 52, 55]],
    "bb_f_gm_eb": [[46, 50, 53], [53, 57, 60], [55, 58, 62], [51, 55, 58]],
    "am_em_f_g": [[57, 60, 64], [52, 55, 59], [53, 57, 60], [55, 59, 62]],
    # added 2026-11-27
    "d_a_bm_g": [[50, 54, 57], [57, 61, 64], [59, 62, 66], [55, 59, 62]],
    "cm_ab_eb_bb": [[48, 51, 55], [56, 60, 63], [51, 55, 58], [46, 50, 53]],
    "em_am_d_g": [[52, 55, 59], [57, 60, 64], [50, 54, 57], [55, 59, 62]],
}


def make_music(path, seconds, bpm=78, seed=1, prog="am_f_c_g", drums=True, arp_density=0.85, lead="keys"):
    """Original warm lo-fi bed: pad + keys arpeggio + soft kick/hat. prog picks the chord loop."""
    rnd = np.random.default_rng(seed)
    n = int(seconds * SR)
    out = np.zeros(n + SR * 3)
    beat = 60 / bpm
    bar = beat * 4
    prog = PROGS[prog] if isinstance(prog, str) else prog
    bars = int(math.ceil(seconds / bar)) + 1
    for b in range(bars):
        ch = prog[b % 4]
        s0 = int(b * bar * SR)
        for m in ch:
            p = _note(midi(m - 12), bar + 0.6, kind="pad") * 0.10
            out[s0:s0 + len(p)] += p[: len(out) - s0]
        bassn = _note(midi(ch[0] - 24), bar, kind="pad") * 0.16
        out[s0:s0 + len(bassn)] += bassn[: len(out) - s0]
        arp = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 12, ch[0] + 24, ch[2] + 12, ch[1] + 12, ch[2] + 12]
        for i, m in enumerate(arp):
            if rnd.random() > arp_density:
                continue
            si = s0 + int(i * beat / 2 * SR)
            k = _note(midi(m), 1.2, kind=lead) * (0.09 if lead == "pluck" else 0.07)
            out[si:si + len(k)] += k[: max(0, len(out) - si)]
        for q in range(4 if drums else 0):
            si = s0 + int(q * beat * SR)
            t = np.arange(int(0.35 * SR)) / SR
            if q in (0, 2):
                kick = np.sin(2 * np.pi * (50 + 70 * np.exp(-t * 30)) * t) * np.exp(-t * 9) * 0.28
                out[si:si + len(kick)] += kick[: max(0, len(out) - si)]
            else:
                sn = rnd.normal(0, 1, len(t)) * np.exp(-t * 25) * 0.05
                out[si:si + len(sn)] += sn[: max(0, len(out) - si)]
            for e in (0, 0.5):
                hi = si + int(e * beat * SR)
                th = np.arange(int(0.05 * SR)) / SR
                hat = np.diff(rnd.normal(0, 1, len(th) + 1)) * np.exp(-th * 90) * 0.025
                out[hi:hi + len(hat)] += hat[: max(0, len(out) - hi)]
    out = out[:n]
    # simple low-pass for warmth
    k = np.ones(6) / 6
    out = np.convolve(out, k, mode="same")
    fade = int(1.5 * SR)
    out[:int(0.4 * SR)] *= np.linspace(0, 1, int(0.4 * SR))
    out[-fade:] *= np.linspace(1, 0, fade)
    out = out / (np.abs(out).max() + 1e-9) * 0.55
    st = np.stack([out, out], -1)
    data = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def write_srt(path, cues):
    with open(path, "w") as f:
        for i, (a, b, txt) in enumerate(cues, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{txt}\n\n")
