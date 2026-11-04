"""The BTC Demon (Ep02+): a giant pixel demon whose head is the Dark Tap's TAP dome.

Drawn at native pixel scale (canvas 160x250) and scaled up by shots. `demon_image()` returns (RGBA, anchors).
"""
import math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw
import os
import paths

SKIN = (40, 16, 56)
SKIN_HI = (78, 34, 104)
SKIN_LO = (20, 6, 30)
RIM = (214, 80, 255)
DOME = (130, 40, 210)
DOME_HI = (230, 190, 255)
EYE = (255, 170, 40)          # bitcoin orange
BTC = (247, 147, 26)
HORN = (226, 214, 190)
HORN_LO = (120, 104, 88)
CHAIN = (120, 116, 130)
W, H = 160, 250
CX = 80

def _poly(d, pts, c):
    d.polygon([(round(x), round(y)) for x, y in pts], fill=c)

def _arm(d, sx, sy, ex, ey, hx, hy, side):
    for (a, b, w) in (((sx, sy), (ex, ey), 16), ((ex, ey), (hx, hy), 13)):
        d.line((a, b), fill=SKIN, width=w)
        d.ellipse((b[0] - w / 2, b[1] - w / 2, b[0] + w / 2, b[1] + w / 2), fill=SKIN)
    d.ellipse((sx - 12, sy - 10, sx + 12, sy + 12), fill=SKIN)          # shoulder
    # hand + claws
    d.ellipse((hx - 9, hy - 8, hx + 9, hy + 8), fill=SKIN)
    for k in range(4):
        ang = math.atan2(hy - ey, hx - ex) + (k - 1.5) * .35
        cx, cy = hx + math.cos(ang) * 8, hy + math.sin(ang) * 8
        d.line((cx, cy, cx + math.cos(ang) * 8, cy + math.sin(ang) * 8), fill=HORN, width=2)
    # broken shackle on the wrist
    wx, wy = ex + (hx - ex) * .7, ey + (hy - ey) * .7
    d.ellipse((wx - 9, wy - 5, wx + 9, wy + 5), outline=CHAIN, width=3)
    d.line((wx + 8 * side, wy, wx + 14 * side, wy + 10), fill=CHAIN, width=2)

