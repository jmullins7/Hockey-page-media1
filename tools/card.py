import sys
from PIL import Image, ImageDraw
from lib import *

W, H = 1080, 1350
img = background(W, H, seed=61, rink_lines=False).convert("RGBA")
d = ImageDraw.Draw(img)
X = 112
d.text((X, 152), "TUESDAY", font=font(INTER_B, 34), fill=RED)

head = [("THE HOCKEY BAG", WHITE), ("IS PACKED.", WHITE), ("THE SUITCASE", WHITE), ("ISN'T.", RED)]
size = 140
while max(font(ANTON, size).getlength(s) for s, _ in head) > W - 2 * X:
    size -= 4
f = font(ANTON, size)
y = 300
for s, c in head:
    d.text((X, y), s, font=f, fill=c)
    y += int(size * 1.07)
sub = font(INTER_SB, 46)
for line in wrap(sub, "Two days to Thanksgiving. We know what matters.", W - 2 * X):
    d.text((X, y + 58), line, font=sub, fill=SLATE)
    y += 60
img.convert("RGB").save(sys.argv[1], quality=92)
print("size", size)
