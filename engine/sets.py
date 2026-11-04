"""Ep02 v2 set pieces: detailed Cretaceous, abandoned Marsbase lounge, bar close-ups for MINT GHOULIPS."""
import math, random
import numpy as np
from PIL import Image, ImageDraw
from shots import *

def finish(im, outline=(10, 6, 8, 255), rim=None):
    """1px dark outline + optional rim light on right edges (pixel-art finish)."""
    a = np.asarray(im).copy()
    m = a[..., 3] > 0
    grow = m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
    a[grow & ~m] = outline
    if rim:
        r = m & ~np.roll(m, -1, 1)
        a[r, :3] = (a[r, :3] * .5 + np.array(rim) * .5).astype(np.uint8)
    return Image.fromarray(a)

def stand(img, name, x, ground, pose='idle', expr='neutral', scale=2, flip=False, marks=(), mouth=0, t=0.0, hop=0, legs=True, dim=1.0):
    """Place a ghoul with its FEET on `ground` (fixes floating characters)."""
    ch, an = FC.character(name, pose, expr, mouth=mouth, t=t, marks=marks, legs=legs)
    if dim != 1.0:
        a = np.asarray(ch).astype(float).copy(); a[..., :3] *= dim; ch = Image.fromarray(a.astype(np.uint8))
    big = iscale(ch, scale)
    fx, fy = an['feet']
    if flip:
        big = big.transpose(Image.FLIP_LEFT_RIGHT)
        fx = ch.width - fx
    paste(img, big, x - fx * scale, ground - (fy + 1) * scale - hop)
    return an