def _btc(d, cx, cy, r):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(60, 22, 6), outline=BTC, width=2)
    # pixel "₿"
    pts = ['.1.1.', '1111.', '1...1', '1111.', '1...1', '1111.', '.1.1.']
    k = max(1, r // 6)
    ox, oy = cx - 5 * k // 2, cy - 7 * k // 2
    for y, row in enumerate(pts):
        for x, ch in enumerate(row):
            if ch == '1':
                d.rectangle((ox + x * k, oy + y * k, ox + x * k + k - 1, oy + y * k + k - 1), fill=BTC)

@lru_cache(None)
def _body(pose):
    """Static body layer (no face details) for a pose: 'idle', 'open' (arms wide), 'magic' (right hand up), 'point'."""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # torso
    _poly(d, [(CX - 52, 78), (CX + 52, 78), (CX + 44, 150), (CX + 30, 205), (CX - 30, 205), (CX - 44, 150)], SKIN)
    _poly(d, [(CX - 50, 80), (CX - 6, 86), (CX - 4, 120), (CX - 42, 118)], SKIN_HI)           # left pec light
    _poly(d, [(CX + 6, 86), (CX + 50, 80), (CX + 42, 118), (CX + 4, 120)], SKIN)
    for i in range(3):                                                                       # abs
        y = 132 + i * 20
        d.rectangle((CX - 18, y, CX - 3, y + 14), fill=SKIN_HI)
        d.rectangle((CX + 3, y, CX + 18, y + 14), fill=SKIN)
    # neck
    d.rectangle((CX - 18, 60, CX + 18, 84), fill=SKIN)
    # belt of chains + ragged loincloth
    for x in range(CX - 34, CX + 34, 8):
        d.ellipse((x, 196, x + 9, 204), outline=CHAIN, width=2)
    _poly(d, [(CX - 34, 204), (CX + 34, 204), (CX + 26, 248), (CX + 10, 236), (CX, 250), (CX - 12, 238), (CX - 28, 248)], (24, 8, 30))
    # arms
    if pose == 'open':
        _arm(d, CX - 54, 86, CX - 76, 110, CX - 78, 64, -1)
        _arm(d, CX + 54, 86, CX + 76, 110, CX + 78, 64, 1)
    elif pose == 'magic':
        _arm(d, CX - 54, 86, CX - 70, 140, CX - 58, 186, -1)
        _arm(d, CX + 54, 86, CX + 74, 60, CX + 70, 14, 1)
    elif pose == 'point':
        _arm(d, CX - 54, 86, CX - 70, 140, CX - 58, 186, -1)
        _arm(d, CX + 54, 86, CX + 70, 118, CX + 40, 150, 1)
    else:
        _arm(d, CX - 54, 86, CX - 72, 140, CX - 62, 188, -1)
        _arm(d, CX + 54, 86, CX + 72, 140, CX + 62, 188, 1)
    _btc(d, CX, 104, 15)
    # pentagram scars
    for k in range(5):
        a1 = -math.pi / 2 + k * 4 * math.pi / 5
        a2 = -math.pi / 2 + (k + 1) * 4 * math.pi / 5
        d.line((CX + math.cos(a1) * 30, 104 + math.sin(a1) * 30, CX + math.cos(a2) * 30, 104 + math.sin(a2) * 30), fill=(110, 30, 140), width=1)
    return im

def _head(eyes='glow', mouth=0, t=0.0):
    im = Image.new('RGBA', (W, 90), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # horns (behind the dome)
    for side in (-1, 1):
        base = (CX + side * 26, 40)
        pts = [base, (CX + side * 40, 30), (CX + side * 54, 12), (CX + side * 58, 0), (CX + side * 50, 8), (CX + side * 38, 22), (CX + side * 28, 30)]
        _poly(d, pts, HORN)
        d.line(pts[:4], fill=HORN_LO, width=1)
    # face block
    _poly(d, [(CX - 28, 34), (CX + 28, 34), (CX + 24, 58), (CX + 12, 68), (CX - 12, 68), (CX - 24, 58)], SKIN)
    # the TAP dome = the cranium
    d.pieslice((CX - 28, 6, CX + 28, 62), 180, 360, fill=DOME)
    d.pieslice((CX - 22, 12, CX + 22, 56), 180, 360, fill=(160, 60, 240))
    d.ellipse((CX - 16, 14, CX - 8, 20), fill=DOME_HI)
    d.line((CX - 28, 34, CX + 28, 34), fill=(30, 0, 40), width=2)
    # eyes
    if eyes == 'closed':
        for s in (-1, 1):
            d.line((CX + s * 6, 44, CX + s * 18, 42), fill=(10, 0, 10), width=2)
    else:
        k = 1.0 if eyes == 'glow' else 1.3
        for s in (-1, 1):
            _poly(d, [(CX + s * 5, 46), (CX + s * 19 * k, 39), (CX + s * 19 * k, 44), (CX + s * 7, 49)], EYE)
            d.point((CX + s * 12, 44), fill=(255, 255, 220))
    # mouth with teeth (opens with the voice)
    m = int(mouth)
    d.rectangle((CX - 13, 54, CX + 13, 56 + m * 2), fill=(30, 0, 12))
    for x in range(CX - 12, CX + 12, 4):
        _poly(d, [(x, 54), (x + 3, 54), (x + 1.5, 58)], (240, 230, 210))
        if m:
            _poly(d, [(x + 1, 57 + m * 2), (x + 4, 57 + m * 2), (x + 2.5, 53 + m * 2)], (240, 230, 210))
    return im

def _finish(im):
    """Dark outline + magenta rim light on the right edges."""
    a = np.asarray(im).copy()
    m = a[..., 3] > 0
    grow = m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
    edge = grow & ~m
    a[edge] = (8, 0, 12, 255)
    rim = m & ~np.roll(m, -1, 1)
    a[rim, :3] = (a[rim, :3] * .4 + np.array(RIM) * .6).astype(np.uint8)
    return Image.fromarray(a)

def demon_image(pose='idle', eyes='glow', mouth=0, t=0.0):
    body = _body(pose).copy()
    head = _head(eyes, mouth, t)
    body.alpha_composite(head, (0, 0))
    out = _finish(body)
    anchors = dict(dome_top=(CX, 6), eyes=(CX, 44), mouth=(CX, 56), chest=(CX, 104), waist=(CX, 200), size=(W, H))
    return out, anchors

@lru_cache(None)
def flame_sprite():
    return Image.open(os.path.join(paths.SPRITES, 'props', 'flame.png')).convert('RGBA')

def flame(img, x, y, t, scale=3, seed=0):
    """Draw one animated lila flame (the provided asset) with flicker + sway; (x,y) = base centre."""
    f = flame_sprite()
    rnd = (math.sin(t * 9 + seed * 1.7) + math.sin(t * 13.3 + seed)) * .5
    sy = scale * (1 + .14 * rnd)
    sx = scale * (1 - .08 * rnd)
    fl = f.resize((max(1, int(f.width * sx)), max(1, int(f.height * sy))), Image.NEAREST)
    if int(t * 6 + seed) % 2:
        fl = fl.transpose(Image.FLIP_LEFT_RIGHT)
    x0, y0 = int(x - fl.width / 2 + math.sin(t * 4 + seed) * scale), int(y - fl.height)
    ax0, ay0 = max(0, -x0), max(0, -y0)
    ax1, ay1 = min(fl.width, img.width - x0), min(fl.height, img.height - y0)
    if ax1 > ax0 and ay1 > ay0:
        img.alpha_composite(fl.crop((ax0, ay0, ax1, ay1)), (x0 + ax0, y0 + ay0))


def laser_eyes(img, eyes, k, length=700):
    """Red laser beams out of the demon's eyes (k: 0..1 intensity)."""
    if k <= 0:
        return
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i, (ex, ey) in enumerate(eyes):
        a = math.radians(70 if i == 0 else 110)
        x2, y2 = ex + math.cos(a) * length * (-1 if i == 0 else 1) * -1, ey + math.sin(a) * length
        x2 = ex + (-length * .55 if i == 0 else length * .55)
        for w, c in ((22, (255, 0, 0, int(70 * k))), (10, (255, 30, 30, int(200 * k))), (4, (255, 230, 230, int(255 * k)))):
            d.line((ex, ey, x2, y2), fill=c, width=w)
        d.ellipse((ex - 14, ey - 14, ex + 14, ey + 14), fill=(255, 60, 60, int(220 * k)))
        d.ellipse((ex - 6, ey - 6, ex + 6, ey + 6), fill=(255, 255, 255, int(255 * k)))
    img.alpha_composite(lay)
