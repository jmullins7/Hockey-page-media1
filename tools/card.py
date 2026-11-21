import sys
from PIL import Image, ImageDraw
from lib import *

W, H = 1080, 1350
img = background(W, H, seed=21, rink_lines=False).convert("RGBA")
d = ImageDraw.Draw(img)
X = 112
d.text((X, 152), "SATURDAY", font=font(INTER_B, 34), fill=RED)

head = [("NOBODY SLEEPS", WHITE), ("IN ON A", WHITE), ("TOURNAMENT", RED), ("SATURDAY.", WHITE)]
f = font(ANTON, 140)
y = 300
for s, c in head:
    d.text((X, y), s, font=f, fill=c)
    y += 150
sub = font(INTER_SB, 46)
for line in wrap(sub, "Not the kids. Not the parents. Not the hotel waffle iron.", W - 2 * X):
    d.text((X, y + 58), line, font=sub, fill=SLATE)
    y += 60
img.convert("RGB").save(sys.argv[1], quality=92)
