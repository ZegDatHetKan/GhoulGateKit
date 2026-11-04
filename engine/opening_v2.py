"""The GhoulGate OP — version 2 (used from Ep03 on; Ep01/Ep02 keep their OPs: engine/opening.py stays untouched).

add_opening(ep, title_jp, title_en) has exactly the same length, music (music.m_op, 150 bpm) and beat grid as the v1 OP,
and the same final title card (logo + episode title). Everything in between is redrawn with more detail:

  black beat · title slam · roll call (one beat per ghoul, each in a blurred location from the series + face cut-in panel)
  · graveyard hero lineup under the moon (all 17) · 4 detailed "other episode" scenes (beach, neon rooftop in the rain,
  live house, summer festival) · timeline vortex (all 17 tumbling through the shattered timelines)
  · Cretaceous chase (Taras/Luke/Cheesus) · Mars flag (Giulio/Uh/Pedrox/Slaughtermelon) · Giulio taps the Dark Tap
  · the gang facing the BTC Demon · final title card.

Director's rules: Giulio is one ghoul among many (everyone gets one roll-call beat and appears in both group shots), but the
lore stays: it's Giulio's hand that taps the Dark Tap, and the Cretaceous/Mars groups match Ep02.
"""

from shots import *
from PIL import ImageFilter
import demon as DM
import sets as ST
from opening import add_ending          # the ED / 次回予告 are unchanged

FC.FLOAT = True                          # from Ep03 the ghouls have no legs and levitate (see 02_characters.md)

BEAT = 60 / 150
ROLL = ['giulio', 'quin', 'chops', 'colin', 'uh', 'pedrox', 'slaughter', 'elegy', 'taras', 'jeff', 'luke',
        'noside', 'errorgarden', 'pondering', 'cheesus', 'deepcode', 'bb']


# ======================================================================= small drawing helpers
def layer():
    return Image.new('RGBA', (W, H), (0, 0, 0, 0))

def comp(img, lay):
    img.alpha_composite(lay)
    return img

def tint(img, col, k):
    a = np.asarray(img.convert('RGBA')).astype(np.float32).copy()
    a[..., :3] = a[..., :3] * (1 - k) + np.array(col, np.float32) * k
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

def dim(img, k):
    a = np.asarray(img.convert('RGBA')).astype(np.float32).copy()
    a[..., :3] *= k
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

def blur(img, r):
    return img.filter(ImageFilter.GaussianBlur(r))

def silhouette(im, col):
    a = np.asarray(im)
    return Image.fromarray(np.where(a[..., 3:] > 0, np.array(list(col) + [255], np.uint8), 0).astype(np.uint8))

def outline(im, col=(255, 255, 255, 255)):
    """1px outline around a sprite (pop against busy backgrounds)."""
    a = np.asarray(im).copy()
    m = a[..., 3] > 0
    g = m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
    a[g & ~m] = col
    return Image.fromarray(a)

def ghoul(name, pose='idle', expr='happy', t=0.0, marks=(), scale=1, flip=False, mouth=0, legs=True, rot=0, line=None):
    ch, an = FC.character(name, pose, expr, mouth=mouth, t=t, marks=marks, legs=legs, blink=False)
    if line:
        ch = outline(ch, line)
    if flip:
        ch = ch.transpose(Image.FLIP_LEFT_RIGHT)
        an = dict(an); an['feet'] = (ch.width - an['feet'][0], an['feet'][1])
    big = iscale(ch, scale) if scale != 1 else ch
    if rot:
        big = big.rotate(rot, Image.NEAREST, expand=True)
    return big, an

def put(img, name, x, ground, pose='idle', expr='happy', scale=2, t=0.0, flip=False, marks=(), mouth=0, hop=0, legs=True, line=None):
    big, an = ghoul(name, pose, expr, t, marks, scale, flip, mouth, legs, line=line)
    fx, fy = an['feet']
    paste(img, big, x - fx * scale, ground - (fy + 1) * scale - hop)
    return an

def credit(f, role, name):
    E.title_text(f, 40, 40, role, 20, (255, 255, 255), (30, 0, 40), 3, anchor='lm')
    E.title_text(f, 40, 72, name, 34, (255, 255, 255), (30, 0, 40), 4, anchor='lm')

def stars(d, t, n=90, ymax=150, seed=9):
    rnd = random.Random(seed)
    for i in range(n):
        x, y = rnd.randrange(W), rnd.randrange(ymax)
        v = int(110 + 145 * (math.sin(t * 3 + i * 1.7) + 1) / 2)
        d.point((x, y), fill=(v, v, min(255, v + 20), 255))
        if i % 17 == 0 and v > 220:
            d.point((x - 1, y), fill=(v, v, v, 160)); d.point((x + 1, y), fill=(v, v, v, 160))
            d.point((x, y - 1), fill=(v, v, v, 160)); d.point((x, y + 1), fill=(v, v, v, 160))

def wisp(img, x, y, t):
    """Thin cigarette smoke (smaller than shots.smoke_curl)."""
    lay = layer(); dl = ImageDraw.Draw(lay)
    for i in range(10):
        ph = (t * .35 + i / 10) % 1
        xx = x + math.sin(ph * 8 + t) * 6 * ph
        yy = y - ph * 46
        r = 1 + ph * 3
        dl.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(190, 200, 220, int(120 * (1 - ph))))
    img.alpha_composite(lay)

def whip(img, k):
    """Horizontal smear for whip-pan cuts (k 0..1)."""
    if k <= 0:
        return img
    w = max(8, int(W * (1 - .9 * k)))
    return img.resize((w, H), Image.BILINEAR).resize((W, H), Image.NEAREST)


# ======================================================================= roll call
ROLL_LOOK = {   # pose, expression, marks, location
    'giulio':      ('thumb', 'smug', (), 'door'),
    'quin':        ('crossed', 'deadpan', ('sweat',), 'throne'),
    'chops':       ('point', 'serious', (), 'gold3'),
    'colin':       ('fist', 'evil', (), 'dark'),
    'uh':          ('cheer', 'happy', ('sparkles',), 'mars'),
    'pedrox':      ('thumb', 'happy', (), 'mars2'),
    'slaughter':   ('crossed', 'serious', (), 'mars3'),
    'elegy':       ('smoke', 'deadpan', (), 'mars4'),
    'taras':       ('shrug', 'worried', ('?',), 'jungle'),
    'jeff':        ('idle', 'deadpan', (), 'poker'),
    'luke':        ('cheer', 'sparkle', ('sparkles',), 'volcano'),
    'noside':      ('talk_b', 'happy', (), 'city2'),
    'errorgarden': ('shock', 'shock', ('!',), 'gold'),
    'pondering':   ('facepalm', 'serious', (), 'city3'),
    'cheesus':     ('cheer', 'happy', ('sparkles',), 'jungle2'),
    'deepcode':    ('smoke', 'menace', (), 'city4'),
    'bb':          ('hero', 'happy', ('sparkles',), 'gold2'),
}