# ======================================================================= CRETACEOUS
def trex(t, run=True, mouth=0.0, scale=3, blink=False):
    """Detailed side-view T-rex (native 100x66), facing right."""
    im = Image.new('RGBA', (100, 66), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    g, gd, gl, belly = (78, 120, 58), (46, 78, 38), (118, 160, 84), (196, 186, 132)
    ph = math.sin(t * 14) if run else 0
    bob = int(abs(ph) * 2) if run else 0
    # far leg
    hx = 46
    kx = hx - 6 * ph
    d.polygon([(hx - 6, 34 + bob), (hx + 6, 34 + bob), (kx + 4, 50), (kx - 4, 50)], fill=gd)
    d.line((kx, 50, kx + 6 * ph + 4, 62), fill=gd, width=5)
    d.line((kx + 6 * ph, 62, kx + 6 * ph + 10, 62), fill=gd, width=3)
    # tail + body
    d.polygon([(0, 22 + bob), (20, 18 + bob), (40, 16 + bob), (60, 18 + bob), (70, 26 + bob), (64, 40 + bob), (44, 44 + bob), (28, 38 + bob), (12, 30 + bob)], fill=g)
    d.polygon([(30, 36 + bob), (44, 43 + bob), (62, 40 + bob), (66, 32 + bob), (50, 36 + bob)], fill=belly)
    for i in range(7):                                                                   # back stripes
        x = 16 + i * 7
        d.line((x, 18 + bob, x + 3, 25 + bob), fill=gd, width=2)
    # neck + head
    d.polygon([(60, 18 + bob), (72, 10 + bob), (78, 18 + bob), (70, 30 + bob)], fill=g)
    d.polygon([(70, 6 + bob), (88, 4 + bob), (98, 9 + bob), (98, 15 + bob), (84, 17 + bob), (72, 18 + bob)], fill=g)
    d.line((72, 6 + bob, 88, 5 + bob), fill=gl)                                           # skull ridge highlight
    jaw = 2 + int(mouth * 9)
    d.polygon([(76, 17 + bob), (98, 15 + bob), (96, 17 + bob + jaw), (80, 20 + bob + jaw // 2)], fill=gd)
    if jaw > 3:
        d.polygon([(80, 17 + bob), (96, 15 + bob), (95, 16 + bob + jaw), (82, 19 + bob + jaw // 2)], fill=(120, 30, 40))
    for x in range(79, 97, 3):
        d.polygon([(x, 15 + bob), (x + 2, 15 + bob), (x + 1, 18 + bob)], fill=(245, 240, 220))
        if jaw > 3:
            d.polygon([(x, 16 + bob + jaw), (x + 2, 16 + bob + jaw), (x + 1, 13 + bob + jaw)], fill=(245, 240, 220))
    d.rectangle((95, 9 + bob, 96, 10 + bob), fill=(30, 20, 20))                            # nostril
    d.line((82, 7 + bob, 87, 8 + bob), fill=gd, width=2)                                   # brow ridge
    if not blink:
        d.rectangle((83, 9 + bob, 85, 11 + bob), fill=(255, 210, 0)); d.point((84, 10 + bob), fill=(20, 10, 0))
    # tiny arm
    d.line((66, 30 + bob, 72, 34 + bob), fill=gd, width=3); d.line((72, 34 + bob, 74, 32 + bob), fill=(245, 240, 220))
    # near leg (big thigh)
    kx = hx + 6 * ph
    d.ellipse((hx - 10, 26 + bob, hx + 12, 46 + bob), fill=g)
    d.polygon([(hx - 4, 42 + bob), (hx + 6, 42 + bob), (kx + 5, 52), (kx - 3, 52)], fill=g)
    d.line((kx, 52, kx - 6 * ph + 2, 63), fill=g, width=6)
    d.line((kx - 6 * ph, 63, kx - 6 * ph + 12, 63), fill=g, width=3)
    for c in range(3):
        d.point((kx - 6 * ph + 8 + c * 2, 64), fill=(240, 236, 210))
    return iscale(finish(im, rim=(255, 220, 160)), scale)

def ptero(t, scale=2, seed=0):
    im = Image.new('RGBA', (44, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    wing = int(math.sin(t * 8 + seed) * 6)
    c, cd = (170, 100, 80), (120, 64, 52)
    d.polygon([(2, 8 - wing), (20, 9), (22, 11), (14, 11)], fill=c)
    d.polygon([(42, 8 - wing), (24, 9), (22, 11), (30, 11)], fill=cd)
    d.polygon([(16, 9), (28, 8), (38, 10), (26, 12)], fill=cd)
    d.polygon([(30, 7), (40, 5), (36, 8)], fill=c)                                          # crest
    return iscale(finish(im), scale)

def brachio(scale=1, col=(70, 60, 90)):
    im = Image.new('RGBA', (80, 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((10, 36, 60, 62), fill=col)
    d.line((52, 44, 70, 6), fill=col, width=7); d.ellipse((64, 0, 78, 10), fill=col)
    d.line((14, 50, 0, 58), fill=col, width=5)
    for x in (18, 28, 44, 52):
        d.rectangle((x, 56, x + 5, 70), fill=col)
    return iscale(im, scale)

def cycad(d, x, y, s, col=(40, 110, 50), trunk=(96, 66, 40)):
    d.line((x, y, x + 2 * s, y - 34 * s), fill=trunk, width=int(max(2, 4 * s)))
    for k in range(int(4 * s) + 1):
        d.line((x + 2 * s - 2, y - (8 + k * 7) * s, x + 2 * s + 2, y - (8 + k * 7) * s), fill=(70, 46, 28), width=1)
    top = (x + 2 * s, y - 34 * s)
    for k in range(9):
        a = -math.pi + k * math.pi / 8
        ln = (24 + (k % 3) * 6) * s
        tip = (top[0] + math.cos(a) * ln, top[1] + math.sin(a) * ln * .5 + ln * .25)
        d.line((top, tip), fill=col, width=max(2, int(3 * s)))
        for j in range(1, 4):
            px, py = top[0] + (tip[0] - top[0]) * j / 4, top[1] + (tip[1] - top[1]) * j / 4
            d.line((px, py, px + 3 * s * math.cos(a + 1.2), py + 3 * s * math.sin(a + 1.2) + 2 * s), fill=col, width=1)

def fern(d, x, y, s, col):
    for k in range(7):
        a = -math.pi * .95 + k * math.pi * .9 / 6
        ln = 22 * s
        tip = (x + math.cos(a) * ln, y + math.sin(a) * ln)
        d.line((x, y, tip[0], tip[1]), fill=col, width=max(2, int(2 * s)))
        for j in range(1, 5):
            px, py = x + (tip[0] - x) * j / 5, y + (tip[1] - y) * j / 5
            d.line((px, py, px + math.cos(a - .9) * 4 * s, py + math.sin(a - .9) * 4 * s), fill=col, width=1)

def prehistoric_bg(t, scroll=0.0, fg=True, ground=212):
    img = Wd.vgrad(W, H, [(0, (255, 132, 90)), (.38, (255, 196, 128)), (.62, (255, 222, 160)), (1, (210, 150, 90))])
    d = ImageDraw.Draw(img)
    d.ellipse((60, 40, 104, 84), fill=(255, 238, 190)); d.ellipse((66, 46, 98, 78), fill=(255, 250, 225))
    for i in range(5):                                                                   # clouds
        cx = (i * 120 - scroll * .05 + t * 3) % (W + 120) - 60
        for k in range(4):
            d.ellipse((cx + k * 14, 30 + i % 2 * 18 - (k % 2) * 6, cx + k * 14 + 26, 44 + i % 2 * 18), fill=(255, 220, 190))
    o1 = scroll * .15
    pts = [(x, 132 + 18 * math.sin((x + o1) / 47) + 8 * math.sin((x + o1) / 17)) for x in range(-4, W + 8, 4)]
    d.polygon(pts + [(W, H), (0, H)], fill=(186, 120, 110))                                     # far ridge
    vx = 330 - o1 % 900 if (330 - o1) > -200 else 330
    d.polygon([(vx - 90, 160), (vx - 12, 54), (vx + 12, 54), (vx + 90, 160)], fill=(110, 62, 56))   # volcano
    d.polygon([(vx - 12, 54), (vx + 12, 54), (vx + 8, 64), (vx - 8, 64)], fill=(255, 110, 30))
    d.line((vx - 4, 64, vx - 10, 90, vx - 6, 110), fill=(255, 140, 40), width=2)
    for i in range(8):
        ph = (t * .25 + i / 8) % 1
        r = 6 + ph * 18
        cx, cy = vx + math.sin(i * 1.7 + t * .5) * 10 + ph * 20, 50 - ph * 70
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(90, 70, 70, int(180 * (1 - ph))))
    for i, bx in enumerate((150, 230)):                                                 # brachiosaurs in the haze
        b = brachio(1, (150, 100, 110))
        paste(img, b, bx - o1 * .8 % 600 if False else bx - (scroll * .25) % 700, 148 - b.height + 10 + i * 4)
    o2 = scroll * .45
    pts = [(x, 168 + 10 * math.sin((x + o2) / 31)) for x in range(-4, W + 8, 4)]
    d.polygon(pts + [(W, H), (0, H)], fill=(84, 120, 70))                                       # mid jungle mass
    for i in range(12):
        x = (i * 46 - o2) % (W + 80) - 40
        cycad(d, x, 190, .9 + (i % 3) * .15, (52 + (i % 3) * 10, 116, 58))
    # ground
    d.rectangle((0, ground, W, H), fill=(146, 106, 62))
    for i in range(60):
        x = (i * 37 - scroll) % W
        y = ground + 4 + (i * 13) % (H - ground - 6)
        d.line((x, y, x + 3, y), fill=(120, 86, 50))
    for i in range(10):                                                                  # rocks + a fossil bone joke
        x = (i * 71 - scroll) % (W + 40) - 20
        d.ellipse((x, ground + 6 + (i % 3) * 8, x + 14, ground + 14 + (i % 3) * 8), fill=(120, 110, 100), outline=(70, 60, 56))
    for x in range(0, W, 9):
        xx = (x - scroll) % W
        d.line((xx, ground, xx + 3, ground - 6), fill=(80, 140, 60), width=2)
    # dragonflies
    for i in range(3):
        x = (t * 50 * (1 + i * .3) + i * 140) % W
        y = 120 + math.sin(t * 3 + i) * 14 + i * 12
        d.line((x - 3, y, x + 3, y), fill=(40, 160, 200)); d.point((x, y - 1), fill=(200, 255, 255))
    if fg:                                                                               # dark foreground ferns (parallax)
        o3 = scroll * 1.6
        for i in range(6):
            x = (i * 110 - o3) % (W + 160) - 80
            fern(d, x, H + 6, 2.2, (30, 64, 30))
    L = np.zeros((H, W, 3), np.float32)
    Wd.glow(L, 82, 62, 240, (255, 210, 150), .35)
    Wd.glow(L, vx, 56, 60, (255, 120, 40), .5)
    return Wd.apply_light(img, L, 1.0)

def puddle_close(t, boom):
    img = Wd.vgrad(W, H, [(0, (80, 70, 50)), (1, (60, 50, 36))])
    d = ImageDraw.Draw(img)
    d.ellipse((60, 60, 420, 230), fill=(70, 110, 120), outline=(40, 34, 26), width=4)
    d.ellipse((80, 76, 400, 214), fill=(100, 150, 170))
    for k in range(4):                                                                  # reflection of sky + fern
        d.line((140 + k * 30, 110, 170 + k * 30, 180), fill=(130, 180, 190), width=2)
    for i in range(4):                                                                  # concentric ripples
        r = ((boom * 3 + i * .25) % 1) * 150
        if r > 4:
            d.ellipse((240 - r, 145 - r * .38, 240 + r, 145 + r * .38), outline=(210, 240, 250), width=2)
    for i in range(10):
        x = 50 + i * 40
        fern(d, x, 260, 1.4, (50, 90, 40))
    return img

def cave(d, x, y, s=1):
    d.pieslice((x - 110 * s, y - 120 * s, x + 110 * s, y + 100 * s), 180, 360, fill=(96, 72, 60))
    d.pieslice((x - 96 * s, y - 104 * s, x + 96 * s, y + 90 * s), 180, 360, fill=(78, 58, 50))
    d.pieslice((x - 62 * s, y - 74 * s, x + 62 * s, y + 70 * s), 180, 360, fill=(10, 6, 8))
    for k in range(5):
        d.polygon([(x - 50 * s + k * 24 * s, y - 70 * s), (x - 44 * s + k * 24 * s, y - 70 * s), (x - 47 * s + k * 24 * s, y - 56 * s)], fill=(90, 70, 60))

# ======================================================================= MARSBASE (abandoned lounge)
def mars_ruins_bg(t):
    img = Wd.vgrad(W, H, [(0, (34, 16, 34)), (.55, (120, 56, 56)), (1, (170, 90, 66))])
    d = ImageDraw.Draw(img)
    # window band: Mars outside + Earth in the sky
    d.rectangle((0, 18, W, 120), fill=(196, 104, 72))
    pts = [(x, 92 + 10 * math.sin(x / 37) + 4 * math.sin(x / 9)) for x in range(0, W + 4, 4)]
    d.polygon(pts + [(W, 120), (0, 120)], fill=(150, 66, 44))
    d.ellipse((380, 30, 404, 54), fill=(70, 120, 210)); d.ellipse((386, 34, 396, 44), fill=(90, 170, 90))
    for i in range(30):
        d.point(((i * 61) % W, 22 + (i * 17) % 40), fill=(255, 230, 220))
    # window frames + cracked panes
    for x in range(0, W + 1, 60):
        d.rectangle((x - 3, 14, x + 3, 124), fill=(170, 180, 186)); d.line((x - 2, 14, x - 2, 124), fill=(220, 230, 236))
    d.rectangle((0, 12, W, 18), fill=(150, 160, 166)); d.rectangle((0, 120, W, 128), fill=(150, 160, 166))
    for (cx, cy) in ((150, 50), (330, 80)):
        for k in range(6):
            a = k * 1.05 + .3
            d.line((cx, cy, cx + math.cos(a) * 26, cy + math.sin(a) * 20), fill=(240, 240, 250), width=1)
    # interior wall + ceiling garden pipes
    d.rectangle((0, 128, W, 200), fill=(92, 56, 66))
    for x in range(0, W, 24):
        d.line((x, 128, x, 200), fill=(80, 48, 58))
    # dead neon sign
    fl = 1 if (math.sin(t * 17) + math.sin(t * 5.3)) > 1.2 else 0
    Wd.tiny(img, 120, 140, 'BASED GHOUL CRYPT', (255, 90, 210, 255) if fl else (110, 60, 90, 255), 2)
    Wd.tiny(img, 270, 156, 'MARS', (255, 90, 210, 255) if fl else (110, 60, 90, 255), 2)
    # faded welcome banner hanging by one corner
    d.polygon([(150, 28), (330, 28), (326, 46), (154, 46)], fill=(220, 210, 190))
    Wd.tiny(img, 162, 34, 'WELCOME TO MARSBASE', (150, 60, 50, 255), 2)
    d.line((330, 28, 344, 54), fill=(220, 210, 190), width=2)
    # broken arcade cabinet + framed photo + hanging planters
    d.rectangle((30, 140, 56, 200), fill=(50, 30, 80), outline=(20, 10, 30)); d.rectangle((34, 146, 52, 164), fill=(10, 14, 20))
    d.line((36, 148, 50, 162), fill=(160, 200, 220)); d.line((50, 148, 40, 158), fill=(160, 200, 220))
    d.rectangle((420, 140, 452, 166), fill=(90, 60, 30), outline=(40, 24, 10)); d.rectangle((424, 144, 448, 162), fill=(200, 170, 140))
    for k, cx in enumerate((428, 436, 444)):
        d.ellipse((cx - 3, 148, cx + 3, 154), fill=(220, 214, 196))
    for x in (90, 380):
        d.line((x, 18, x, 60), fill=(60, 50, 50))
        d.polygon([(x - 10, 60), (x + 10, 60), (x + 6, 72), (x - 6, 72)], fill=(150, 90, 60))
        for k in range(6):
            d.line((x - 8 + k * 3, 66, x - 10 + k * 4, 96 + (k % 3) * 10), fill=(70, 170, 130), width=2)
            d.ellipse((x - 11 + k * 4, 94 + (k % 3) * 10, x - 7 + k * 4, 98 + (k % 3) * 10), fill=(220, 130, 230))
    # floor: tiles half buried in sand drifts
    d.rectangle((0, 200, W, H), fill=(150, 110, 100))
    for x in range(0, W, 20):
        for y in range(200, H, 12):
            d.rectangle((x + (y // 12 % 2) * 10, y, x + 18 + (y // 12 % 2) * 10, y + 10), outline=(130, 92, 84))
    for x in range(-40, W, 70):
        d.pieslice((x, 196, x + 110, 260), 180, 360, fill=(176, 96, 66))
    # overgrown alien plants
    for i, x in enumerate((14, 104, 446)):
        for k in range(6):
            d.line((x, 210, x + (k - 2.5) * 8, 160 + (k % 2) * 14), fill=(60, 180, 160), width=3)
            d.ellipse((x + (k - 2.5) * 8 - 3, 156 + (k % 2) * 14, x + (k - 2.5) * 8 + 3, 162 + (k % 2) * 14), fill=(210, 130, 230))
    # scattered cups
    for x in (200, 214, 300):
        d.rectangle((x, 236, x + 6, 244), fill=(200, 205, 215), outline=(90, 90, 100))
    return img

def dust(img, t, n=40, seed=4):
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    for i in range(n):
        x = (rnd.random() * W + t * 8 * (1 + rnd.random())) % W
        y = (rnd.random() * H + math.sin(t + i) * 10) % H
        d.point((x, y), fill=(255, 230, 200, 170))

def light_shafts(img, k=.6):
    from PIL import ImageFilter
    L = np.zeros((H, W, 3), np.float32)
    shaft = Image.new('L', (W, H), 0)
    sd = ImageDraw.Draw(shaft)
    for x0 in (110, 250, 360):
        sd.polygon([(x0, 18), (x0 + 40, 18), (x0 + 120, H), (x0 + 60, H)], fill=60)
    sh = np.asarray(shaft.filter(ImageFilter.GaussianBlur(8))).astype(np.float32) / 255
    L += sh[..., None] * np.array([1.0, .82, .66])[None, None] * k
    Wd.glow(L, 392, 42, 40, (120, 170, 255), .5)
    return Wd.apply_light(img, L, 1.0)

# ======================================================================= the bar (MINT GHOULIPS close-ups)
def bar_bg(t):
    """Blurred Mars lounge behind a wooden bar counter."""
    bg = light_shafts(mars_ruins_bg(t), .5)
    small = bg.resize((W // 6, H // 6), Image.BOX).resize((W, H), Image.BILINEAR)
    img = small.convert('RGBA')
    d = ImageDraw.Draw(img)
    for i in range(10):                                                                # bokeh
        x, y, r = (i * 53) % W, 30 + (i * 37) % 120, 5 + i % 3 * 3
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 200, 150, 28))
    d.rectangle((0, 242, W, H), fill=(110, 64, 40))
    for y in range(246, H, 6):
        d.line((0, y, W, y + (y % 12) // 6), fill=(96, 54, 34))
    d.line((0, 242, W, 242), fill=(170, 112, 76), width=2)
    return img

def tin(img, x, base, t, frost=0.0, fill=0.0, liquid=(200, 160, 90)):
    """Julep tin with metallic bands; frost 0..1 creeps up; fill 0..1 liquid level."""
    w0, w1, h = 46, 36, 112
    d = ImageDraw.Draw(img)
    top, bot = base - h, base
    d.polygon([(x - w0, top), (x + w0, top), (x + w1, bot), (x - w1, bot)], fill=(176, 182, 192), outline=(70, 72, 80))
    for k, (o, c) in enumerate(((-30, (220, 226, 236)), (-22, (240, 244, 250)), (14, (150, 156, 166)), (26, (196, 202, 212)))):
        d.line((x + o, top + 4, x + o * w1 / w0, bot - 3), fill=c, width=3)
    d.ellipse((x - w0, top - 6, x + w0, top + 6), fill=(120, 124, 134), outline=(70, 72, 80))
    if fill > 0:
        ly = bot - (h - 10) * fill
        d.ellipse((x - w0 + 6, ly - 4, x + w0 - 6, ly + 4), fill=liquid + (255,))
    if frost > 0:
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        fy = bot - h * frost
        ld.polygon([(x - w1 - (w0 - w1) * (bot - fy) / h, fy), (x + w1 + (w0 - w1) * (bot - fy) / h, fy), (x + w1, bot), (x - w1, bot)], fill=(225, 238, 252, 85))
        img.alpha_composite(lay)
        for o, c in ((-22, (250, 252, 255)), (26, (210, 220, 232))):
            d.line((x + o, max(fy, top + 4), x + o * w1 / w0, bot - 3), fill=c, width=2)
        for j in range(int(10 * frost)):                                                # condensation drops
            yy = bot - 6 - (j * 23) % int(max(8, h * frost - 8))
            xx = x - w1 + 6 + (j * 29) % (2 * w1 - 12)
            d.line((xx, yy, xx, yy + 4), fill=(255, 255, 255)); d.point((xx, yy + 5), fill=(170, 210, 240))
        rnd = random.Random(7)
        for i in range(int(90 * frost)):                                                 # frost crystals
            yy = bot - rnd.random() * h * frost
            xx = x + (rnd.random() - .5) * 2 * (w1 + (w0 - w1) * (bot - yy) / h)
            d.line((xx - 2, yy, xx + 2, yy), fill=(255, 255, 255)); d.line((xx, yy - 2, xx, yy + 2), fill=(255, 255, 255))
    return top

def ice_dome(d, x, top, k=1.0, w=46, hgt=30):
    """Crushed-ice mound: soft dome body + individual faceted chips."""
    hh = hgt * k
    if hh < 2:
        return
    d.pieslice((x - w, top - hh, x + w, top + hh), 180, 360, fill=(226, 240, 252), outline=(150, 186, 220))
    rnd = random.Random(3)
    for i in range(int(70 * k)):
        a = rnd.random() * math.pi
        r = rnd.random() ** .5
        cx = x + math.cos(a) * w * r * .95
        cy = top - math.sin(a) * hh * r * .95
        sz = rnd.choice((3, 4, 5))
        d.polygon([(cx, cy - sz), (cx + sz, cy), (cx + 1, cy + sz - 1), (cx - sz, cy)], fill=(248, 252, 255), outline=(170, 200, 230))
        if rnd.random() < .3:
            d.point((cx - 1, cy - 1), fill=(255, 255, 255))

def mint_top(d, x, y, s=7):
    """The GHOULIPS signature: two bright pixel mint leaves on the ice dome."""
    d.rectangle((x + 4, y - s * 2, x + 4 + s * 2, y), fill=(0, 200, 30), outline=(0, 120, 20))
    d.rectangle((x + 4 + s * 2, y - s * 3, x + 4 + s * 3, y - s * 2), fill=(30, 220, 40), outline=(0, 130, 20))
    d.rectangle((x - s * 2, y - s * 1, x, y), fill=(40, 150, 60), outline=(0, 100, 20))
    d.point((x + 6, y - s * 2 + 2), fill=(170, 255, 170))

def mint_leaf(d, x, y, a, s=1.0, col=(66, 176, 76)):
    ca, sa = math.cos(a), math.sin(a)
    pts = []
    for k in range(9):
        u = k / 8 * math.pi
        px, py = math.cos(u) * 9 * s, math.sin(u) * 4 * s
        pts.append((x + px * ca - py * sa, y + px * sa + py * ca))
    for k in range(9):
        u = math.pi + k / 8 * math.pi
        px, py = math.cos(u) * 9 * s, math.sin(u) * 4 * s
        pts.append((x + px * ca - py * sa, y + px * sa + py * ca))
    d.polygon(pts, fill=col, outline=(30, 96, 40))
    d.line((x - 8 * s * ca, y - 8 * s * sa, x + 8 * s * ca, y + 8 * s * sa), fill=(150, 220, 140))

def skull_bottle(kind, scale=2):
    """KAH Añejo = painted day-of-the-dead skull; Crystal Head = clear glass skull."""
    im = Image.new('RGBA', (56, 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if kind == 'kah':
        body, eye = (236, 226, 206), (40, 20, 30)
        d.ellipse((4, 18, 52, 66), fill=body, outline=(80, 60, 50))
        d.rectangle((14, 56, 42, 74), fill=body, outline=(80, 60, 50))
        for (cx, c) in ((16, (230, 60, 80)), (40, (60, 140, 220))):
            d.ellipse((cx - 8, 34, cx + 8, 48), fill=c); d.ellipse((cx - 4, 38, cx + 4, 44), fill=eye)
        for k in range(5):
            d.ellipse((10 + k * 8, 22, 14 + k * 8, 26), fill=(240, 180, 40))
        d.polygon([(28, 48), (24, 56), (32, 56)], fill=eye)
        for x in range(18, 40, 4):
            d.line((x, 62, x, 70), fill=(80, 60, 50))
        d.rectangle((22, 4, 34, 18), fill=(30, 20, 20)); d.rectangle((20, 0, 36, 6), fill=(200, 160, 60))
    else:
        d.ellipse((4, 18, 52, 66), fill=(200, 226, 240, 170), outline=(120, 150, 170))
        d.rectangle((14, 56, 42, 74), fill=(200, 226, 240, 170), outline=(120, 150, 170))
        for cx in (16, 40):
            d.ellipse((cx - 8, 34, cx + 8, 48), fill=(150, 180, 200, 200))
        d.polygon([(28, 48), (24, 56), (32, 56)], fill=(150, 180, 200, 200))
        d.line((12, 26, 18, 52), fill=(255, 255, 255), width=2)
        d.rectangle((22, 4, 34, 18), fill=(180, 210, 230, 200)); d.rectangle((20, 0, 36, 6), fill=(60, 60, 70))
    return iscale(im, scale)

def muddler(img, x, y, scale=3):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x - 5 * scale // 2, y - 60 * scale // 2, x + 5 * scale // 2, y), 4, fill=(160, 108, 66), outline=(80, 50, 30))
    d.line((x - 2, y - 58 * scale // 2, x - 2, y - 2), fill=(196, 140, 92))

def kitchen_close(f, step, ghoul):
    """Five recipe steps as detailed anime food-show close-ups, with a bony hand from `ghoul`."""
    img = bar_bg(f.T)
    E.speed_radial(img, f.T, 240, 110, (255, 240, 210), n=36, inner=150)
    d = ImageDraw.Draw(img)
    x, base = 240, 246
    k = min(1.0, f.t / max(.1, f.d))
    if step == 1:                                     # WAKE THE MINT: syrup + leaves, gentle press
        top = tin(img, x, base, f.T, fill=.12, liquid=(240, 230, 200))
        if f.t < .8:                                   # syrup ribbon from a little jug
            d.polygon([(330, 60), (366, 60), (360, 96), (336, 96)], fill=(240, 240, 236), outline=(120, 120, 120))
            d.line((332, 70, x + 6, top + 8), fill=(250, 240, 210), width=4)
            Wd.tiny(img, 330, 100, 'SYRUP 10ML', (255, 255, 255, 255), 2)
        for i in range(9):
            mint_leaf(d, x - 28 + (i % 5) * 14, top + 6 + (i // 5) * 4, .3 * i, 1.0)
        press = abs(math.sin(f.t * 3.2)) if f.t > .8 else 0
        mud_y = top + 4 + int(press * 10)
        muddler(img, x, mud_y, 3)
        hand(img, x, mud_y - 88, ghoul, 3)
        if press > .8:                                 # aroma swirls
            for j in range(3):
                d.arc((x - 40 + j * 24, top - 50 - j * 8, x - 16 + j * 24, top - 26 - j * 8), 200, 340, fill=(160, 240, 170), width=2)
    elif step == 2:                                   # SUMMON THE SPIRITS: two skull bottles
        top = tin(img, x, base, f.T, fill=.15 + .35 * k, liquid=(214, 170, 90))
        for i in range(9):
            mint_leaf(d, x - 28 + (i % 5) * 14, top + 30 + (i // 5) * 4, .3 * i, .9, (50, 140, 60))
        first = f.t < f.d * .5
        b = skull_bottle('kah' if first else 'crystal', 2)
        b = b.rotate(-120 if first else 120, Image.NEAREST, expand=True)
        bx = x - 150 if first else x + 40
        paste(img, b, bx, 0)
        sx = bx + (b.width - 20 if first else 20)
        d.line((sx, 70, x + (8 if first else -8), top + 6), fill=((214, 160, 80) if first else (230, 240, 250)), width=5)
        E.title_text(f, 140 if first else 820, 470, '45ml KAH AÑEJO' if first else '15ml CRYSTAL HEAD', 28, (255, 255, 255), (60, 30, 10), 4)
        for j in range(5):                             # splash droplets
            ph = (f.T * 3 + j * .2) % 1
            d.ellipse((x - 20 + j * 10, top - ph * 20, x - 16 + j * 10, top - ph * 20 + 4), fill=(240, 220, 160))
    elif step == 3:                                   # BRING THE CHILL: ice + stir + frost creeping
        top = tin(img, x, base, f.T, frost=min(1, f.t / max(.1, f.d) * 1.3), fill=.55, liquid=(214, 170, 90))
        ice_dome(d, x, top, .35)
        sp = (f.t * 2.4) % 1
        spx = x + 26 * math.cos(sp * math.tau)
        d.line((spx, top - 70, spx * .5 + x * .5, top + 10), fill=(210, 214, 222), width=4)
        hand(img, int(spx), top - 66, ghoul, 3)
        if f.t > f.d * .6:
            E.sfx_text(f, 760, 160, 'キンキン！', 60, (200, 240, 255), (20, 60, 100), 5, rot=8)
    elif step == 4:                                   # RAISE THE MOUND: ice dome
        top = tin(img, x, base, f.T, frost=1.0)
        ice_dome(d, x, top, .35 + .65 * min(1, k * 1.4))
        sc_y = top - 70 + int(abs(math.sin(f.t * 5)) * 14)
        d.polygon([(x + 40, sc_y + 10), (x + 76, sc_y + 2), (x + 80, sc_y + 16), (x + 46, sc_y + 22)], fill=(200, 205, 215), outline=(90, 90, 100))   # ice scoop
        for j in range(6):
            d.rectangle((x + 48 + j * 5, sc_y + 6, x + 52 + j * 5, sc_y + 10), fill=(248, 252, 255), outline=(170, 200, 230))
        hand(img, x + 66, sc_y - 2, ghoul, 3)
    else:                                             # FINISH WITH MINT: slap, sprig, straw
        top = tin(img, x, base, f.T, frost=1.0)
        ice_dome(d, x, top, 1.0)
        if f.t < f.d * .35:
            for i in range(7):
                mint_leaf(d, 330 + i * 8, 90 + (i % 2) * 8, 1.2 + i * .2, 1.6)
            E.sfx_text(f, 700, 200, 'パンッ！', 80, (255, 255, 255), (30, 110, 50), 6, shake=3)
            for j in range(8):
                a = j * math.tau / 8
                d.line((340 + math.cos(a) * 30, 100 + math.sin(a) * 30, 340 + math.cos(a) * 46, 100 + math.sin(a) * 46), fill=(180, 255, 190), width=2)
        else:
            d.line((x + 20, top - 58, x + 14, top - 14), fill=(240, 80, 80), width=5)          # short straw
            d.line((x + 21, top - 58, x + 15, top - 14), fill=(255, 170, 170), width=1)
            d.line((x - 10, top - 26, x - 14, top - 58), fill=(70, 120, 50), width=2)          # sprig stem
            for i, (lx, ly, a) in enumerate(((-14, -58, -.6), (-8, -54, .5), (-18, -48, -1.1), (-6, -44, .9), (-16, -38, -.4), (-10, -32, .3))):
                mint_leaf(d, x + lx, top + ly, a, 1.3 - i * .05)
            E.sparkles(img, f.T, 30, color=(255, 255, 230))
    # colour wash per spirit + measuring jigger + layered cutaway
    if step == 2:
        first = f.t < f.d * .5
        wash = Image.new('RGBA', img.size, ((255, 170, 60, 38) if first else (140, 200, 255, 38)))
        img.alpha_composite(wash)
        jl = min(1, ((f.t if first else f.t - f.d * .5) / (f.d * .4)))
        jigger(img, 400 if first else 80, 180, jl, (214, 150, 60, 255) if first else (215, 235, 250, 255), 2)
    if step == 1:
        jigger(img, 400, 180, min(1, f.t / .6), (240, 214, 140, 255), 2)
    if step >= 1:
        lay = [(.10, (240, 214, 140), 'SYRUP'), (.08, (80, 176, 86), 'MINT')]
        if step >= 2:
            lay += [(.30 * (min(1, k * 2) if step == 2 else 1), (214, 150, 60), 'KAH'),
                    (.10 * (max(0, k * 2 - 1) if step == 2 else 1), (205, 228, 245), 'CRYSTAL')]
        if step >= 3:
            lay += [(.22 if step == 3 else .34, (236, 246, 255), 'ICE')]
        pass
    E.sparkles(img, f.T, 10, seed=step)
    return img

# ======================================================================= v3: cave from the inside
def cave_inside(t, snout=0.0):
    """Looking OUT of the cave: bright jungle framed by a dark, craggy mouth; snout 0..1 = T-rex head poking in."""
    img = prehistoric_bg(t, scroll=1300, fg=False)
    d = ImageDraw.Draw(img)
    if snout > 0:
        rx = trex(t, run=False, mouth=.15 + .1 * math.sin(t * 6), scale=7).transpose(Image.FLIP_LEFT_RIGHT)
        paste(img, rx, lerp(W + 40, 170, snout), 40 - int(math.sin(t * 3) * 4))
    mask = Image.new('L', (W, H), 255)
    md = ImageDraw.Draw(mask)
    pts = [(70, H), (60, 200), (80, 140), (110, 96), (150, 70), (200, 56), (260, 54), (320, 66), (370, 92), (402, 136), (420, 190), (414, H)]
    md.polygon(pts, fill=0)
    rock = Wd.vgrad(W, H, [(0, (40, 30, 34)), (1, (18, 12, 14))])
    rd = ImageDraw.Draw(rock)
    rnd = random.Random(12)
    for i in range(140):                                                     # strata + cracks
        x, y = rnd.randrange(W), rnd.randrange(H)
        rd.line((x, y, x + rnd.randint(8, 30), y + rnd.randint(-3, 3)), fill=(56, 42, 46))
    for i in range(16):                                                      # stalactites on the rim
        x = 100 + i * 20
        y = 60 + abs(math.sin(i * 1.3)) * 30
        rd.polygon([(x - 6, y - 10), (x + 6, y - 10), (x, y + 14 + (i % 3) * 6)], fill=(50, 38, 40))
    for i in range(10):                                                      # hanging vines + moss
        x = 110 + i * 30
        rd.line((x, 60, x + math.sin(t * 1.5 + i) * 3, 90 + (i % 4) * 14), fill=(50, 110, 50), width=2)
        rd.ellipse((x - 8, 54, x + 8, 64), fill=(56, 96, 48))
    img.paste(rock, (0, 0), mask)
    L = np.zeros((H, W, 3), np.float32)
    Wd.glow(L, 240, 170, 220, (255, 210, 150), .5)
    return Wd.apply_light(img, L, .9)

# ======================================================================= v3: detailed skull-ban megacity
_KANJI = ['骸骨禁止', '監視中', '秩序', '和諧', '繁栄', '安全第一', '健全', '文明']

def china_bg(t, scroll=0.0, rain=True):
    from PIL import ImageFont
    fnt = ImageFont.truetype(os.path.join(paths.FONTS, 'DotGothic16.ttf'), 16)
    img = Wd.vgrad(W, H, [(0, (8, 4, 22)), (.5, (40, 10, 40)), (1, (70, 16, 36))])
    d = ImageDraw.Draw(img)
    rnd = random.Random(8)
    o1 = scroll * .2
    for i in range(18):                                                      # far skyline + antennas
        x0 = (i * 30 - o1) % (W + 60) - 30
        h = 60 + (i * 37) % 90
        d.rectangle((x0, 170 - h, x0 + 26, 200), fill=(30, 16, 44))
        d.line((x0 + 13, 170 - h, x0 + 13, 160 - h), fill=(60, 30, 70))
        if int(t * 2 + i) % 4 == 0:
            d.point((x0 + 13, 159 - h), fill=(255, 40, 40))
    o2 = scroll * .5
    for i in range(9):                                                       # mid towers with lit windows + vertical neon
        x0 = (i * 62 - o2) % (W + 120) - 60
        h = 120 + (i * 53) % 70
        d.rectangle((x0, 216 - h, x0 + 50, 230), fill=(22, 12, 30), outline=(40, 22, 50))
        r2 = random.Random(i)
        for k in range(24):
            if r2.random() < .5:
                wx, wy = x0 + 4 + (k % 4) * 11, 222 - h + (k // 4) * 14
                d.rectangle((wx, wy, wx + 6, wy + 6), fill=r2.choice([(255, 200, 90), (120, 220, 255), (255, 90, 120)]))
        txt = _KANJI[i % len(_KANJI)]
        col = [(255, 60, 90), (90, 240, 255), (255, 210, 60)][i % 3]
        fl = 1 if (math.sin(t * 9 + i * 2) > -.8) else .3
        for c_i, ch in enumerate(txt):
            d.text((x0 + 52, 230 - h + c_i * 16), ch, font=fnt, fill=tuple(int(v * fl) for v in col))
    # elevated rail + passing maglev
    d.rectangle((0, 138, W, 142), fill=(70, 60, 80))
    for x in range(0, W, 40):
        d.rectangle((x - int(o2) % 40, 142, x - int(o2) % 40 + 4, 200), fill=(50, 40, 60))
    tx = (t * 260) % (W + 400) - 300
    d.rounded_rectangle((tx, 124, tx + 240, 138), 6, fill=(220, 226, 236), outline=(90, 90, 110))
    for k in range(10):
        d.rectangle((tx + 10 + k * 22, 128, tx + 24 + k * 22, 133), fill=(255, 220, 140))
    # big holographic billboard: banned skull
    bx = 300 - int(scroll * .5) % 200
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.rectangle((bx, 26, bx + 150, 106), fill=(16, 10, 20, 230), outline=(255, 210, 60, 255), width=3)
    ld.ellipse((bx + 18, 44, bx + 50, 76), fill=(240, 240, 230, 255))
    ld.rectangle((bx + 25, 54, bx + 31, 61), fill=(0, 0, 0, 255)); ld.rectangle((bx + 37, 54, bx + 43, 61), fill=(0, 0, 0, 255))
    ld.rectangle((bx + 26, 74, bx + 42, 82), fill=(240, 240, 230, 255))
    ld.ellipse((bx + 10, 36, bx + 58, 84), outline=(235, 30, 40, 255), width=5)
    ld.line((bx + 18, 76, bx + 50, 44), fill=(235, 30, 40, 255), width=5)
    ld.text((bx + 66, 42), '骸骨禁止', font=fnt, fill=(255, 220, 60, 255))
    ld.text((bx + 66, 68), 'NO SKULLS', font=fnt, fill=(255, 255, 255, 255))
    for y in range(26, 106, 2):
        ld.line((bx, y, bx + 150, y), fill=(0, 0, 0, 40))
    img.alpha_composite(lay)
    # street level: shopfronts, awnings, lantern strings
    d.rectangle((0, 200, W, 232), fill=(36, 20, 34))
    for i in range(8):
        x0 = (i * 64 - scroll) % (W + 64) - 32
        aw = [(200, 40, 40), (40, 120, 90), (220, 160, 40)][i % 3]
        d.rectangle((x0, 200, x0 + 58, 232), fill=(52, 30, 44), outline=(20, 10, 16))
        d.polygon([(x0 - 2, 200), (x0 + 60, 200), (x0 + 56, 210), (x0 + 2, 210)], fill=aw)
        d.rectangle((x0 + 8, 214, x0 + 50, 230), fill=(255, 210, 140))
    for i in range(14):
        x = (i * 36 - int(scroll * 1.2)) % (W + 40) - 20
        y = 196 + 4 * math.sin(i + t)
        d.ellipse((x, y, x + 10, y + 13), fill=(230, 40, 40)); d.rectangle((x + 4, y - 3, x + 6, y), fill=(255, 210, 60))
    d.line([(x, 192 + 4 * math.sin(x / 40)) for x in range(0, W + 8, 8)], fill=(30, 20, 20))
    # wet street with neon reflections
    d.rectangle((0, 232, W, H), fill=(26, 18, 30))
    for i in range(20):
        x = (i * 31 - scroll) % W
        col = [(255, 60, 90), (90, 240, 255), (255, 210, 60)][i % 3]
        d.line((x, 236 + (i % 4) * 8, x + 12, 236 + (i % 4) * 8), fill=tuple(c // 2 for c in col), width=2)
    # crowd silhouettes with umbrellas (background pedestrians)
    for i in range(10):
        x = (i * 52 + t * (12 if i % 2 else -10)) % (W + 40) - 20
        d.rectangle((x - 3, 214, x + 3, 232), fill=(14, 8, 16)); d.ellipse((x - 3, 208, x + 3, 214), fill=(14, 8, 16))
        if i % 3 == 0:
            d.pieslice((x - 10, 200, x + 10, 214), 180, 360, fill=(40, 30, 50))
    if rain:
        for i in range(140):
            x = (rnd.random() * W - t * 30) % W
            y = (rnd.random() * H + t * 500 + i * 7) % H
            d.line((x, y, x - 2, y + 8), fill=(150, 160, 210))
    L = np.zeros((H, W, 3), np.float32)
    Wd.glow(L, bx + 75, 66, 120, (255, 60, 80), .35)
    for i in range(6):
        Wd.glow(L, (i * 90 + 40 - scroll) % W, 220, 60, (255, 180, 100), .3)
    return Wd.apply_light(img, L, .95), bx

# ======================================================================= v3: drink extras
def jigger(img, x, y, level, liquid, scale=2):
    """Double jigger (measuring cup) with ml marks, filling to `level` 0..1."""
    d = ImageDraw.Draw(img)
    s = scale
    d.polygon([(x - 12 * s, y - 28 * s), (x + 12 * s, y - 28 * s), (x + 5 * s, y), (x - 5 * s, y)], fill=(170, 176, 188), outline=(70, 72, 80))
    if level > 0:
        ly = y - 26 * s * level
        wl = 5 + 7 * level
        d.polygon([(x - wl * s, ly), (x + wl * s, ly), (x + 5 * s, y - 2), (x - 5 * s, y - 2)], fill=liquid)
    for k in (1, 2, 3):
        d.line((x - 8 * s + k, y - k * 8 * s, x - 4 * s, y - k * 8 * s), fill=(240, 244, 250))
    d.polygon([(x - 5 * s, y), (x + 5 * s, y), (x + 10 * s, y + 20 * s), (x - 10 * s, y + 20 * s)], fill=(150, 156, 168), outline=(70, 72, 80))

def layers_inset(img, layers, x=34, y=60, w=60, h=90):
    """'Inside the tin' cutaway: coloured layers bottom→top [(height_frac, rgb, label)]."""
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x - 4, y - 16, x + w + 4, y + h + 4), 4, fill=(20, 14, 18, 230), outline=(255, 220, 140))
    Wd.tiny(img, x + 2, y - 12, 'INSIDE', (255, 220, 140, 255), 1)
    yy = y + h
    for frac, col, lab in layers:
        hh = int(h * frac)
        d.rectangle((x, yy - hh, x + w, yy), fill=col)
        Wd.tiny(img, x + 2, yy - hh + 2, lab, (20, 20, 20, 255), 1)
        yy -= hh
