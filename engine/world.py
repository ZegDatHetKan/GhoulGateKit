"""v2 sets at 480x270: crypt room, basement corridor, door side, Dark Tap console, light maps."""
import math, random
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 480, 270

def rgba(c, a=255):
    return tuple(int(v) for v in c[:3]) + (a,)

_B4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0

def bayer(h, w):
    return np.tile(_B4, (h // 4 + 1, w // 4 + 1))[:h, :w]

def vgrad(w, h, stops, dither=True):
    ys = np.linspace(0, 1, h)
    a = np.zeros((h, w, 3))
    th = bayer(h, w) if dither else np.full((h, w), .5)
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]; p1, c1 = stops[i + 1]
        sel = (ys >= p0) & (ys <= p1)
        t = ((ys[sel] - p0) / max(1e-6, p1 - p0))[:, None]
        steps = 6
        tq = np.floor(t * steps + th[sel]) / steps
        tq = np.clip(tq, 0, 1)[..., None]
        a[sel] = np.array(c0) * (1 - tq) + np.array(c1) * tq
    return Image.fromarray(a.astype(np.uint8)).convert('RGBA')

def bricks(img, box, base, mortar, seed=0, bw=18, bh=9, var=10):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    d.rectangle(box, fill=rgba(mortar))
    rnd = random.Random(seed)
    row = 0
    for y in range(y0, y1, bh):
        off = (bw // 2) if row % 2 else 0
        for x in range(x0 - off, x1, bw):
            v = rnd.randint(-var, var)
            c = tuple(max(0, min(255, b + v)) for b in base)
            d.rectangle((x + 1, y + 1, x + bw - 1, y + bh - 1), fill=rgba(c))
            d.line((x + 1, y + 1, x + bw - 2, y + 1), fill=rgba([min(255, k + 12) for k in c]))
            d.line((x + 1, y + bh - 1, x + bw - 1, y + bh - 1), fill=rgba([max(0, k - 10) for k in c]))
            if rnd.random() < .25:
                d.point((x + rnd.randint(2, bw - 3), y + rnd.randint(2, bh - 2)), fill=rgba(mortar))
            if rnd.random() < .06:  # moss / cracks
                cx = x + rnd.randint(2, bw - 4)
                d.line((cx, y + 2, cx + 2, y + bh - 2), fill=rgba(mortar))
        row += 1

def checker_floor(img, y0, c0, c1, horizon, cx=W // 2, tile=30):
    a = np.asarray(img).copy()
    xs = np.arange(W)
    for y in range(y0, H):
        z = (H - horizon) / max(1, (y - horizon))
        row_i = int(z * 3.2)
        u = (xs - cx) * z / tile
        m = ((np.floor(u).astype(int) + row_i) % 2) == 0
        shade = min(1.0, .55 + .45 * (y - y0) / (H - y0))
        a[y, m, :3] = np.array(c0) * shade
        a[y, ~m, :3] = np.array(c1) * shade
        a[y, :, 3] = 255
    img.paste(Image.fromarray(a))

# ---------------------------------------------------------------- tiny 3x5 font for props
_F35 = {
    'A': '010101111101101', 'B': '110101110101110', 'C': '011100100100011', 'D': '110101101101110',
    'E': '111100110100111', 'F': '111100110100100', 'G': '011100101101011', 'H': '101101111101101',
    'I': '111010010010111', 'J': '001001001101010', 'K': '101101110101101', 'L': '100100100100111',
    'M': '101111111101101', 'N': '110101101101101', 'O': '010101101101010', 'P': '110101110100100',
    'Q': '010101101110011', 'R': '110101110101101', 'S': '011100010001110', 'T': '111010010010010',
    'U': '101101101101111', 'V': '101101101101010', 'W': '101101111111101', 'X': '101101010101101',
    'Y': '101101010010010', 'Z': '111001010100111', '0': '111101101101111', '1': '010110010010111',
    '2': '110001010100111', '3': '110001010001110', '4': '101101111001001', '5': '111100110001110',
    '6': '011100111101111', '7': '111001010010010', '8': '111101111101111', '9': '111101111001110',
    '!': '010010010000010', '?': '110001010000010', '.': '000000000000010', '-': '000000111000000',
    ' ': '000000000000000', ':': '000010000010000',
}

def tiny(img, x, y, s, color, k=1):
    d = ImageDraw.Draw(img)
    cx = x
    for ch in s.upper():
        g = _F35.get(ch, _F35[' '])
        for i, b in enumerate(g):
            if b == '1':
                px, py = cx + (i % 3) * k, y + (i // 3) * k
                d.rectangle((px, py, px + k - 1, py + k - 1), fill=color)
        cx += 4 * k
    return cx - x

def tiny_w(s, k=1):
    return len(s) * 4 * k - k

# ---------------------------------------------------------------- lights (additive, soft)
def glow(layer_arr, x, y, r, color, a):
    """Add a soft radial light into float array (H,W,3)."""
    h, w = layer_arr.shape[:2]
    x0, x1 = max(0, int(x - r)), min(w, int(x + r) + 1)
    y0, y1 = max(0, int(y - r)), min(h, int(y + r) + 1)
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    dd = np.sqrt((xx - x) ** 2 + (yy - y) ** 2) / r
    k = np.clip(1 - dd, 0, 1) ** 2 * a
    layer_arr[y0:y1, x0:x1] += k[..., None] * np.array(color)[None, None] / 255.0

def apply_light(img, light, ambient=1.0):
    a = np.asarray(img).astype(np.float32)
    rgb = a[..., :3] / 255.0
    out = rgb * ambient + rgb * light * 1.4 + light * .25
    a[..., :3] = np.clip(out * 255, 0, 255)
    return Image.fromarray(a.astype(np.uint8))

# ---------------------------------------------------------------- the Dark Tap console (buttons!)
def console(img, x, y, t, dark=0.0, untap=0.0, glow_k=1.0, s=1):
    """The Dark Tap: an obsidian pedestal with a glowing pentagram, a TAP dome and an UNTAP button.
    dark/untap: press depth 0..1. (x,y) = bottom centre of pedestal."""
    d = ImageDraw.Draw(img)
    S = lambda v: int(round(v * s))
    pulse = .75 + .25 * math.sin(t * 3)
    g = max(0.0, min(2.0, glow_k))
    rim = (int(70 + 60 * g * pulse), int(10 + 10 * g), int(110 + 70 * g * pulse))
    # pedestal (obsidian)
    pw, ph = S(46), S(34)
    px0, py0 = x - pw // 2, y - ph
    d.polygon([(px0 + S(4), py0), (px0 + pw - S(4), py0), (px0 + pw, y), (px0, y)], fill=(12, 8, 16, 255), outline=rim + (255,))
    d.line((px0 + S(5), py0 + S(1), px0 + pw - S(5), py0 + S(1)), fill=(40, 30, 54, 255))
    # glowing pentagram in a circle on the front
    cx, cy, r = x, py0 + S(18), S(10)
    pc = (int(150 + 100 * min(1, g) * pulse), int(20 + 30 * min(1, g)), int(200 + 55 * min(1, g) * pulse), 255)
    pts = [(cx + r * .86 * math.cos(-math.pi / 2 + i * 4 * math.pi / 5), cy + r * .86 * math.sin(-math.pi / 2 + i * 4 * math.pi / 5)) for i in range(6)]
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=pc, width=max(1, S(1)))
    d.line(pts, fill=pc, width=max(1, S(1)))
    # top plate
    tx0, tx1, ty = px0 - S(4), px0 + pw + S(4), py0
    d.polygon([(tx0, ty), (tx1, ty), (tx1 - S(6), ty - S(9)), (tx0 + S(6), ty - S(9))], fill=(22, 14, 28, 255), outline=rim + (255,))
    # TAP dome (left): black glass with a violet core
    bx, by = x - S(9), ty - S(6)
    br = S(9)
    dep = S(3) * dark
    d.ellipse((bx - br - S(1), by - S(3), bx + br + S(1), by + S(4)), fill=(6, 2, 8, 255))
    core = (int(70 + 120 * min(1, g) * pulse), int(10 + 20 * min(1, g)), int(110 + 140 * min(1, g) * pulse))
    d.pieslice((bx - br, by - br + dep, bx + br, by + br + dep), 180, 360, fill=(30, 6, 44, 255), outline=(8, 0, 12, 255))
    d.pieslice((bx - br + S(2), by - br + S(3) + dep, bx + br - S(2), by + br - S(1) + dep), 180, 360, fill=core + (255,))
    d.ellipse((bx - br // 2, by - br + S(2) + dep, bx - br // 2 + S(3), by - br + S(4) + dep), fill=(230, 190, 255, 255))
    # UNTAP button (right), bone white
    ux, uy = x + S(13), ty - S(5)
    ur = S(5)
    udep = S(2) * untap
    d.ellipse((ux - ur - S(1), uy - S(2), ux + ur + S(1), uy + S(3)), fill=(6, 4, 8, 255))
    d.pieslice((ux - ur, uy - ur + S(2) + udep, ux + ur, uy + ur + S(2) + udep), 180, 360, fill=(226, 230, 222, 255), outline=(70, 70, 66, 255))
    k = max(1, s // 2)
    tiny(img, bx - tiny_w('TAP', k) // 2, ty + S(2), 'TAP', (230, 80, 255, 255), k)
    tiny(img, ux - tiny_w('UNTAP', k) // 2, ty + S(2), 'UNTAP', (220, 230, 220, 255), k)
    return (bx, by - br + dep), (ux, uy - ur + S(2) + udep)

def portal(img, x, y, t, r=22, k=1.0):
    if k <= 0:
        return
    gl = Image.new('RGBA', img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(gl)
    for i in range(6, 0, -1):
        rr = r * k * (0.35 + i * .13)
        col = [(20, 0, 40), (60, 0, 110), (120, 30, 220), (180, 90, 255), (230, 170, 255), (255, 240, 255)][6 - i]
        gd.ellipse((x - rr, y - rr * .38, x + rr, y + rr * .38), fill=col + (170 + 12 * i,))
    for i in range(14):
        a = t * 5 + i * math.tau / 14
        rr = r * k * (1 + .08 * math.sin(t * 7 + i))
        gd.point((x + math.cos(a) * rr, y + math.sin(a) * rr * .38), fill=(255, 210, 255, 255))
    img.alpha_composite(gl)

# ---------------------------------------------------------------- the crypt (main room)
TABLE = (112, 196, 368, 222)    # x0, top y, x1, front y
CONSOLE_POS = (438, 250)
PORTAL_POS = (392, 258)

@lru_cache(None)
def _room_static(night=False):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    bricks(img, (0, 0, W, 158), (50, 38, 72), (22, 16, 32), seed=7)
    # arched ceiling beams
    d = ImageDraw.Draw(img)
    for x in (0, 160, 320, 480):
        d.rectangle((x - 9, 0, x + 9, 158), fill=(42, 32, 60, 255))
        d.line((x - 7, 0, x - 7, 158), fill=(70, 58, 94, 255))
        d.line((x + 8, 0, x + 8, 158), fill=(26, 20, 38, 255))
    checker_floor(img, 158, (60, 36, 84), (24, 14, 34), horizon=70)
    d.rectangle((0, 152, W, 159), fill=(30, 20, 42, 255)); d.line((0, 152, W, 152), fill=(84, 64, 108, 255))
    # high barred window (moonlight source at night)
    d.rectangle((356, 26, 400, 52), fill=(14, 18, 40, 255), outline=(20, 14, 26, 255))
    d.rectangle((358, 28, 398, 50), fill=(40, 60, 110, 255) if night else (30, 40, 70, 255))
    if night:
        d.ellipse((380, 31, 391, 42), fill=(230, 235, 255, 255))
    for x in range(362, 398, 7):
        d.line((x, 28, x, 50), fill=(16, 12, 20, 255), width=2)
    # arcade cabinet (left)
    ax, ay = 22, 74
    d.polygon([(ax, ay), (ax + 34, ay), (ax + 34, 156), (ax, 156)], fill=(34, 18, 80, 255), outline=(12, 6, 30, 255))
    d.rectangle((ax + 2, ay + 2, ax + 32, ay + 11), fill=(250, 200, 40, 255))
    tiny(img, ax + 6, ay + 4, 'GHOUL', (120, 0, 60, 255))
    d.rectangle((ax + 4, ay + 15, ax + 30, ay + 38), fill=(4, 4, 12, 255))
    d.rectangle((ax + 1, ay + 42, ax + 33, ay + 50), fill=(64, 42, 120, 255))
    for i, c in enumerate(((255, 40, 40), (40, 200, 255), (255, 230, 40))):
        d.rectangle((ax + 16 + i * 5, ay + 45, ax + 17 + i * 5, ay + 46), fill=c + (255,))
    d.line((ax + 8, ay + 44, ax + 8, ay + 40), fill=(200, 200, 200, 255)); d.rectangle((ax + 7, ay + 39, ax + 9, ay + 40), fill=(255, 40, 40, 255))
    # shelves w/ bottles, skull, plant, lava lamp
    for sy in (72, 104):
        d.rectangle((70, sy, 128, sy + 3), fill=(80, 50, 32, 255)); d.line((70, sy + 4, 128, sy + 4), fill=(30, 18, 12, 255))
    cols = [(60, 160, 80), (180, 60, 60), (220, 190, 60), (90, 120, 220), (200, 100, 220), (90, 200, 200)]
    for i, bx in enumerate(range(73, 126, 7)):
        c = cols[i % 6]; hh = 10 + (i * 3) % 6
        d.rectangle((bx, 72 - hh, bx + 4, 71), fill=c + (255,), outline=tuple(v // 3 for v in c) + (255,))
        d.rectangle((bx + 1, 72 - hh - 4, bx + 3, 72 - hh), fill=c + (255,))
        d.point((bx + 1, 72 - hh + 3), fill=(255, 255, 255, 255))
    d.ellipse((74, 91, 86, 103), fill=(222, 214, 190, 255), outline=(60, 50, 40, 255))
    d.rectangle((77, 96, 79, 98), fill=(10, 10, 10, 255)); d.rectangle((81, 96, 83, 98), fill=(10, 10, 10, 255))
    d.rectangle((112, 94, 122, 103), fill=(150, 80, 50, 255))
    for i in range(6):
        d.line((117, 94, 108 + i * 4, 82 + (i % 2) * 4), fill=(60, 170, 70, 255))
    # posters
    d.rectangle((140, 66, 168, 100), fill=(16, 16, 30, 255), outline=(200, 200, 220, 255))
    d.ellipse((146, 71, 160, 85), fill=(230, 230, 210, 255)); d.ellipse((150, 70, 164, 83), fill=(16, 16, 30, 255))
    tiny(img, 145, 90, 'GM', (255, 220, 80, 255), 1)
    d.rectangle((306, 66, 332, 98), fill=(200, 40, 40, 255), outline=(30, 0, 0, 255))
    tiny(img, 310, 70, 'HODL', (255, 240, 220, 255))
    d.ellipse((313, 78, 325, 92), fill=(240, 236, 220, 255)); d.rectangle((316, 84, 318, 86), fill=(0, 0, 0, 255)); d.rectangle((320, 84, 322, 86), fill=(0, 0, 0, 255))
    # wall clock
    d.ellipse((412, 64, 434, 86), fill=(220, 210, 180, 255), outline=(60, 40, 20, 255))
    # CRT stack (right)
    for (tx, ty, tw, th) in ((418, 96, 40, 30), (424, 126, 34, 26), (440, 72, 28, 22)):
        d.rectangle((tx, ty, tx + tw, ty + th), fill=(74, 70, 64, 255), outline=(20, 18, 16, 255))
        d.rectangle((tx + 3, ty + 3, tx + tw - 8, ty + th - 3), fill=(8, 20, 14, 255))
        d.point((tx + tw - 4, ty + 6), fill=(255, 60, 60, 255))
    # throne on a dais (centre back)
    d.rectangle((206, 140, 274, 156), fill=(60, 44, 30, 255), outline=(20, 12, 8, 255))
    d.rectangle((222, 64, 258, 146), fill=(70, 46, 18, 255))
    d.polygon([(216, 66), (240, 40), (264, 66)], fill=(96, 66, 24, 255))
    d.rectangle((226, 70, 254, 140), fill=(130, 20, 44, 255))
    for x in (224, 256):
        d.rectangle((x - 3, 60, x + 3, 146), fill=(200, 160, 56, 255)); d.line((x - 2, 60, x - 2, 146), fill=(250, 220, 120, 255))
    d.ellipse((236, 48, 244, 56), fill=(255, 220, 90, 255))
    # rug
    d.ellipse((90, 214, 390, 268), fill=(96, 20, 54, 255))
    d.ellipse((100, 218, 380, 264), outline=(210, 160, 60, 255))
    d.ellipse((110, 222, 370, 260), outline=(150, 40, 80, 255))
    # couch (left front)
    d.rounded_rectangle((14, 206, 104, 246), 6, fill=(46, 90, 110, 255), outline=(14, 30, 40, 255))
    d.rounded_rectangle((10, 196, 30, 248), 5, fill=(40, 80, 100, 255), outline=(14, 30, 40, 255))
    d.rounded_rectangle((88, 196, 108, 248), 5, fill=(40, 80, 100, 255), outline=(14, 30, 40, 255))
    d.line((20, 222, 98, 222), fill=(30, 66, 84, 255))
    if night:
        a = np.asarray(img).astype(float)
        a[..., 0] *= .32; a[..., 1] *= .38; a[..., 2] *= .72
        img = Image.fromarray(a.astype(np.uint8))
    return img

def room_bg(t, night=False, clock_h=3):
    img = _room_static(night).copy()
    d = ImageDraw.Draw(img)
    fl = 1.0 if (math.sin(t * 13) + math.sin(t * 5.1 + 1)) > -1.75 else 0.3
    if night:
        fl *= .15
    s = 'BASED GHOUL CRYPT'
    tw = tiny_w(s, 2)
    sx = (W - tw) // 2
    neon = (255, 90, 210)
    core = tuple(int(c * (.35 + .65 * fl)) for c in (255, 215, 245))
    tiny(img, sx + 1, 15, s, rgba([c * .4 * fl for c in neon]), 2)
    tiny(img, sx, 14, s, rgba(core), 2)
    # string lights
    cols = [(255, 80, 80), (255, 220, 60), (80, 255, 140), (80, 160, 255), (255, 90, 230)]
    pts = []
    for i, x in enumerate(range(10, 472, 12)):
        y = 38 + 7 * math.sin(x / 30)
        pts.append((x, y))
    d.line(pts, fill=(16, 10, 20, 255))
    for i, (x, y) in enumerate(pts):
        on = (int(t * 3) + i) % 5 != 0
        c = cols[i % 5] if on else tuple(v // 3 for v in cols[i % 5])
        if night:
            c = tuple(v // 3 for v in c)
        d.rectangle((x, y + 1, x + 1, y + 3), fill=c + (255,))
    # arcade attract mode
    ax, ay = 22, 74
    ph = int(t * 8)
    for i in range(4):
        d.point((ax + 6 + (ph * 3 + i * 5) % 22, ay + 18 + i * 5), fill=(255, 255, 80, 255))
    d.rectangle((ax + 6 + ph % 20, ay + 33, ax + 8 + ph % 20, ay + 35), fill=(80, 255, 120, 255))
    # CRTs: static + rising chart
    rnd = random.Random(int(t * 15))
    for (tx, ty, tw_, th_) in ((418, 96, 40, 30), (424, 126, 34, 26), (440, 72, 28, 22)):
        for _ in range(26):
            v = rnd.randint(50, 190) // (3 if night else 1)
            d.point((tx + 3 + rnd.randrange(tw_ - 11), ty + 3 + rnd.randrange(th_ - 6)), fill=(v // 2, v, v // 2, 255))
    d.line([(422 + i * 3, 120 - int(abs(math.sin(i * .9 + t)) * 8) - i) for i in range(10)], fill=(80, 255, 120, 255))
    # lava lamp
    d.polygon([(130, 104), (134, 80), (140, 80), (144, 104)], fill=(40, 10, 50, 255))
    for i in range(3):
        by = 99 - ((t * 4 + i * 7) % 17)
        d.ellipse((134 + i, by, 138 + i, by + 4), fill=(255, 80, 160, 255) if not night else (120, 40, 80, 255))
    # clock hands
    cx, cy = 423, 75
    ang_m = t * .6
    ang_h = math.radians(clock_h * 30) + ang_m / 12
    d.line((cx, cy, cx + math.sin(ang_m) * 8, cy - math.cos(ang_m) * 8), fill=(20, 10, 10, 255))
    d.line((cx, cy, cx + math.sin(ang_h) * 5, cy - math.cos(ang_h) * 5), fill=(20, 10, 10, 255), width=2)
    # candles
    for i, (x, y) in enumerate(((80, 64), (124, 96), (150, 189), (330, 189))):
        candle(img, x, y, t, i, night)
    return img

def candle(img, x, y, t, seed=0, night=False):
    d = ImageDraw.Draw(img)
    d.rectangle((x, y, x + 2, y + 7), fill=(230, 220, 200, 255))
    d.point((x + 1, y + 2), fill=(160, 150, 140, 255))
    f = int((math.sin(t * 17 + seed) + math.sin(t * 9.3 + seed * 2)) > .3)
    d.point((x + 1, y - 1), fill=(255, 240, 140, 255))
    d.point((x + 1, y - 2 - f), fill=(255, 160, 40, 255))
    if f:
        d.point((x, y - 2), fill=(255, 120, 30, 255))

def room_lights(t, night=False, console_glow=1.0, extra=()):
    L = np.zeros((H, W, 3), np.float32)
    fl = 1.0 if (math.sin(t * 13) + math.sin(t * 5.1 + 1)) > -1.75 else 0.3
    if not night:
        glow(L, 240, 20, 150, (255, 90, 210), .55 * fl)          # neon sign
        for i, (x, y) in enumerate(((80, 62), (124, 94), (150, 187), (330, 187))):
            k = .55 + .1 * math.sin(t * 9 + i * 3)
            glow(L, x + 1, y - 2, 46, (255, 170, 80), k)
        glow(L, 440, 110, 70, (90, 255, 150), .35)               # CRTs
        glow(L, 40, 100, 50, (120, 80, 255), .3)                 # arcade
        glow(L, 240, 200, 200, (255, 200, 150), .18)             # table lamp spill
    else:
        glow(L, 378, 40, 60, (140, 170, 255), .5)                # moon window
        # moon shaft across the floor
        shaft = Image.new('L', (W, H), 0)
        sd = ImageDraw.Draw(shaft)
        sd.polygon([(358, 30), (398, 30), (300, 270), (190, 270)], fill=70)
        sh = np.asarray(shaft.filter(ImageFilter.GaussianBlur(10))).astype(np.float32) / 255
        L += sh[..., None] * np.array([.45, .55, 1.0])[None, None] * .8
        glow(L, 440, 110, 60, (90, 255, 150), .25)
    cx, cy = CONSOLE_POS
    glow(L, cx - 8, cy - 40, 70, (170, 60, 255), (.45 if not night else .9) * console_glow * (.8 + .2 * math.sin(t * 3)))
    for (x, y, r, c, a) in extra:
        glow(L, x, y, r, c, a)
    return L

def table_layer(img, t, night=False):
    d = ImageDraw.Draw(img)
    x0, ty, x1, fy = TABLE
    top = (100, 56, 36) if not night else (36, 22, 30)
    d.rounded_rectangle((x0, ty, x1, fy), 10, fill=rgba(top), outline=(30, 14, 10, 255))
    d.rounded_rectangle((x0 + 10, ty + 3, x1 - 10, fy - 6), 8, fill=rgba((30, 110, 62) if not night else (12, 36, 28)))
    d.rounded_rectangle((x0 + 12, ty + 4, x1 - 12, fy - 7), 7, outline=rgba((50, 140, 80) if not night else (20, 50, 36)))
    d.rectangle((x0 + 8, fy, x1 - 8, fy + 10), fill=rgba((66, 34, 22) if not night else (22, 12, 16)))
    for lx in (x0 + 18, x1 - 24):
        d.rectangle((lx, fy + 10, lx + 6, 266), fill=rgba((54, 26, 18) if not night else (18, 10, 12)))
    # props: chips, cards, drinks, bong
    for i, (cx_, c) in enumerate(((228, (220, 40, 40)), (233, (40, 80, 220)), (238, (240, 220, 60)), (246, (220, 40, 40)))):
        for k in range(3 + i % 2):
            d.rectangle((cx_, ty + 11 - k, cx_ + 4, ty + 12 - k), fill=rgba(c if not night else [v // 3 for v in c]))
    for i, cx_ in enumerate((176, 186, 296, 306)):
        d.rectangle((cx_, ty + 8, cx_ + 6, ty + 13), fill=rgba((240, 240, 240) if not night else (80, 80, 90)), outline=(60, 60, 60, 255))
    for gx in (140, 200, 330):
        d.rectangle((gx, ty - 2, gx + 4, ty + 6), fill=(255, 200, 60, 210) if not night else (90, 70, 30, 255))
        d.line((gx, ty - 2, gx + 4, ty - 2), fill=(255, 255, 230, 255))
    # the bong stands ON the felt (it used to sit on the back edge and read as floating above the table)
    d.ellipse((255, ty + 15, 273, ty + 19), fill=(20, 60, 36, 200))
    d.rectangle((262, ty - 8, 266, ty + 12), fill=(80, 200, 220, 190))
    d.ellipse((257, ty + 7, 271, ty + 17), fill=(80, 200, 220, 210))
    d.line((270, ty + 9, 275, ty + 4), fill=(160, 160, 170, 255))

# ---------------------------------------------------------------- basement corridor (cold open)
@lru_cache(None)
def _basement_static():
    img = Image.new('RGBA', (W, H), (6, 6, 10, 255))
    d = ImageDraw.Draw(img)
    # corridor walls in perspective toward the door
    vx, vy = 240, 118
    bricks(img, (0, 0, W, 200), (34, 32, 44), (14, 12, 18), seed=3, bw=22, bh=11)
    # darken edges toward the camera (perspective side walls)
    side = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(side)
    sd.polygon([(0, 0), (150, 52), (150, 196), (0, 270)], fill=(10, 8, 14, 170))
    sd.polygon([(480, 0), (330, 52), (330, 196), (480, 270)], fill=(10, 8, 14, 170))
    img.alpha_composite(side)
    # floor
    for y in range(196, H):
        k = (y - 196) / (H - 196)
        d.line((0, y, W, y), fill=(int(18 + 18 * k), int(16 + 15 * k), int(22 + 18 * k), 255))
    for x in range(-400, W + 400, 30):
        d.line((vx + (x - vx) * .25, 196, x, H), fill=(12, 10, 16, 255))
    # pipes
    d.rectangle((0, 10, W, 15), fill=(30, 26, 34, 255)); d.line((0, 11, W, 11), fill=(60, 52, 64, 255))
    for x in (60, 400):
        for y in range(15, 90, 5):
            d.ellipse((x, y, x + 4, y + 5), outline=(74, 70, 80, 255))
    d.ellipse((90, 226, 170, 240), fill=(26, 30, 48, 255)); d.line((100, 232, 150, 232), fill=(70, 80, 120, 255))
    # door frame + stone arch
    d.rectangle((182, 48, 298, 198), fill=(22, 16, 22, 255))
    d.rectangle((188, 54, 292, 198), fill=(4, 3, 6, 255))
    for i, x in enumerate(range(176, 304, 14)):
        d.rectangle((x, 38, x + 12, 47), fill=(54, 50, 62, 255), outline=(20, 18, 24, 255))
    # cobwebs
    for i in range(7):
        d.line((0, 0, 40 - i * 4, 12 + i * 6), fill=(70, 70, 80, 255))
    for r in (10, 18, 26):
        d.arc((-r, -r, r, r), 0, 90, fill=(70, 70, 80, 255))
    return img

def door_panel(w, h):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), fill=(66, 38, 30, 255), outline=(20, 10, 10, 255))
    for x in range(5, w - 2, 11):
        d.line((x, 1, x, h - 2), fill=(50, 28, 22, 255))
    for y in (16, h - 22):
        d.rectangle((0, y, w - 1, y + 5), fill=(44, 42, 50, 255))
        for x in range(4, w - 2, 12):
            d.point((x, y + 2), fill=(130, 126, 140, 255))
    sw = 50
    sx = (w - sw) // 2
    d.rectangle((sx, 34, sx + sw, 64), fill=(176, 166, 136, 255), outline=(40, 30, 20, 255))
    for i, line in enumerate(('BASED', 'GHOUL', 'CRYPT')):
        tw = tiny_w(line)
        tiny(im, (w - tw) // 2, 37 + i * 9, line, (70, 10, 10, 255))
    d.ellipse((w - 24, h // 2 - 2, w - 13, h // 2 + 8), fill=(196, 186, 156, 255), outline=(40, 30, 20, 255))
    d.point((w - 21, h // 2 + 2), fill=(0, 0, 0, 255)); d.point((w - 16, h // 2 + 2), fill=(0, 0, 0, 255))
    d.arc((w - 24, h // 2 + 4, w - 13, h // 2 + 16), 0, 180, fill=(210, 180, 70, 255))
    return im

def basement(t, door_open=0.0, inside=None):
    img = _basement_static().copy()
    dx0, dy0, dx1, dy1 = 188, 54, 292, 198
    if door_open > 0 and inside is not None:
        view = inside.resize((dx1 - dx0, dy1 - dy0), Image.NEAREST)
        img.alpha_composite(view, (dx0, dy0))
    pw = int((dx1 - dx0) * (1 - door_open * .86))
    if pw > 2:
        panel = door_panel(dx1 - dx0, dy1 - dy0).resize((pw, dy1 - dy0), Image.NEAREST)
        img.alpha_composite(panel, (dx0, dy0))
    d = ImageDraw.Draw(img)
    ph = (t * .8) % 1
    d.point((120, 16 + int(ph * 210)), fill=(90, 110, 160, 255))
    return img

def basement_lights(t, door_open=0.0):
    L = np.zeros((H, W, 3), np.float32)
    swing = math.sin(t * 1.3) * 18
    fl = 1.0 if (math.sin(t * 23) + math.sin(t * 7.7)) > -1.6 else .25
    glow(L, 240 + swing, 30, 170, (255, 200, 120), .8 * fl)
    if door_open > 0:
        glow(L, 240, 140, 160, (220, 120, 255), .9 * door_open)
        shaft = Image.new('L', (W, H), 0)
        sd = ImageDraw.Draw(shaft)
        sd.polygon([(188, 198), (292, 198), (400, 270), (80, 270)], fill=int(120 * door_open))
        sh = np.asarray(shaft.filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
        L += sh[..., None] * np.array([.9, .6, 1.0])[None, None]
    return L, swing, fl

def bulb(img, t, swing, fl):
    d = ImageDraw.Draw(img)
    bx = 240 + swing * .6
    d.line((240, 0, bx, 26), fill=(20, 20, 20, 255))
    d.ellipse((bx - 3, 24, bx + 4, 32), fill=(255, 230, 150, 255) if fl > .5 else (90, 80, 60, 255))

# ---------------------------------------------------------------- door side of the crypt (reverse angle)
@lru_cache(None)
def _door_side():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    bricks(img, (0, 0, W, 210), (50, 38, 72), (22, 16, 32), seed=11)
    checker_floor(img, 210, (60, 36, 84), (24, 14, 34), horizon=90)
    d = ImageDraw.Draw(img)
    d.rectangle((160, 30, 320, 211), fill=(30, 20, 26, 255))
    d.rectangle((168, 38, 312, 211), fill=(4, 3, 8, 255))
    for i in range(7):
        d.rectangle((186 + i * 5, 190 - i * 18, 294 - i * 5, 211 - i * 18), fill=(12 + i * 3, 10 + i * 3, 16 + i * 3, 255))
    d.polygon([(168, 38), (196, 48), (196, 200), (168, 211)], fill=(66, 38, 30, 255))
    d.line((196, 48, 196, 200), fill=(30, 14, 10, 255))
    for x, txt, col in ((40, 'WAGMI', (80, 255, 140)), (390, 'NGMI?', (255, 80, 80))):
        d.rectangle((x, 50, x + 50, 86), fill=(16, 16, 30, 255), outline=(200, 200, 220, 255))
        tiny(img, x + 25 - tiny_w(txt, 2) // 2, 63, txt, col + (255,), 2)
    return img

def door_side(t):
    img = _door_side().copy()
    for i, (x, y) in enumerate(((120, 186), (356, 186))):
        candle(img, x, y, t, i)
    return img

def door_lights(t):
    L = np.zeros((H, W, 3), np.float32)
    glow(L, 121, 184, 60, (255, 170, 80), .7)
    glow(L, 357, 184, 60, (255, 170, 80), .7)
    glow(L, 240, 0, 220, (255, 90, 210), .3)
    return L
