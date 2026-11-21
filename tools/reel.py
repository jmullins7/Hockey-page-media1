import os, sys, json, subprocess, shutil
from PIL import Image, ImageDraw
from lib import *

W, H, FPS = 1080, 1920, 30
X = 96


def header(img, kicker, lines, a):
    draw_text_alpha(img, (X, 250), kicker, font(INTER_B, 36), RED, a)
    y = 330
    for s in lines:
        draw_text_alpha(img, (X, y), s, font(ANTON, 120), WHITE, a, dy=int(20 * (1 - a)))
        y += 124
    return y


def footer(img, t, start, end_text, follow):
    a = ease((t - start) / 0.6)
    if a <= 0:
        return
    f = font(INTER_SB, 46)
    y = 1450
    for ln in wrap(f, end_text, W - 2 * X):
        draw_text_alpha(img, (X, y), ln, f, WHITE, a, dy=int(16 * (1 - a)))
        y += 60
    a2 = ease((t - start - 1.2) / 0.6)
    draw_text_alpha(img, (X, 1700), follow, font(INTER_B, 38), RED, a2)


def build(spec, outdir):
    name = spec["name"]
    tmp = f"/tmp/frames_{name}"
    shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    bg = background(W, H, seed=spec.get("seed", 3)).convert("RGBA")
    dur = spec["duration"]
    items = spec["items"]
    t0, step = spec["first"], spec["step"]
    item_times = [t0 + i * step for i in range(len(items))]
    end_start = item_times[-1] + step
    cues = [(0.3, t0 - 0.1, spec["kicker"].title() + ": " + " ".join(spec["head"]).title())]
    for i, it in enumerate(items):
        a = item_times[i]
        b = item_times[i + 1] if i + 1 < len(items) else end_start
        cues.append((a, b, it["cap"]))
    cues.append((end_start, dur - 0.1, spec["end"]))
    cues.append((end_start + 1.2, dur, spec["follow"]))
    write_srt(os.path.join(outdir, name + ".srt"), cues)

    for fi in range(int(dur * FPS)):
        t = fi / FPS
        img = bg.copy()
        y = header(img, spec["kicker"], spec["head"], ease((t - 0.2) / 0.7)) + 72
        if spec["layout"] == "ledger":
            total = 0.0
            for i, it in enumerate(items):
                a = ease((t - item_times[i]) / 0.45)
                if a > 0:
                    total += it["amt"] * min(1, max(0, (t - item_times[i]) / 0.5))
                yy = y + i * 70
                draw_text_alpha(img, (X, yy + 6), it["time"], font(MONO, 30), DIM, a, dy=int(12 * (1 - a)))
                draw_text_alpha(img, (X + 205, yy), it["label"], font(INTER_SB, 38), WHITE, a, dy=int(12 * (1 - a)))
                draw_text_alpha(img, (W - X, yy + 2), it["price"], font(MONO_M, 38), WHITE, a, dy=int(12 * (1 - a)), anchor="ra")
            ly = 1300
            if t > item_times[0]:
                d = ImageDraw.Draw(img)
                d.line([(X, ly), (W - X, ly)], fill=(70, 82, 100), width=2)
                draw_text_alpha(img, (X, ly + 28), "RUNNING TOTAL", font(INTER_B, 30), SLATE, 1)
                draw_text_alpha(img, (W - X, ly + 14), f"${total:,.2f}", font(MONO_M, 64), WHITE, 1, anchor="ra")
        else:
            for i, it in enumerate(items):
                a = ease((t - item_times[i]) / 0.45)
                yy = y + i * 150
                draw_text_alpha(img, (X, yy), it["label"], font(INTER_B, 46), RED if i == 0 else WHITE, a, dy=int(14 * (1 - a)))
                draw_text_alpha(img, (X, yy + 60), it["sub"], font(INTER_M, 36), SLATE, a, dy=int(14 * (1 - a)))
        footer(img, t, end_start, spec["end"], spec["follow"])
        img.convert("RGB").save(f"{tmp}/{fi:05}.png", compress_level=1)

    wav = f"/tmp/{name}.wav"
    make_music(wav, dur, bpm=spec.get("bpm", 78), seed=spec.get("seed", 3))
    out = os.path.join(outdir, name + ".mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{tmp}/%05d.png", "-i", wav,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
    print(out)


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1]))
    build(spec, sys.argv[2])