def gold_bg(t, seed=0):
    """#7777 timeline: penthouse night with gold rain."""
    img = Wd.vgrad(W, H, [(0, (30, 10, 40)), (.6, (90, 40, 60)), (1, (160, 110, 50))])
    d = ImageDraw.Draw(img)
    rnd = random.Random(3 + seed)
    for i in range(16):                                       # skyline
        x0 = i * 32; hh = rnd.randint(50, 140)
        d.rectangle((x0, 200 - hh, x0 + 28, 270), fill=(24, 10, 34, 255))
        for k in range(14):
            if rnd.random() < .45:
                xx, yy = x0 + 4 + (k % 3) * 8, 200 - hh + 6 + (k // 3) * 10
                d.rectangle((xx, yy, xx + 3, yy + 4), fill=(255, 210, 120, 255))
    d.rectangle((0, 210, W, H), fill=(60, 30, 26, 255))
    for x in range(0, W, 24):
        d.line((x, 210, x - 30, H), fill=(80, 44, 30, 255))
    for i in range(70):                                       # gold coins falling
        x = (rnd.random() * W + math.sin(t * 2 + i) * 6) % W
        y = (rnd.random() * H + t * (90 + i % 5 * 30)) % (H + 10) - 5
        w_ = abs(math.sin(t * 6 + i)) * 3 + 1
        d.ellipse((x - w_, y - 3, x + w_, y + 3), fill=(255, 210, 70, 255), outline=(170, 110, 20, 255))
    d.text((300, 70), '#7777', fill=(255, 220, 120, 255))
    return img

def location(key, t):
    if key == 'door':
        return Wd.apply_light(Wd.door_side(t), Wd.door_lights(t), .8)
    if key in ('throne', 'crypt', 'poker'):
        img = Wd.room_bg(t, key != 'crypt')
        if key == 'poker':
            d = ImageDraw.Draw(img)
            d.ellipse((90, 200, 390, 262), fill=(30, 90, 50, 255), outline=(90, 60, 30, 255), width=4)
            rnd = random.Random(5)
            for i in range(12):
                x, y = 140 + rnd.random() * 200, 214 + rnd.random() * 30
                d.rectangle((x, y, x + 7, y + 10), fill=(250, 250, 245, 255), outline=(40, 40, 40, 255))
                d.point((x + 3, y + 4), fill=(220, 30, 40, 255) if i % 2 else (20, 20, 20, 255))
            for i in range(5):
                for k in range(6):
                    d.ellipse((150 + i * 40, 240 - k * 2, 162 + i * 40, 245 - k * 2), fill=[(220, 40, 40), (40, 80, 220), (240, 240, 240)][i % 3] + (255,), outline=(20, 20, 20, 255))
        return img
    if key == 'dark':
        img = Wd.vgrad(W, H, [(0, (10, 0, 16)), (1, (50, 0, 70))])
        Wd.console(img, 240, 300, t, .6, 0, 2.0, 2)
        for i in range(9):
            DM.flame(img, 20 + i * 56, 270, t, 2, i)
        L = np.zeros((H, W, 3), np.float32)
        Wd.glow(L, 240, 230, 200, (190, 60, 255), 1.0)
        return Wd.apply_light(img, L, .8)
    if key.startswith('mars'):
        return ST.light_shafts(ST.mars_ruins_bg(t), .5)
    if key.startswith('city'):
        return ST.china_bg(t, scroll=t * 40 + len(key) * 120)[0]
    if key in ('jungle', 'jungle2', 'volcano'):
        return ST.prehistoric_bg(t, scroll=t * 30 + (300 if key == 'jungle2' else 0))
    if key.startswith('gold'):
        return gold_bg(t, len(key))
    return E.bg_solid((0, 0, 0))

CROP = {'gold3': (120, 150), 'mars4': (240, 130), 'door': (240, 120), 'throne': (240, 110), 'crypt': (130, 120), 'poker': (240, 200), 'dark': (240, 200),
        'mars': (120, 120), 'mars2': (300, 120), 'mars3': (420, 130), 'city': (380, 120), 'city2': (120, 150),
        'city3': (260, 140), 'city4': (420, 160), 'jungle': (160, 130), 'jungle2': (360, 150), 'volcano': (300, 90),
        'gold': (200, 120), 'gold2': (360, 140)}

_loc_cache = {}
def roll_bg(n, t, lt):
    pose, expr, marks, key = ROLL_LOOK[n]
    col = COL[n]
    q = round(t * 12) / 12                                    # backgrounds animate at 12 fps (cheap + anime-like)
    ck = (key, q)
    if ck not in _loc_cache:
        if len(_loc_cache) > 64:
            _loc_cache.clear()
        bg = location(key, q)
        cx, cy = CROP[key]
        _loc_cache[ck] = (bg, cx, cy)
    bg, cx, cy = _loc_cache[ck]
    img = E.camera(bg, cx + lt * 30, cy, 1.35)
    img = blur(img, 1.6)
    img = tint(dim(img, .8), tuple(int(c * .45) for c in col), .42)
    return img

def face_panel(n, expr, t, lt):
    """Slanted close-up panel (960x540 overlay coords) of the ghoul's face."""
    col = COL[n]
    ch, an = FC.character(n, 'idle', expr, t=t, blink=False, legs=False)
    cx, cy = an['center']
    s = 7
    crop = ch.crop((cx - 22, cy - 18, cx + 22, cy + 14))
    big = crop.resize((crop.width * s, crop.height * s), Image.NEAREST)
    pw, ph = 330, 190
    panel = Image.new('RGBA', (pw, ph), tuple(int(c * .25) for c in col) + (255,))
    pd = ImageDraw.Draw(panel)
    for i in range(0, pw + ph, 14):                            # halftone stripes
        pd.line((i, 0, i - ph, ph), fill=tuple(int(c * .4) for c in col) + (255,), width=5)
    panel.alpha_composite(big, (int((pw - big.width) / 2 + (1 - ease_out(lt / .2)) * 60), int((ph - big.height) / 2 + 6)))
    mask = Image.new('L', (pw, ph), 0)
    ImageDraw.Draw(mask).polygon([(40, 0), (pw, 0), (pw - 40, ph), (0, ph)], fill=255)
    out = Image.new('RGBA', (pw, ph), (0, 0, 0, 0))
    out.paste(panel, (0, 0), mask)
    frame = ImageDraw.Draw(out)
    frame.line([(40, 0), (pw - 1, 0), (pw - 41, ph - 1), (0, ph - 1), (40, 0)], fill=(255, 255, 255, 255), width=4)
    return out


# ======================================================================= graveyard hero lineup
def graveyard(t, cam_k):
    img = Wd.vgrad(W, H, [(0, (8, 4, 26)), (.45, (40, 12, 70)), (.75, (120, 40, 110)), (1, (60, 20, 50))])
    d = ImageDraw.Draw(img)
    stars(d, t, 120, 140)
    mx, my, r = 240, 92, 64                                    # the moon
    L = np.zeros((H, W, 3), np.float32)
    Wd.glow(L, mx, my, 170, (255, 200, 255), .55)
    img = Wd.apply_light(img, L, 1.0)
    d = ImageDraw.Draw(img)
    d.ellipse((mx - r, my - r, mx + r, my + r), fill=(255, 236, 246, 255))
    d.ellipse((mx - r + 10, my - r + 4, mx + r, my + r), fill=(250, 222, 238, 255))
    for ox, oy, rr in ((-22, -18, 12), (18, 10, 9), (-8, 26, 7), (26, -24, 6), (-34, 14, 5), (6, -36, 5)):
        d.ellipse((mx + ox - rr, my + oy - rr, mx + ox + rr, my + oy + rr), fill=(232, 200, 222, 255))
        d.arc((mx + ox - rr, my + oy - rr, mx + ox + rr, my + oy + rr), 200, 340, fill=(210, 176, 204, 255))
    lay = layer(); dl = ImageDraw.Draw(lay)
    for i in range(5):                                         # thin clouds drifting past the moon
        cy_ = 120 + i * 9
        cx_ = (i * 131 + t * (10 + i * 3)) % (W + 200) - 100
        dl.rounded_rectangle((cx_, cy_, cx_ + 80 + i * 10, cy_ + 3), 1, fill=(160, 90, 170, 120))
    img.alpha_composite(lay); d = ImageDraw.Draw(img)
    # far hill + the crypt with lit windows
    pts = [(x, 168 + int(10 * math.sin(x / 60 + 1) + 4 * math.sin(x / 17))) for x in range(0, W + 4, 4)]
    d.polygon(pts + [(W, H), (0, H)], fill=(26, 10, 40, 255))
    d.rectangle((360, 118, 430, 172), fill=(20, 6, 32, 255)); d.polygon([(352, 120), (395, 92), (438, 120)], fill=(20, 6, 32, 255))
    d.rectangle((391, 78, 399, 96), fill=(20, 6, 32, 255)); d.rectangle((384, 84, 406, 88), fill=(20, 6, 32, 255))
    for wx in (368, 384, 406, 420):
        on = (int(t * 2) + wx) % 7 != 0
        d.rectangle((wx, 132, wx + 5, 142), fill=(255, 180, 90, 255) if on else (60, 30, 50, 255))
    d.rectangle((388, 150, 402, 172), fill=(180, 80, 255, 255))
    # dead tree
    def branch(x, y, a, ln, w):
        if ln < 4:
            return
        x2, y2 = x + math.cos(a) * ln, y + math.sin(a) * ln
        d.line((x, y, x2, y2), fill=(14, 4, 20, 255), width=max(1, w))
        branch(x2, y2, a - .45, ln * .7, w - 1)
        branch(x2, y2, a + .35, ln * .66, w - 1)
    branch(60, 180, -math.pi / 2 - .1, 36, 5)
    # bats
    for i in range(6):
        bx = (i * 83 + t * 70) % (W + 40) - 20
        by = 40 + i * 9 + math.sin(t * 4 + i) * 6
        fl = 3 if int(t * 10 + i) % 2 else -2
        d.polygon([(bx, by), (bx - 6, by - fl), (bx - 3, by + 1)], fill=(10, 2, 16, 255))
        d.polygon([(bx, by), (bx + 6, by - fl), (bx + 3, by + 1)], fill=(10, 2, 16, 255))
    # ridge for the back row
    pts = [(x, 190 + int(4 * math.sin(x / 40))) for x in range(0, W + 4, 4)]
    d.polygon(pts + [(W, H), (0, H)], fill=(36, 16, 44, 255))
    for x in range(0, W, 7):
        y = 190 + int(4 * math.sin(x / 40))
        d.line((x, y, x + 2, y - 3 - (x * 7) % 4), fill=(50, 26, 60, 255))
    return img

def tombstones(img, t):
    d = ImageDraw.Draw(img)
    for i, (x, w_, h_, tilt) in enumerate(((22, 28, 40, -4), (96, 22, 30, 3), (392, 26, 38, 5), (456, 30, 44, -3))):
        y = 270
        pts = [(x - w_ / 2, y), (x - w_ / 2 + tilt, y - h_), (x + w_ / 2 + tilt, y - h_), (x + w_ / 2, y)]
        d.polygon(pts, fill=(60, 54, 80, 255))
        d.pieslice((x - w_ / 2 + tilt, y - h_ - w_ / 2, x + w_ / 2 + tilt, y - h_ + w_ / 2), 180, 360, fill=(60, 54, 80, 255))
        d.line((x - w_ / 2 + tilt + 2, y - h_, x - w_ / 2 + 2, y), fill=(90, 84, 110, 255))
        d.text((x - 5 + tilt * .5, y - h_ + 2), 'RIP', fill=(30, 26, 44, 255))
    # drifting fog
    lay = layer(); dl = ImageDraw.Draw(lay)
    for i in range(10):
        fx = (i * 70 + t * (12 + i % 3 * 6)) % (W + 140) - 70
        fy = 236 + (i % 3) * 10
        dl.ellipse((fx - 50, fy - 9, fx + 50, fy + 9), fill=(200, 160, 230, 46))
    img.alpha_composite(lay)


# ======================================================================= montage A: four "other episodes"
def scene_beach(f, lt):
    """Beach episode — ErrorGarden surfs, BB plays beach ball. Sunset."""
    img = Wd.vgrad(W, H, [(0, (90, 40, 120)), (.22, (230, 90, 140)), (.4, (255, 170, 120)), (.46, (255, 220, 150))])
    d = ImageDraw.Draw(img)
    hz = 124
    sx, sy = 330, hz
    L = np.zeros((H, W, 3), np.float32)
    Wd.glow(L, sx, sy, 200, (255, 190, 120), .7)
    img = Wd.apply_light(img, L, 1.0); d = ImageDraw.Draw(img)
    d.pieslice((sx - 34, sy - 34, sx + 34, sy + 34), 180, 360, fill=(255, 246, 200, 255))
    for k in range(4):                                          # sun stripes
        y = sy - 6 - k * 7
        d.line((sx - 40, y, sx + 40, y), fill=(255, 180, 140, 255), width=1 + k // 2)
    for i in range(6):                                          # long clouds
        cx_ = (i * 110 - lt * 20) % (W + 120) - 60
        cy_ = 30 + i * 13
        d.rounded_rectangle((cx_, cy_, cx_ + 90 - i * 6, cy_ + 5), 2, fill=(255, 150, 170, 255))
        d.line((cx_ + 4, cy_ + 5, cx_ + 80 - i * 6, cy_ + 5), fill=(200, 90, 140, 255))
    # sea
    sea = Wd.vgrad(W, 70, [(0, (70, 120, 200)), (1, (40, 170, 190))])
    img.alpha_composite(sea, (0, hz))
    d = ImageDraw.Draw(img)
    for y in range(hz + 2, hz + 70, 3):                         # sun glitter column + wave lines
        ph = (y * 13 + int(f.T * 10)) % 9
        wd = int(6 + (y - hz) * .7)
        d.line((sx - wd + ph * 2, y, sx + wd - ph, y), fill=(255, 230, 180, 255))
        off = (y * 37 + f.T * 30) % 60
        for x in range(-60, W, 60):
            d.line((x + off, y, x + off + 14, y), fill=(130, 200, 235, 255))
    # boat on the horizon
    d.polygon([(90, hz - 1), (110, hz - 1), (106, hz + 3), (94, hz + 3)], fill=(60, 30, 60, 255)); d.line((100, hz - 14, 100, hz - 1), fill=(60, 30, 60, 255))
    d.polygon([(101, hz - 13), (108, hz - 3), (101, hz - 3)], fill=(255, 240, 230, 255))
    # ErrorGarden surfing the wave
    wx = 300 + lt * 40
    wave = [(x, 160 - max(0, 26 - abs(x - wx) * .35) - 2 * math.sin(x / 7 + f.T * 6)) for x in range(int(wx - 110), int(wx + 110), 3)]
    d.polygon(wave + [(wx + 110, 194), (wx - 110, 194)], fill=(50, 150, 200, 255))
    d.line(wave, fill=(240, 250, 255, 255), width=2)
    for i in range(18):                                          # spray
        a = random.Random(i).random() * math.pi
        rr = (f.T * 40 + i * 9) % 26
        d.point((wx + 30 + math.cos(a) * rr, 134 - math.sin(a) * rr), fill=(255, 255, 255, 255))
    by = 136 + math.sin(f.T * 5) * 2
    d.polygon([(wx - 30, by + 2), (wx + 26, by - 4), (wx + 30, by), (wx - 26, by + 6)], fill=(255, 220, 60, 255), outline=(120, 70, 20, 255))
    d.line((wx - 24, by + 3, wx + 24, by - 2), fill=(230, 60, 60, 255))
    put(img, 'errorgarden', wx, by + 1, 'hero', 'happy', 1, f.T, marks=('sparkles',))
    # shore foam + sand
    shore = [(x, 194 + 3 * math.sin(x / 23 + f.T * 2)) for x in range(0, W + 4, 4)]
    d.polygon(shore + [(W, H), (0, H)], fill=(240, 206, 150, 255))
    d.line(shore, fill=(255, 255, 255, 255), width=3)
    rnd = random.Random(7)
    for i in range(160):
        x, y = rnd.randrange(W), rnd.randrange(200, H)
        d.point((x, y), fill=(210, 170, 120, 255) if i % 2 else (255, 230, 180, 255))
    for i in range(5):                                           # shells
        x, y = 40 + i * 97, 236 + (i * 13) % 26
        d.pieslice((x, y, x + 8, y + 8), 180, 360, fill=(255, 190, 200, 255), outline=(170, 100, 110, 255))
    # sandcastle with a skull flag
    cx_ = 70
    d.rectangle((cx_ - 22, 236, cx_ + 22, 254), fill=(220, 180, 120, 255), outline=(170, 130, 80, 255))
    d.rectangle((cx_ - 10, 218, cx_ + 10, 236), fill=(220, 180, 120, 255), outline=(170, 130, 80, 255))
    for k in range(-22, 23, 8):
        d.rectangle((cx_ + k, 232, cx_ + k + 4, 236), fill=(220, 180, 120, 255))
    d.line((cx_, 200, cx_, 218), fill=(90, 60, 40, 255))
    d.polygon([(cx_ + 1, 200), (cx_ + 14, 204 + math.sin(f.T * 8) * 2), (cx_ + 1, 209)], fill=(30, 20, 30, 255))
    d.point((cx_ + 5, 203), fill=(255, 255, 255, 255)); d.point((cx_ + 8, 203), fill=(255, 255, 255, 255))
    # parasol + towel
    d.line((420, 160, 412, 250), fill=(240, 240, 240, 255), width=2)
    for k in range(6):
        a0, a1 = math.pi + k * math.pi / 6, math.pi + (k + 1) * math.pi / 6
        d.polygon([(420, 160), (420 + math.cos(a0) * 54, 172 + math.sin(a0) * 18), (420 + math.cos(a1) * 54, 172 + math.sin(a1) * 18)],
                  fill=((255, 80, 120) if k % 2 else (255, 250, 240)) + (255,))
    d.polygon([(330, 252), (430, 248), (440, 266), (336, 270)], fill=(80, 200, 220, 255))
    for k in range(4):
        d.line((334 + k * 4, 254 + k * 4, 434 + k * 2, 250 + k * 4), fill=(255, 255, 255, 255))
    # BB jumping for the beach ball
    hop = abs(math.sin(lt * 4)) * 16
    put(img, 'bb', 220, 262, 'cheer', 'happy', 1.3, f.T, hop=hop)
    bx, by2 = 230 + math.sin(lt * 3) * 10, 170 - abs(math.sin(lt * 4 + 1)) * 30
    d.ellipse((bx - 9, by2 - 9, bx + 9, by2 + 9), fill=(255, 255, 255, 255), outline=(40, 40, 60, 255))
    d.pieslice((bx - 9, by2 - 9, bx + 9, by2 + 9), 0, 60, fill=(255, 70, 90, 255))
    d.pieslice((bx - 9, by2 - 9, bx + 9, by2 + 9), 120, 180, fill=(70, 140, 255, 255))
    d.pieslice((bx - 9, by2 - 9, bx + 9, by2 + 9), 240, 300, fill=(255, 210, 60, 255))
    # gulls + foreground palm
    for i in range(3):
        gx, gy = (i * 60 + lt * 50 + 120) % W, 50 + i * 12
        d.line((gx - 4, gy, gx, gy + 2), fill=(60, 30, 60, 255)); d.line((gx, gy + 2, gx + 4, gy), fill=(60, 30, 60, 255))
    d.line((W - 6, H, W - 40, 30), fill=(70, 40, 40, 255), width=7)
    for k in range(6):
        a = -math.pi / 2 + (k - 2.5) * .55 + math.sin(f.T * 2 + k) * .05
        tipx, tipy = W - 40 + math.cos(a) * 70, 30 + math.sin(a) * 26 + 30
        d.polygon([(W - 40, 30), (tipx, tipy), (W - 40 + math.cos(a) * 30, 30 + math.sin(a) * 10 + 14)], fill=(20, 80, 50, 255))
    return E.camera(img, 230 + lt * 20, 140, 1.06)

def scene_rooftop(f, lt):
    """Neon rooftop in the rain — Elegy under a clear umbrella, DeepCode's cigar glow, Colin at the edge."""
    img = Wd.vgrad(W, H, [(0, (6, 4, 20)), (.55, (36, 16, 60)), (1, (20, 10, 30))])
    d = ImageDraw.Draw(img)
    rnd = random.Random(31)
    L = np.zeros((H, W, 3), np.float32)
    for layer_i, (base, col, step) in enumerate(((150, (20, 14, 44), 26), (180, (12, 8, 26), 34))):
        x = -10
        while x < W:
            w_ = rnd.randint(step - 8, step + 10); h_ = rnd.randint(40, 120 - layer_i * 20)
            d.rectangle((x, base - h_, x + w_, 200), fill=col + (255,))
            for k in range(int(w_ / 6) * int(h_ / 9)):
                if rnd.random() < .3:
                    wx = x + 2 + (k % max(1, int(w_ / 6))) * 6; wy = base - h_ + 4 + (k // max(1, int(w_ / 6))) * 9
                    d.rectangle((wx, wy, wx + 2, wy + 3), fill=rnd.choice([(255, 220, 140), (140, 220, 255), (255, 120, 200)]) + (255,))
            if rnd.random() < .3:
                d.point((x + w_ // 2, base - h_ - 1), fill=(255, 40, 40, 255) if int(f.T * 2 + x) % 2 else (80, 0, 0, 255))
            x += w_ + 4
    # neon signs
    for (nx, ny, txt, c) in ((60, 70, 'ゴール', (255, 80, 200)), (330, 54, '骨', (80, 230, 255)), (400, 96, 'BAR', (255, 220, 80))):
        on = not (txt == 'BAR' and int(f.T * 7) % 5 == 0)
        fnt = E.font('DotGothic16.ttf', 16 if len(txt) > 1 else 28)
        if on:
            d.text((nx, ny), txt, font=fnt, fill=c + (255,))
            Wd.glow(L, nx + 16, ny + 10, 50, c, .55)
    # searchlights
    lay = layer(); dl = ImageDraw.Draw(lay)
    for i, x in enumerate((140, 380)):
        a = -math.pi / 2 + math.sin(f.T * .7 + i * 2) * .5
        dl.polygon([(x, 200), (x + math.cos(a - .06) * 300, 200 + math.sin(a - .06) * 300), (x + math.cos(a + .06) * 300, 200 + math.sin(a + .06) * 300)], fill=(180, 200, 255, 26))
    img.alpha_composite(lay); d = ImageDraw.Draw(img)
    # rooftop: wet floor with reflections
    d.rectangle((0, 196, W, H), fill=(22, 18, 34, 255))
    refl = img.crop((0, 120, W, 196)).transpose(Image.FLIP_TOP_BOTTOM).resize((W, 74), Image.NEAREST)
    refl = dim(blur(refl, 1), .45)
    img.alpha_composite(refl, (0, 196))
    d = ImageDraw.Draw(img)
    for y in range(198, H, 6):
        d.line((0, y, W, y), fill=(30, 26, 46, 255))
    d.rectangle((0, 192, W, 197), fill=(60, 56, 80, 255))
    for x in range(0, W, 16):                                       # railing
        d.line((x, 170, x, 192), fill=(70, 66, 90, 255))
    d.line((0, 170, W, 170), fill=(90, 86, 110, 255), width=2)
    # water tank on stilts + AC units
    d.rectangle((24, 96, 84, 150), fill=(46, 40, 60, 255), outline=(20, 16, 30, 255))
    for k in range(3):
        d.line((24, 108 + k * 14, 84, 108 + k * 14), fill=(30, 26, 44, 255))
    d.polygon([(20, 96), (54, 82), (88, 96)], fill=(40, 34, 54, 255))
    for x in (30, 78):
        d.line((x, 150, x, 196), fill=(30, 26, 44, 255), width=3)
    for x in (420, 446):
        d.rectangle((x, 176, x + 22, 196), fill=(80, 80, 96, 255), outline=(30, 30, 40, 255))
        d.ellipse((x + 4, 180, x + 16, 192), outline=(40, 40, 50, 255))
        a = f.T * 12
        d.line((x + 10, 186, x + 10 + math.cos(a) * 5, 186 + math.sin(a) * 5), fill=(40, 40, 50, 255))
    # characters
    put(img, 'colin', 384, 232, 'idle', 'serious', 1.25, f.T)
    Wd.glow(L, 384, 163, 34, (80, 230, 255), .6)
    put(img, 'deepcode', 118, 246, 'smoke', 'menace', 1.3, f.T)
    cg = .6 + .4 * math.sin(f.T * 5)
    Wd.glow(L, 128, 180, 14, (255, 80, 40), cg)
    wisp(img, 128, 178, f.T)
    put(img, 'elegy', 250, 262, 'smoke', 'deadpan', 1.6, f.T)
    wisp(img, 266, 172, f.T + 2)
    # clear umbrella over Elegy
    lay = layer(); dl = ImageDraw.Draw(lay)
    ux, uy = 244, 134
    dl.pieslice((ux - 46, uy - 26, ux + 46, uy + 26), 180, 360, fill=(220, 230, 255, 60), outline=(240, 245, 255, 200))
    for k in range(1, 6):
        a = math.pi + k * math.pi / 6
        dl.line((ux, uy - 26, ux + math.cos(a) * 46, uy + math.sin(a) * 26), fill=(240, 245, 255, 120))
    dl.line((ux, uy - 26, ux, uy + 50), fill=(220, 220, 230, 255), width=2)
    img.alpha_composite(lay); d = ImageDraw.Draw(img)
    img = Wd.apply_light(img, L, .9)
    # rain + splashes
    lay = layer(); dl = ImageDraw.Draw(lay)
    for i in range(240):
        x = (rnd.random() * (W + 80) + f.T * 60) % (W + 80) - 40
        y = (rnd.random() * H + f.T * 520 + i * 3) % H
        ln = 6 + i % 3 * 4
        dl.line((x, y, x - 3, y + ln), fill=(170, 190, 240, 110 + i % 3 * 40))
    for i in range(30):
        x = rnd.randrange(W); ph = (f.T * 3 + i * .37) % 1
        y = 200 + rnd.randrange(68)
        dl.arc((x - ph * 5, y - ph * 2, x + ph * 5, y + ph * 2), 180, 360, fill=(200, 210, 255, int(200 * (1 - ph))))
    img.alpha_composite(lay)
    # lightning
    if .45 < lt < .55:
        f.flash = .55; f.flash_c = (220, 220, 255)
        d = ImageDraw.Draw(img)
        x, y = 300, 0
        pts = [(x, y)]
        r2 = random.Random(int(f.T))
        while y < 110:
            x += r2.randint(-12, 12); y += r2.randint(10, 18); pts.append((x, y))
        d.line(pts, fill=(255, 255, 255, 255), width=2)
    return E.camera(img, 240, 150 - lt * 12, 1.04 + lt * .12)

def scene_live(f, lt):
    """Live house — Chops on vocals, NoSide on guitar, Jeff on drums (with the burger), a monster crowd."""
    img = Wd.vgrad(W, H, [(0, (10, 4, 24)), (1, (34, 10, 44))])
    d = ImageDraw.Draw(img)
    # LED wall: equalizer + GHOUL
    d.rectangle((60, 30, 420, 168), fill=(14, 8, 24, 255))
    for i in range(30):
        x = 66 + i * 12
        hgt = int((math.sin(f.T * 9 + i * .7) * .5 + .5) * 70 + (math.sin(f.T * 23 + i) + 1) * 12)
        for k in range(hgt // 6):
            y = 160 - k * 6
            c = (255, 70, 200) if k > 10 else ((255, 200, 80) if k > 6 else (80, 220, 255))
            d.rectangle((x, y - 4, x + 9, y), fill=c + (255,))
    fnt = E.sfx_font(34)
    d.text((240, 62), 'GHOULGATE', font=E.sfx_font(24), fill=(255, 255, 255, 255), anchor='mm', stroke_width=2, stroke_fill=(120, 0, 120, 255))
    for x in range(60, 421, 4):                                     # LED grid lines
        d.line((x, 30, x, 168), fill=(0, 0, 0, 255))
    # truss + spotlights
    d.rectangle((0, 8, W, 16), fill=(70, 70, 80, 255))
    for x in range(0, W, 10):
        d.line((x, 8, x + 10, 16), fill=(40, 40, 50, 255))
    lay = layer(); dl = ImageDraw.Draw(lay)
    cols = [(255, 60, 200), (60, 200, 255), (255, 230, 90), (160, 90, 255)]
    for i in range(6):
        x = 40 + i * 80
        a = math.pi / 2 + math.sin(f.T * 2.3 + i * 1.3) * .5
        c = cols[i % 4]
        dl.polygon([(x, 18), (x + math.cos(a - .14) * 300, 18 + math.sin(a - .14) * 300), (x + math.cos(a + .14) * 300, 18 + math.sin(a + .14) * 300)], fill=c + (46,))
        d.rectangle((x - 5, 14, x + 5, 24), fill=(30, 30, 36, 255)); d.ellipse((x - 3, 20, x + 3, 26), fill=c + (255,))
    # stage
    d.rectangle((0, 196, W, 214), fill=(40, 30, 50, 255))
    d.rectangle((0, 196, W, 198), fill=(120, 100, 140, 255))
    for x in range(10, W, 30):
        d.rectangle((x, 204, x + 4, 206), fill=cols[(x // 30 + int(f.T * 4)) % 4] + (255,))
    for sx in (8, 430):                                             # speaker stacks
        for k in range(3):
            y = 120 + k * 26
            d.rectangle((sx, y, sx + 42, y + 24), fill=(24, 22, 28, 255), outline=(60, 60, 70, 255))
            r = 7 + (1 if int(f.T * 10) % 2 else 0)
            d.ellipse((sx + 21 - r, y + 12 - r, sx + 21 + r, y + 12 + r), fill=(50, 50, 60, 255), outline=(90, 90, 100, 255))
    # Jeff on drums (back), NoSide guitar (left), Chops vocals (front centre)
    put(img, 'jeff', 330, 196, 'idle', 'deadpan', 1, f.T)
    hit = int(f.T / BEAT * 2) % 2
    d.ellipse((300, 168, 360, 200), fill=(220, 40, 60, 255), outline=(250, 250, 250, 255), width=2)
    Wd.tiny(img, 316, 180, 'GG', (255, 255, 255, 255), 2)
    for cx_, cy_ in ((292, 160), (370, 156)):
        d.ellipse((cx_ - 14, cy_ - 2 - hit, cx_ + 14, cy_ + 2 - hit), fill=(230, 190, 60, 255), outline=(150, 110, 20, 255))
        d.line((cx_, cy_, cx_, 196), fill=(150, 150, 160, 255))
    d.line((320, 150 + hit * 4, 300, 160), fill=(240, 220, 170, 255), width=2); d.line((345, 150 + (1 - hit) * 4, 368, 156), fill=(240, 220, 170, 255), width=2)
    put(img, 'noside', 130, 204, 'talk_b', 'happy', 1, f.T, marks=('note',))
    d.polygon([(112, 160), (138, 148), (142, 156), (118, 168)], fill=(255, 90, 160, 255), outline=(80, 20, 40, 255))
    d.ellipse((104, 156, 124, 176), fill=(255, 90, 160, 255), outline=(80, 20, 40, 255))
    d.line((138, 150, 166, 136), fill=(120, 80, 50, 255), width=3)
    put(img, 'chops', 240, 214, 'fist', 'happy', 1.4, f.T, marks=('note',), mouth=2 + int(f.T * 8) % 2)
    d.line((262, 140, 262, 214), fill=(180, 180, 190, 255), width=2); d.ellipse((256, 132, 268, 144), fill=(60, 60, 70, 255), outline=(150, 150, 160, 255))
    # crowd: monster silhouettes with glowsticks, bouncing on the beat
    for i in range(12):
        n = [1, 3, 5, 6, 8, 9, 11, 12, 13, 16, 18, 19][i]
        m = E.mon_sprite(n, 1.0)
        sil = silhouette(m, (12, 4, 18))
        bounce = abs(math.sin(f.T * math.pi / BEAT + i)) * 8
        x = 10 + i * 42 + (i % 2) * 6
        paste(img, sil, x - sil.width / 2, H - sil.height * .62 - bounce)
        c = cols[i % 4]
        gx, gy = x + 10, H - sil.height * .62 - bounce - 6
        d.line((gx, gy, gx + 4 * math.sin(f.T * 8 + i), gy - 16), fill=c + (255,), width=3)
    # confetti
    rnd = random.Random(12)
    for i in range(70):
        x = (rnd.random() * W + math.sin(f.T * 2 + i) * 10) % W
        y = (rnd.random() * H + f.T * (40 + i % 4 * 15)) % H
        d.rectangle((x, y, x + 2, y + 1 + (int(f.T * 8 + i) % 2)), fill=cols[i % 4] + (255,))
    img.alpha_composite(lay)
    L = np.zeros((H, W, 3), np.float32)
    Wd.glow(L, 240, 110, 200, (255, 120, 220), .5)
    img = Wd.apply_light(img, L, .9)
    return E.camera(img, 240, 160 - lt * 20, 1.12 - lt * .08)

def firework(d, L, cx, cy, ph, col, n=36, r=78):
    if ph <= 0 or ph >= 1:
        return
    if ph < .25:                                                    # rocket trail
        k = ph / .25
        y = 270 - (270 - cy) * k
        d.line((cx, y, cx, y + 16), fill=(255, 230, 180, 255))
        return
    k = (ph - .25) / .75
    if k < .06:
        return
    rr = r * ease_out(k)
    a_ = int(255 * (1 - k ** 2))
    for i in range(n):
        a = i * math.tau / n
        x0, y0 = cx + math.cos(a) * rr * .55, cy + math.sin(a) * rr * .55 + k * k * 10
        x1, y1 = cx + math.cos(a) * rr, cy + math.sin(a) * rr + k * k * 18
        d.line((x0, y0, x1, y1), fill=col + (int(a_ * .6),), width=1)
        d.rectangle((x1 - 1, y1 - 1, x1 + 1, y1 + 1), fill=(255, 255, 240, a_))
        if i % 2:
            xm, ym = cx + math.cos(a + .1) * rr * .75, cy + math.sin(a + .1) * rr * .75 + k * k * 14
            d.point((xm, ym), fill=(255, 255, 255, a_))
    Wd.glow(L, cx, cy, r * 1.6, col, .5 * (1 - k))

def scene_festival(f, lt):
    """Summer festival — Pondering watching the fireworks, Quin (deadpan) with a goldfish bag."""
    img = Wd.vgrad(W, H, [(0, (6, 6, 30)), (.6, (30, 16, 60)), (1, (50, 20, 40))])
    d = ImageDraw.Draw(img)
    stars(d, f.T, 50, 90, seed=4)
    L = np.zeros((H, W, 3), np.float32)
    lay = layer(); dl = ImageDraw.Draw(lay)
    for i, (cx, cy, col, off) in enumerate(((110, 60, (255, 120, 80), 0), (300, 44, (120, 220, 255), .35), (410, 78, (255, 230, 110), .62), (200, 30, (255, 120, 220), .8))):
        firework(dl, L, cx, cy, (f.T * .9 + off) % 1.25, col)
    img.alpha_composite(lay); d = ImageDraw.Draw(img)
    # shrine hill + torii
    pts = [(x, 140 + int(14 * math.sin(x / 80) + 6 * math.sin(x / 23))) for x in range(0, W + 4, 4)]
    d.polygon(pts + [(W, H), (0, H)], fill=(16, 10, 30, 255))
    tx = 380
    d.rectangle((tx - 22, 110, tx - 18, 146), fill=(150, 30, 40, 255)); d.rectangle((tx + 18, 110, tx + 22, 146), fill=(150, 30, 40, 255))
    d.rectangle((tx - 30, 106, tx + 30, 110), fill=(170, 36, 44, 255)); d.rectangle((tx - 24, 116, tx + 24, 118), fill=(150, 30, 40, 255))
    # stalls
    stalls = (('たこ焼き', (240, 70, 60)), ('金魚', (60, 120, 230)), ('りんご飴', (230, 60, 120)), ('かき氷', (60, 180, 170)))
    fnt = E.font('DotGothic16.ttf', 12)
    for i, (txt, c) in enumerate(stalls):
        x0 = 10 + i * 122
        d.rectangle((x0, 150, x0 + 110, 214), fill=(60, 34, 30, 255))
        d.rectangle((x0 + 6, 168, x0 + 104, 204), fill=(255, 200, 120, 255))
        for k in range(8):                                          # striped awning
            d.polygon([(x0 + k * 14, 150), (x0 + k * 14 + 14, 150), (x0 + k * 14 + 14, 162), (x0 + k * 14, 166)], fill=(c if k % 2 else (250, 240, 230)) + (255,))
        d.rectangle((x0 + 20, 166, x0 + 90, 180), fill=c + (255,))
        d.text((x0 + 55, 173), txt, font=fnt, fill=(255, 255, 255, 255), anchor='mm')
        for k in range(5):
            d.ellipse((x0 + 14 + k * 18, 190, x0 + 22 + k * 18, 198), fill=(200, 120, 60, 255))
        Wd.glow(L, x0 + 55, 186, 60, (255, 190, 110), .5)
    # ground path
    d.rectangle((0, 214, W, H), fill=(54, 40, 46, 255))
    for x in range(0, W, 18):
        d.rectangle((x, 216 + (x // 18) % 2 * 2, x + 15, 222), fill=(70, 54, 60, 255))
    # lantern string swaying across the top
    sway = math.sin(f.T * 1.6) * 3
    pts = [(x, 18 + 12 * math.sin(x / 70) + sway) for x in range(0, W + 1, 30)]
    d.line(pts, fill=(40, 20, 20, 255))
    for x, y in pts:
        d.rounded_rectangle((x - 6, y, x + 6, y + 15), 4, fill=(240, 70, 50, 255), outline=(120, 20, 10, 255))
        d.line((x - 4, y + 5, x + 4, y + 5), fill=(255, 150, 90, 255)); d.line((x - 4, y + 10, x + 4, y + 10), fill=(255, 150, 90, 255))
        Wd.glow(L, x, y + 8, 22, (255, 120, 60), .55)
    # cast
    put(img, 'pondering', 170, 262, 'idle', 'sparkle', 1.4, f.T, marks=('sparkles',))
    put(img, 'quin', 330, 264, 'idle', 'deadpan', 1.4, f.T, marks=('sweat',))
    gx, gy = 366, 204 + math.sin(f.T * 3) * 2                          # goldfish bag
    lay = layer(); dl = ImageDraw.Draw(lay)
    dl.ellipse((gx - 12, gy, gx + 12, gy + 24), fill=(170, 220, 255, 110), outline=(230, 245, 255, 220))
    img.alpha_composite(lay); d = ImageDraw.Draw(img)
    d.line((gx, gy - 10, gx, gy), fill=(230, 230, 230, 255))
    fxp = gx + math.sin(f.T * 4) * 5
    d.polygon([(fxp - 4, gy + 14), (fxp + 2, gy + 11), (fxp + 2, gy + 17)], fill=(255, 120, 30, 255)); d.polygon([(fxp + 2, gy + 14), (fxp + 6, gy + 11), (fxp + 6, gy + 17)], fill=(255, 160, 60, 255))
    img = Wd.apply_light(img, L, .85)
    return E.camera(img, 240 + lt * 16, 150, 1.05)


# ======================================================================= timeline vortex
_thumbs = {}
def timeline_thumbs():
    if not _thumbs:
        srcs = [ST.prehistoric_bg(1.0), ST.china_bg(1.0)[0], ST.mars_ruins_bg(1.0), Wd.room_bg(1.0, True), gold_bg(1.0)]
        for i, s in enumerate(srcs):
            th = s.resize((96, 54), Image.BOX).convert('RGBA')
            dd = ImageDraw.Draw(th)
            dd.rectangle((0, 0, 95, 53), outline=(255, 255, 255, 255), width=2)
            _thumbs[i] = th
    return _thumbs

def vortex(f):
    img = E.bg_solid((6, 0, 14))
    d = ImageDraw.Draw(img)
    cx, cy = 240 + math.sin(f.t * 2) * 10, 130 + math.cos(f.t * 1.7) * 6
    # concentric rings rushing outward (tunnel)
    for i in range(16):
        ph = ((f.t * .9 + i / 16) % 1)
        r = 6 + (ph ** 2.2) * 420
        col = (110, 40, 200) if i % 2 else (40, 150, 220)
        a = int(255 * min(1, ph * 3))
        w_ = max(1, int(ph * 6))
        d.ellipse((cx - r, cy - r * .62, cx + r, cy + r * .62), outline=tuple(int(c * a / 255) for c in col) + (255,), width=w_)
        if i % 4 == 0:                                                 # clock numerals on the rings
            for k in range(12):
                ang = k * math.tau / 12 + f.t * (1 if i % 8 else -1)
                tx, ty = cx + math.cos(ang) * r, cy + math.sin(ang) * r * .62
                s = max(1, int(ph * 3))
                d.rectangle((tx - s, ty - s, tx + s, ty + s), fill=(255, 230, 160, 255))
    # clock hands spinning in the centre
    for ln, sp in ((22, 9), (14, -3)):
        a = f.t * sp
        d.line((cx, cy, cx + math.cos(a) * ln, cy + math.sin(a) * ln * .62), fill=(255, 230, 160, 255), width=2)
    # timeline shards (thumbnails from the series) flying out
    th = timeline_thumbs()
    for i in range(8):
        ph = ((f.t * .7 + i * .125) % 1)
        ang = i * 2.4 + 1
        rr = ph ** 1.8 * 320
        s = .15 + ph * 1.0
        t_ = th[i % len(th)]
        im = t_.resize((max(2, int(t_.width * s)), max(2, int(t_.height * s))), Image.NEAREST).rotate((i * 37 + f.t * 40) % 360 - 180, Image.NEAREST, expand=True)
        paste(img, im, cx + math.cos(ang) * rr - im.width / 2, cy + math.sin(ang) * rr * .7 - im.height / 2)
    # the gang tumbling out of the tunnel toward the camera — everyone once, evenly spaced
    order = ['taras', 'bb', 'quin', 'noside', 'jeff', 'chops', 'cheesus', 'slaughter', 'errorgarden', 'giulio', 'deepcode',
             'luke', 'pondering', 'elegy', 'colin', 'pedrox', 'uh']
    span = f.d - .7
    for i, n in enumerate(order):
        t0 = i * span / len(order)
        ph = (f.t - t0) / .9
        if not 0 <= ph < 1:
            continue
        ang = i * 2.1 + .6
        rr = ph ** 1.6 * 300
        s = .3 + ph ** 1.5 * 3.2
        ch, an = FC.character(n, ('shock', 'cheer', 'hero', 'run_a')[i % 4], ('shock', 'happy', 'scared', 'hype')[i % 4], t=f.T, blink=False, shadow=False)
        big = ch.resize((max(2, int(ch.width * s)), max(2, int(ch.height * s))), Image.NEAREST)
        big = big.rotate((i * 53 + f.t * (140 if i % 2 else -140)) % 360, Image.NEAREST, expand=True)
        paste(img, big, cx + math.cos(ang) * rr - big.width / 2, cy + math.sin(ang) * rr * .7 - big.height / 2)
    # the Demon's eye opens in the centre at the end
    k = f.k(f.d - .9, f.d - .2)
    if k > 0:
        ew, eh = 70 * k + 10, max(1, 26 * k)
        d = ImageDraw.Draw(img)
        d.ellipse((cx - ew, cy - eh, cx + ew, cy + eh), fill=(255, 150, 30, 255), outline=(120, 30, 0, 255), width=2)
        if eh > 3:
            d.ellipse((cx - 7, cy - eh + 2, cx + 7, cy + eh - 2), fill=(20, 0, 10, 255))
        L = np.zeros((H, W, 3), np.float32)
        Wd.glow(L, cx, cy, 160, (255, 120, 30), .9 * k)
        img = Wd.apply_light(img, L, 1.0)
    E.speed_radial(img, f.T, cx, cy, (200, 160, 255), n=40, inner=150)
    return img


# ======================================================================= montage B
def scene_trex(f, lt):
    """Cretaceous chase — Taras, Luke and Cheesus flee the T-rex (Ep02 group)."""
    img = ST.prehistoric_bg(f.T, scroll=f.T * 520)
    d = ImageDraw.Draw(img)
    rx = 70 + math.sin(f.T * 3) * 8
    rex = ST.trex(f.T, True, .6 + .4 * math.sin(f.T * 10), 3)
    paste(img, rex, rx - 120, 214 - rex.height + 6)
    for i, (n, x, e, mk) in enumerate((('taras', 300, 'scared', ('sweat',)), ('luke', 362, 'shock', ('!',)), ('cheesus', 424, 'scared', ()))):
        ph = int(f.T * 10 + i) % 2
        hy = 214 - 30 + math.sin(f.T * 9 + i) * 3                    # gliding: ghostly trail behind the hips
        for k in range(5):
            tx = x - 14 - k * 12
            d.line((tx, hy - 6 + k, tx - 16, hy - 6 + k), fill=(255, 245, 225, 200 - k * 36), width=2)
            d.line((tx + 4, hy + 4 - k, tx - 10, hy + 4 - k), fill=(255, 245, 225, 160 - k * 30), width=1)
        put(img, n, x, 214, 'run_a' if ph else 'run_b', e, 1.25, f.T, marks=mk, hop=abs(math.sin(f.T * 6 + i)) * 3)
    E.speed_h(img, f.T, (255, 240, 210), n=26, speed=1800, seed=4)
    E.sfx_text(f, 640, 330, 'ドドドド', 54, (255, 255, 255), (150, 40, 0), 5, rot=8, shake=3)
    f.shake = 2
    return E.camera(img, 250, 140, 1.08)

def scene_mars(f, lt):
    """Mars, outside the base (Ep02 group) — Giulio plants the BASED flag, Uh cheers, Pedrox salutes, the Sergeant stands guard."""
    img = Wd.vgrad(W, H, [(0, (14, 6, 26)), (.5, (110, 46, 54)), (1, (210, 120, 80))])
    d = ImageDraw.Draw(img)
    stars(d, f.T, 60, 80, seed=2)
    d.ellipse((60, 26, 92, 58), fill=(60, 120, 230, 255))
    for ox, oy, rr in ((-6, -4, 6), (6, 6, 5), (-2, 10, 3)):
        d.ellipse((76 + ox - rr, 42 + oy - rr, 76 + ox + rr, 42 + oy + rr), fill=(80, 190, 90, 255))
    d.arc((60, 26, 92, 58), 300, 60, fill=(255, 255, 255, 255), width=2)
    d.ellipse((400, 30, 410, 38), fill=(170, 150, 140, 255))
    for k, (base, col, amp) in enumerate(((150, (130, 56, 50), 18), (176, (160, 70, 50), 10))):
        pts = [(x, base + int(amp * math.sin(x / (50 + k * 30) + k) + 5 * math.sin(x / 13 + k))) for x in range(0, W + 4, 4)]
        d.polygon(pts + [(W, H), (0, H)], fill=col + (255,))
    # Marsbase domes
    L = np.zeros((H, W, 3), np.float32)
    for bx, br in ((330, 34), (392, 22), (290, 18)):
        lay = layer(); dl = ImageDraw.Draw(lay)
        dl.pieslice((bx - br, 172 - br, bx + br, 172 + br), 180, 360, fill=(170, 220, 255, 90), outline=(220, 240, 255, 255))
        img.alpha_composite(lay); d = ImageDraw.Draw(img)
        for k in range(1, 4):
            d.arc((bx - br * k / 4, 172 - br, bx + br * k / 4, 172 + br), 180, 360, fill=(200, 230, 255, 255))
        d.rectangle((bx - br, 172, bx + br, 178), fill=(90, 90, 110, 255))
        Wd.glow(L, bx, 160, br * 1.4, (255, 220, 160), .4)
    d.line((430, 120, 430, 172), fill=(180, 180, 190, 255), width=2); d.line((424, 128, 436, 128), fill=(180, 180, 190, 255))
    if int(f.T * 2) % 2:
        d.point((430, 119), fill=(255, 40, 40, 255)); Wd.glow(L, 430, 119, 8, (255, 40, 40), .8)
    # rover
    d.rectangle((40, 176, 90, 188), fill=(220, 220, 230, 255), outline=(60, 60, 70, 255))
    d.rectangle((50, 168, 70, 176), fill=(120, 170, 220, 255), outline=(60, 60, 70, 255))
    for wx in (46, 66, 84):
        d.ellipse((wx - 5, 186, wx + 5, 196), fill=(40, 40, 46, 255)); d.point((wx, 191), fill=(150, 150, 160, 255))
    d.line((80, 168, 88, 156), fill=(200, 200, 210, 255)); d.ellipse((85, 152, 91, 158), outline=(200, 200, 210, 255))
    # foreground ground with rocks + footprints
    d.rectangle((0, 214, W, H), fill=(178, 86, 58, 255))
    rnd = random.Random(6)
    for i in range(30):
        x, y = rnd.randrange(W), rnd.randrange(218, H)
        r = rnd.randint(2, 7)
        d.ellipse((x - r, y - r * .6, x + r, y + r * .6), fill=(140, 62, 44, 255)); d.line((x - r + 1, y - r * .4, x, y - r * .6), fill=(210, 120, 84, 255))
    for k in range(8):
        d.ellipse((150 + k * 22, 250 - (k % 2) * 6, 158 + k * 22, 254 - (k % 2) * 6), fill=(150, 66, 46, 255))
    # the three with helmets
    plant = f.k(0, .35)
    flx, fly = 196, 236 - (1 - plant) * 20
    d.line((flx, fly - 70, flx, fly), fill=(220, 220, 230, 255), width=2)
    wave = [(flx + k * 6, fly - 70 + math.sin(f.T * 7 - k * .8) * 3 * (k / 8)) for k in range(9)]
    d.polygon(wave + [(p[0], p[1] + 26) for p in wave[::-1]], fill=(255, 90, 210, 255))
    for k in range(0, 9, 2):
        d.line((wave[k][0], wave[k][1], wave[k][0], wave[k][1] + 26), fill=(220, 60, 180, 255))
    Wd.tiny(img, flx + 8, fly - 60, 'BASED', (255, 255, 255, 255), 2)
    for i, (n, x, pose, e) in enumerate((('pedrox', 100, 'thumb', 'happy'), ('giulio', 170, 'hero', 'happy'), ('uh', 262, 'cheer', 'happy'), ('slaughter', 332, 'crossed', 'serious'))):
        an = put(img, n, x, 250, pose, e, 1.3, f.T)
        hx, hy = x, 250 - (an['feet'][1] - an['center'][1] + 1) * 1.3
        lay = layer(); dl = ImageDraw.Draw(lay)
        dl.ellipse((hx - 30, hy - 32, hx + 30, hy + 28), fill=(200, 230, 255, 46), outline=(220, 240, 255, 230), width=2)
        dl.arc((hx - 22, hy - 26, hx + 6, hy - 4), 200, 260, fill=(255, 255, 255, 255), width=2)
        img.alpha_composite(lay)
    d = ImageDraw.Draw(img)
    for i in range(30):                                             # drifting dust
        x = (rnd.random() * W + f.T * 30) % W; y = 150 + rnd.random() * 120
        d.point((x, y), fill=(240, 170, 130, 255))
    img = Wd.apply_light(img, L, 1.0)
    return E.camera(img, 220 - lt * 20, 160, 1.1)

def tap_scene(f):
    """Giulio's hand taps the Dark Tap (as in Ep01) — shockwave, monsters burst out of the console."""
    presses = (.06, .46)
    img = console_close(f, 'giulio', presses=presses, glow=2.2)
    lay = layer(); dl = ImageDraw.Draw(lay)
    for i, p in enumerate(presses):
        k = (f.t - p - .1) / .4
        if 0 <= k < 1:
            r = 20 + k * 260
            dl.ellipse((175 - r, 112 - r * .35, 175 + r, 112 + r * .35), outline=(220, 140, 255, int(230 * (1 - k))), width=3)
    img.alpha_composite(lay)
    for i in range(8):
        k = (f.t - .16 - i * .07) / .5
        if 0 <= k < 1.4:
            m = E.mon_sprite([1, 5, 8, 11, 14, 3, 18, 6][i], 1.2 + k)
            a = -math.pi / 2 + (i - 3.5) * .38
            rr = ease_out(min(1, k)) * 230
            paste(img, m, 175 + math.cos(a) * rr * 1.3 - m.width / 2, 110 + math.sin(a) * rr * .6 - m.height / 2)
    for p in presses:
        if p + .1 <= f.t < p + .16:
            f.flash = .45; f.flash_c = (180, 80, 255)
    if f.t > presses[0] + .1:
        E.sfx_text(f, 700, 140, 'タップ！', 70, (255, 255, 255), (120, 0, 160), 6, rot=-8, shake=2)
    return img

def standoff(f):
    """The gang (backs to camera) facing the BTC Demon over the ruins of the timelines."""
    t = f.t
    img = Wd.vgrad(W, H * 2, [(0, (10, 0, 16)), (.4, (60, 0, 60)), (.7, (170, 40, 60)), (1, (40, 10, 20))])
    d = ImageDraw.Draw(img)
    stars(d, f.T, 60, 200)
    big_h = H * 2
    # demon rises behind the horizon
    rise = ease(min(1, t / .4))
    dm, an = DM.demon_image('open', 'glow', 2 if t > .4 else 0, f.T)
    dm = dm.crop((0, 0, 170, 215))
    dmb = iscale(dm, 2)
    dx, dy = 240 - 80 * 2, 330 - rise * 330
    paste(img, dmb, dx, dy)
    L = np.zeros((big_h, W, 3), np.float32)
    Wd.glow(L, 240, dy + 88, 200, (255, 140, 30), .6)
    # floating timeline shards
    th = timeline_thumbs()
    for i, (x, y) in enumerate(((52, 120), (430, 100), (70, 250), (416, 236), (36, 360))):
        x += math.sin(f.T + i) * 6
        y += math.sin(f.T * 1.3 + i) * 5
        sh = th[i].resize((72, 40), Image.NEAREST).rotate(-12 + i * 6, Image.NEAREST, expand=True)
        paste(img, dim(sh, .8), x - sh.width / 2, y)
    # ruins horizon on fire
    rnd = random.Random(14)
    pts = [(0, 400)]
    x = 0
    while x < W:
        w_ = rnd.randint(16, 40); h_ = rnd.randint(10, 60)
        pts += [(x, 400 - h_), (x + w_, 400 - h_)]
        x += w_
    pts += [(W, 400), (W, big_h), (0, big_h)]
    d = ImageDraw.Draw(img)
    d.polygon(pts, fill=(20, 4, 20, 255))
    for i in range(12):
        DM.flame(img, 20 + i * 40, 404, f.T, 2, i)
        Wd.glow(L, 20 + i * 40, 390, 40, (210, 90, 255), .4)
    d.rectangle((0, 404, W, big_h), fill=(26, 8, 24, 255))
    # the gang, backs to camera, all 17 on the ridge
    pts = [(x, 470 + int(5 * math.sin(x / 37))) for x in range(0, W + 4, 4)]
    d.polygon(pts + [(W, big_h), (0, big_h)], fill=(14, 4, 14, 255))
    for i, n in enumerate(ROLL):
        bc = back_char(n, 'idle')
        bc = dim(bc, .55)
        x = 18 + i * 26.6
        y = 478 + int(5 * math.sin(x / 37)) + (i % 2) * 6
        paste(img, bc, x - bc.width / 2, y - bc.height)
    img = Wd.apply_light(img, L, 1.0)
    # laser eyes on the downbeat
    if t > .45:
        ex = dx + 80 * 2
        ey = dy + 44 * 2
        k = max(0, 1 - (t - .45) / .35)
        DM.laser_eyes(img, [(ex - 24, ey), (ex + 24, ey)], k, 500)
        if t < .52:
            f.impact = True
    # camera: tilt up from the gang to the demon
    cy = lerp(330, 150, ease(min(1, t / .4)))
    out = img.crop((0, int(cy - H / 2), W, int(cy + H / 2)))
    return out


# ======================================================================= the OP
def add_opening(ep, title_jp, title_en):
    def s_gap(f):
        return E.bg_solid((0, 0, 0))
    ep.shot(s_gap, dur=.7)
    ep.mus(np.zeros((10, 2)), 0)          # hard musical cut: silence before the OP hits
    op, op_len = M.m_op()                  # the original song and ending, as in Ep02 (director: m_op2's ending was wrong)
    beat = BEAT

    def op_title(f, final=False):
        """Title card — identical to the v1 OP (also the final episode-title screen)."""
        img = E.bg_solid((34, 0, 52))
        E.speed_radial(img, f.T, W // 2, H // 2, (150, 40, 210), n=110, inner=50)
        x = 14
        for n in ROLL:
            ch, an = FC.character(n, 'cheer' if (int(f.T / beat) + len(n)) % 2 else 'idle', 'happy', t=f.T, blink=False)
            sil = Image.fromarray(np.where(np.asarray(ch)[..., 3:] > 0, np.array([14, 0, 22, 255], np.uint8), 0).astype(np.uint8))
            paste(img, sil, x - sil.width / 2, H - sil.height + 30 - (3 if (int(f.T / beat * 2) + len(n)) % 2 else 0))
            x += 28
        k = ease_out(f.t / .2)
        sz = int(lerp(220, 150, k))
        E.title_text(f, 480, 190, 'ゴールゲート', sz, (255, 255, 255), (120, 0, 70), 10, fnt=E.sfx_font(sz))
        if f.t > .2:
            E.title_text(f, 480, 290, 'G H O U L G A T E', 34, (255, 120, 220), (30, 0, 40), 4)
        if final:
            logo = Image.open(paths.LOGO).convert('RGBA')
            if f.t > .3:
                def put_logo(hd, logo=logo):
                    lg = logo.resize((logo.width * 2, logo.height * 2), Image.NEAREST)
                    hd.alpha_composite(lg, ((960 - lg.width) // 2, 320))
                f.hi.append(put_logo)
            if f.t > .9:
                E.title_text(f, 480, 410, title_jp, 40, (255, 240, 130), (50, 0, 40), 5)
                E.title_text(f, 480, 452, title_en, 22, (255, 255, 255), (50, 0, 40), 3)
            if f.t > f.d - .5:
                f.flash = (f.t - (f.d - .5)) / .5; f.flash_c = (0, 0, 0)
        if f.t < .25:
            f.flash = 1 - f.t / .25
        return img
    ep.shot(op_title, dur=4 * beat)
    op_idx = ep.mus(op, 0, rms=.16, fout=.6)
    ep.sub_extra.append((ep.cur + .2, ep.cur + 4.5, '{\\an9\\fs34}OPENING THEME 「GHOULGATE!」\\N{\\fs26}歌：骸骨少女隊'))

    # ---------------------------------------------------------------- roll call: one beat each
    def op_roll(f):
        i = min(len(ROLL) - 1, int(f.t / beat))
        lt = f.t - i * beat
        n = ROLL[i]
        col = COL[n]
        pose, expr, marks, key = ROLL_LOOK[n]
        img = roll_bg(n, f.T, lt)
        # diagonal colour band with halftone dots behind the ghoul
        lay = layer(); dl = ImageDraw.Draw(lay)
        sl = (1 - ease_out(lt / .12)) * 120
        dl.polygon([(250 + sl, 0), (420 + sl, 0), (360 + sl, H), (190 + sl, H)], fill=col + (150,))
        for yy in range(0, H, 6):
            for xx in range(180, 430, 6):
                r_ = 1 + ((xx + yy) // 6) % 2
                if 190 + sl + (H - yy) * 60 / H < xx < 360 + sl + (H - yy) * 60 / H:
                    dl.ellipse((xx - r_ / 2, yy - r_ / 2, xx + r_ / 2, yy + r_ / 2), fill=(255, 255, 255, 60))
        dl.line((180 + sl, H, 240 + sl, 0), fill=(255, 255, 255, 200), width=2)
        img.alpha_composite(lay)
        E.speed_h(img, f.T, tuple(min(255, int(c * 1.15)) for c in col), n=18, speed=1500, seed=i)
        k = ease_out(lt / .14)
        x = lerp(470, 330, k) + lt * 12
        big, an = ghoul(n, pose, expr, f.T, marks, 3, line=(255, 255, 255, 255))
        paste(img, big, x - big.width / 2, H - big.height + 40)
        # sparkle dust in front
        d = ImageDraw.Draw(img)
        rnd = random.Random(i)
        for q in range(20):
            px = (rnd.random() * W - f.t * 80) % W; py = rnd.random() * H
            d.point((px, py), fill=(255, 255, 255, 255))
        if lt < .08:
            img = whip(img, 1 - lt / .08)
        # face cut-in panel + name
        panel = face_panel(n, expr, f.T, lt)
        px = int(lerp(-200, 40, ease_out(lt / .12)))
        f.hi.append(lambda hd, p=panel, px=px: hd.alpha_composite(p, (px, 130)))
        nm_size = 64 if len(JPN[n]) <= 6 else 42
        E.title_text(f, 60, 380, JPN[n], nm_size, (255, 255, 255), tuple(int(c * .25) for c in col), 6, fnt=E.sfx_font(nm_size), anchor='lm')
        E.title_text(f, 64, 440, ENN[n], 26, col, (0, 0, 0), 4, anchor='lm')
        credits_ = [('原作', 'BASED GHOULS'), ('監督', '骨川 夜一'), ('キャラクターデザイン', '髑髏谷 ミカ'), ('ドット作画監督', '灰原 点')]
        r, nm = credits_[min(3, int(f.t / (17 * beat / 4)))]
        credit(f, r, nm)
        return img
    ep.shot(op_roll, dur=17 * beat)

    # ---------------------------------------------------------------- hero lineup in the graveyard (all 17)
    back = ['quin', 'taras', 'luke', 'noside', 'errorgarden', 'elegy', 'jeff', 'pondering', 'deepcode']
    front = ['chops', 'colin', 'uh', 'pedrox', 'slaughter', 'cheesus', 'bb', 'giulio']
    look = {'quin': ('crossed', 'deadpan'), 'taras': ('shrug', 'happy'), 'luke': ('cheer', 'sparkle'), 'noside': ('cheer', 'happy'),
            'errorgarden': ('cheer', 'happy'), 'elegy': ('smoke', 'deadpan'), 'jeff': ('idle', 'deadpan'), 'pondering': ('crossed', 'smug'),
            'deepcode': ('smoke', 'menace'), 'chops': ('point', 'hype'), 'colin': ('fist', 'evil'), 'uh': ('cheer', 'happy'),
            'pedrox': ('thumb', 'happy'), 'slaughter': ('crossed', 'serious'), 'cheesus': ('cheer', 'happy'), 'bb': ('hero', 'happy'),
            'giulio': ('thumb', 'happy')}

    def op_gang(f):
        b = f.t / beat
        img = graveyard(f.T, f.t / f.d)
        d = ImageDraw.Draw(img)
        # back row rises from behind the ridge
        for i, n in enumerate(back):
            k = ease_out((b - i * .12) / 1.0)
            if k <= 0:
                continue
            p, e = look[n]
            x = 34 + i * 51.5
            gy = 194 + int(4 * math.sin(x / 40))
            hop = 3 if (int(b) + i) % 2 and b > 3 else 0
            put(img, n, x, gy + (1 - k) * 160, p, e, 1.3, f.T, hop=hop)
        tombstones(img, f.T)
        # front row lands on beat 2
        for i, n in enumerate(front):
            k = ease_out((b - 2 - i * .1) / .6)
            if k <= 0:
                continue
            p, e = look[n]
            x = 34 + i * 58.8
            put(img, n, x, 272 + (1 - k) * 60, p, e, 1.45, f.T, hop=(4 if (int(b) + i) % 2 and b > 3.5 else 0))
        if abs(b - 2) < .1:
            f.flash = .5; f.flash_c = (255, 220, 255)
        cam_y = lerp(175, 140, ease(f.t / f.d))
        out = E.camera(img, 240, cam_y, lerp(1.18, 1.0, ease(f.t / f.d)))
        credit(f, 'シリーズ構成・脚本', '墓田 静香')
        return out
    ep.shot(op_gang, dur=7 * beat)

    # ---------------------------------------------------------------- montage A: four "other episodes"
    def op_montage_a(f):
        scenes_ = (scene_beach, scene_rooftop, scene_live, scene_festival)
        i = min(3, int(f.t / (2 * beat)))
        lt = f.t - i * 2 * beat
        img = scenes_[i](f, lt / (2 * beat))
        if lt < .06:
            f.flash = max(f.flash, .6)
        credit(f, '音楽', '鳴神 響八')
        return img
    ep.shot(op_montage_a, dur=8 * beat)

    # ---------------------------------------------------------------- timeline vortex (all 17)
    def op_vortex(f):
        img = vortex(f)
        if f.t < .1:
            f.flash = 1 - f.t / .1
        if f.t > f.d - .2:
            f.flash = (f.t - (f.d - .2)) / .2; f.flash_c = (255, 200, 120)
        credit(f, '美術監督', '地下室 蓮')
        return img
    ep.shot(op_vortex, dur=8 * beat)

    # ---------------------------------------------------------------- montage B: Cretaceous · Mars · Giulio taps · the standoff
    def op_montage_b(f):
        if f.t < 2 * beat:
            img = scene_trex(f, f.t / (2 * beat))
        elif f.t < 4 * beat:
            img = scene_mars(f, (f.t - 2 * beat) / (2 * beat))
        elif f.t < 6 * beat:
            g = E.F(ep, f.T, f.t - 4 * beat, 2 * beat, [])
            img = tap_scene(g)
            f.hi.extend(g.hi); f.flash = g.flash; f.flash_c = g.flash_c
        else:
            g = E.F(ep, f.T, f.t - 6 * beat, 2 * beat, [])
            img = standoff(g)
            f.impact = g.impact
        if (f.t % (2 * beat)) < .05 and f.t < 6.1 * beat and not 4 * beat <= f.t < 4.1 * beat:
            f.flash = .7
        credit(f, '主題歌「GHOULGATE!」', '骸骨少女隊')
        return img
    ep.shot(op_montage_b, dur=8 * beat)
    # the final title holds until the last chord and its tail have rung out (v3: the music was being cut ~1.9 s early)
    ep.shot(lambda f: op_title(f, True), dur=4 * beat + 1.6)
    # like Ep02: the last chord rings out over the episode's next shot — the episode must not start a new music cue before this
    ep.op_music_end = ep.music[op_idx]['t'] + len(op) / 44100
    return ep
