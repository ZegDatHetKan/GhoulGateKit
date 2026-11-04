"""v2 engine: world/camera rendering, actors, monsters sim, FX, subtitles, mixing, encode."""
import os, math, random, subprocess
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import gaussian_filter
import world as Wd
import face as FC
import skeleton as K
import voice as V

W, H = Wd.W, Wd.H
OW, OH = 960, 540
FPS = 24
import paths
HERE = paths.ENGINE
ROOT = paths.ROOT
BUILD = os.path.join(paths.ENGINE, 'build')    # each episode script overrides this with its own build dir
FONTS = paths.FONTS

@lru_cache(None)
def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)

def sfx_font(size):
    return font('DelaGothicOne-Regular.ttf', size)

def ui_font(size):
    return font('MPLUSRounded1c-ExtraBold.ttf', size)

def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)

def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3

def lerp(a, b, k):
    return a + (b - a) * k

def blank(c=(0, 0, 0)):
    return Image.new('RGBA', (W, H), c + (255,))

def paste(dst, im, x, y):
    x, y = int(round(x)), int(round(y))
    x0, y0 = max(0, -x), max(0, -y)
    x1, y1 = min(im.width, dst.width - x), min(im.height, dst.height - y)
    if x1 > x0 and y1 > y0:
        dst.alpha_composite(im.crop((x0, y0, x1, y1)), (x + x0, y + y0))

def iscale(im, k):
    if k == 1:
        return im
    return im.resize((max(1, int(round(im.width * k))), max(1, int(round(im.height * k)))), Image.NEAREST)

# ======================================================================= timeline
class Line:
    def __init__(self, who, jp, en, emo, start, say=None):
        """say: optional text actually spoken (e.g. monster gibberish) while the subtitles show jp/en."""
        self.who, self.jp, self.en, self.emo, self.start = who, jp, en, emo, start
        self.say = say
        import re
        self.audio = V.synth(who, say if say else re.sub('■+', 'ピー', jp), emo)
        self.dur = len(self.audio) / V.SR
        self.env = V.envelope(self.audio)
        self.end = self.start + self.dur

class Ep:
    def __init__(self):
        self.shots, self.lines, self.sfx, self.music, self.spawns, self.sub_extra = [], [], [], [], [], []
        self.t = 0.0
        self.cur = 0.0

    def shot(self, fn, dur=None, lines=(), pre=.25, post=.42, gap=.18, min_dur=1.0):
        """Lines play sequentially (never on top of each other). Duration follows the voices."""
        start = self.t
        self.cur = start
        t = pre
        made = []
        for l in lines:
            who, jp, en = l[:3]
            opts = l[3] if len(l) > 3 else {}
            emo = opts.get('emo', 'normal')
            if 'at' in opts:
                t = opts['at']
            ln = Line(who, jp, en, emo, start + t, say=opts.get('say'))
            made.append(ln)
            self.lines.append(ln)
            t += ln.dur + opts.get('gap', gap)
        d = max(min_dur, (t - gap + post) if made else 0, dur or 0)
        self.shots.append((start, d, fn, made))
        self.t += d
        return start, made

    def fx(self, name, at=0.0, gain=1.0, absolute=False):
        self.sfx.append(((at if absolute else self.cur + at), name, gain))

    def mus(self, arr, at=0.0, rms=None, fin=0.0, fout=0.0, absolute=False, gain=1.0, overlay=False):
        """Music cues are sequential: each one is cut (with a short fade) where the next starts."""
        self.music.append(dict(t=(at if absolute else self.cur + at), arr=arr, rms=rms, fin=fin, fout=fout, gain=gain, overlay=overlay))
        return len(self.music) - 1

    def spawn(self, n, at=0.0, behaviour='run', scale=1.0):
        self.spawns.append((self.cur + at, n, behaviour, scale))
        self.fx('spawn', at, .8)

    # ---- speech helpers
    def mouth(self, who, T):
        for l in self.lines:
            if l.who == who and l.start <= T < l.end:
                i = int((T - l.start) * FPS)
                return int(l.env[min(i, len(l.env) - 1)])
        return 0

    def speaking(self, who, T):
        return any(l.who == who and l.start <= T < l.end for l in self.lines)

    def speaker(self, T):
        for l in self.lines:
            if l.start <= T < l.end:
                return l.who
        return None

# ======================================================================= frame context
class F:
    def __init__(self, ep, T, t, d, lines):
        self.ep, self.T, self.t, self.d, self.lines = ep, T, t, d, lines
        self.hi = []              # callables on the 960x540 frame
        self.shake = 0
        self.flash = 0.0
        self.flash_c = (255, 255, 255)
        self.impact = False
        self.grade = None
        self.bloom = .5
        self.vignette = .35
        self.letterbox = 0

    def mouth(self, who):
        return self.ep.mouth(who, self.T)

    def talking(self, who):
        return self.ep.speaking(who, self.T)

    def k(self, a, b):
        """eased progress within [a,b] seconds of the shot"""
        return ease((self.t - a) / max(1e-6, b - a))

# ======================================================================= actors
def talk_pose(f, who, base='idle'):
    if not f.talking(who):
        return base
    ph = int(f.T * 2.2 + len(who)) % 3
    return ('talk_a', 'talk_b', base)[ph]

def actor(f, name, expr='neutral', pose=None, marks=(), look=0, legs=True, bob=0, talkpose=True):
    m = f.mouth(name)
    if pose is None:
        pose = talk_pose(f, name) if talkpose else 'idle'
    img, an = FC.character(name, pose, expr, mouth=m, t=f.T, look=look, legs=legs, marks=marks, bob=bob)
    return img, an

def place(world, img, an, x, y, anchor='feet', flip=False, scale=1):
    if flip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if scale != 1:
        img = iscale(img, scale)
    ax, ay = an[anchor]
    if flip:
        ax = img.width / scale - ax if scale != 1 else img.width - ax
    paste(world, img, x - ax * scale, y - ay * scale)

# seat plan in the crypt (x, pelvis/feet y, mode)
SEATS = {
    'quin':        (240, 134, 'throne'),
    'taras':       (148, 192, 'back'), 'luke': (180, 190, 'back'),
    'noside':      (300, 192, 'back'), 'errorgarden': (332, 192, 'back'),
    'elegy':       (132, 212, 'front'), 'jeff': (166, 214, 'front'), 'pondering': (198, 212, 'front'),
    'cheesus':     (230, 214, 'front'), 'chops': (262, 212, 'front'), 'colin': (294, 212, 'front'),
    'uh':          (326, 212, 'front'),
    'slaughter':   (96, 222, 'end'), 'pedrox': (386, 222, 'end'),
    'deepcode':    (40, 232, 'couch'), 'bb': (76, 232, 'couch'),
}
ORDER = ['quin', 'taras', 'luke', 'noside', 'errorgarden', 'elegy', 'jeff', 'pondering', 'cheesus', 'chops', 'colin', 'uh',
         'slaughter', 'pedrox', 'deepcode', 'bb']

def seat_pos(name):
    return SEATS[name][:2]

def look_dir(name, target_x):
    x = SEATS[name][0] if name in SEATS else 240
    if target_x is None:
        return 0
    return -1 if target_x < x - 6 else (1 if target_x > x + 6 else 0)

# ======================================================================= monsters (simulated)
MON_SCALE = 0.85

@lru_cache(None)
def mon_sprite(n, s=1.0):
    p = os.path.join(paths.SPRITES, 'monsters', f'monster{n}.png')
    im = Image.open(p).convert('RGBA')
    k = MON_SCALE * s
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.NEAREST)

@lru_cache(None)
def mon_sprite_hd(n, height=110):
    """High-detail monster sprite (assets/sprites/monsters_hd) scaled to a target height — for close-ups / interviews."""
    im = Image.open(os.path.join(paths.SPRITES, 'monsters_hd', f'monster{n}.png')).convert('RGBA')
    k = height / im.height
    if k >= 1:
        k = max(1, round(k))
        return im.resize((im.width * k, im.height * k), Image.NEAREST)
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.NEAREST)

FLYERS = {4, 10, 15, 17}

def mon_state(n, ts, T, behaviour, scale, origin=Wd.PORTAL_POS):
    """Deterministic monster position/pose at time T (seconds since episode start)."""
    age = T - ts
    rnd = random.Random(n * 977)
    ox, oy = origin
    if age < .45:
        k = ease_out(age / .45)
        return dict(x=ox, y=oy + (1 - k) * 14, sx=.35 + .75 * k, sy=1.35 - .35 * k, rise=True, dirn=1)
    a = age - .45
    if n in FLYERS or behaviour == 'fly':
        cx = 60 + rnd.random() * 360
        x = cx + math.sin(a * (.6 + rnd.random() * .5) + n) * (60 + rnd.random() * 60)
        y = 70 + rnd.random() * 60 + math.sin(a * 1.7 + n) * 18
        x = lerp(ox, x, ease(a / 1.0)); y = lerp(oy - 20, y, ease(a / 1.0))
        return dict(x=x, y=y, sx=1, sy=1, rise=False, dirn=1 if math.cos(a + n) > 0 else -1)
    if behaviour == 'table':
        x = 140 + (math.sin(a * .9 + n) * .5 + .5) * 200
        hop = abs(math.sin(a * 6 + n)) * 6
        y = 194 - hop
        x = lerp(ox, x, ease(a / .8)); y = lerp(oy, y, ease(a / .8))
        return dict(x=x, y=y, sx=1, sy=1 - .1 * (hop < 1), rise=False, dirn=1 if math.cos(a * .9 + n) > 0 else -1)
    # runner: bounce around the floor
    vx = (70 + rnd.random() * 90) * (1 if rnd.random() < .5 else -1)
    vy = (25 + rnd.random() * 40) * (1 if rnd.random() < .5 else -1)
    x0, x1, y0, y1 = 20, 460, 172, 266
    def bounce(p, v, lo, hi):
        span = hi - lo
        q = (p - lo + v * a) % (2 * span)
        return (lo + q if q < span else hi - (q - span)), (1 if q < span else -1) * (1 if v > 0 else -1)
    x, dx = bounce(ox, vx, x0, x1)
    y, _ = bounce(oy, vy, y0, y1)
    hop = abs(math.sin(a * (7 + n % 5))) * (6 + n % 4)
    return dict(x=x, y=y - hop, sx=1 + (.12 if hop < 1 else 0), sy=1 - (.12 if hop < 1 else 0), rise=False, dirn=dx, ground=y)

def draw_monsters(f, world, upto=None, frozen=False, flee_cb=None):
    items = []
    for ts, n, beh, sc in f.ep.spawns:
        if ts > f.T or (upto and n not in upto):
            continue
        st = mon_state(n, ts, ts + 2.0 if frozen and f.T - ts > 2 else f.T, beh, sc)
        items.append((st['y'], n, st, sc, ts))
    items.sort()
    for _, n, st, sc, ts in items:
        im = mon_sprite(n, sc)
        if st['dirn'] < 0:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        w2, h2 = int(im.width * st['sx']), int(im.height * st['sy'])
        im2 = im.resize((max(1, w2), max(1, h2)), Image.NEAREST)
        if st.get('ground') is not None:
            sh = Image.new('RGBA', (w2, 6), (0, 0, 0, 0))
            ImageDraw.Draw(sh).ellipse((0, 0, w2 - 1, 5), fill=(0, 0, 0, 90))
            paste(world, sh, st['x'] - w2 / 2, st['ground'] - 3)
        paste(world, im2, st['x'] - w2 / 2, st['y'] - h2)
        if f.T - ts < .5:
            Wd.portal(world, *Wd.PORTAL_POS, f.T, 26, 1 - (f.T - ts) / .5 * .3)
        if not frozen and int(f.T * 3 + n) % 7 == 0 and st.get('ground'):
            # dust puffs while running
            d = ImageDraw.Draw(world)
            for i in range(3):
                d.ellipse((st['x'] - 8 + i * 5, st['ground'] - 3, st['x'] - 5 + i * 5, st['ground']), fill=(170, 150, 190, 150))

# ======================================================================= the crypt world
def crypt_world(f, night=False, who=None, expr=None, pose=None, marks=None, dy=None, look_at=None,
                hide=(), extras_back=(), extras_front=(), monsters=False, mon_upto=None, console_glow=1.0,
                dark=0.0, untap=0.0, standing=(), sleep=(), lights_extra=(), focus=None, light=True, frozen=False, console=True):
    """Render the crypt with the gang. standing: list of (name, x, feet_y, kw) drawn free on the floor."""
    expr = expr or {}; pose = pose or {}; marks = marks or {}; dy = dy or {}
    world = Wd.room_bg(f.T, night)
    focus_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0)) if focus else None
    spk = f.ep.speaker(f.T)
    if look_at is None and spk:
        look_x = SEATS[spk][0] if spk in SEATS else 240
    else:
        look_x = look_at
    names = [n for n in ORDER if n not in hide and (who is None or n in who)]
    def draw_seated(n):
        x, y, mode = SEATS[n]
        e = expr.get(n, 'sleep' if n in sleep else 'neutral')
        p = pose.get(n, 'slump' if n in sleep else ('table' if mode == 'front' else 'idle'))
        if f.talking(n) and n not in pose:
            p = talk_pose(f, n, p)
        mk = marks.get(n, ())
        if n in sleep and not mk:
            mk = ()
        img, an = actor(f, n, e, p, mk, look=look_dir(n, look_x), legs=False, bob=0)
        breath = int((math.sin(f.T * (1.3 if n in sleep else 2.1) + len(n)) + 1) * .5 + .3)
        target = focus_layer if (focus and n in focus) else world
        # anchor seated bodies by their lowest pixel (pelvis)
        an2 = dict(an); an2['seat'] = (an['feet'][0], an['feet'][1])
        place(target, img, an2, x, y + breath + dy.get(n, 0), 'seat')
        if n in sleep and n in ('jeff', 'quin', 'taras', 'uh', 'bb', 'pondering', 'luke', 'deepcode'):
            zzz(target, x + 10, y - 40 + dy.get(n, 0), f.T + len(n))
    for e in extras_back:
        e(world, focus_layer)
    for n in [n for n in names if SEATS[n][2] in ('throne', 'back')]:
        draw_seated(n)
    for n in [n for n in names if SEATS[n][2] == 'front']:
        draw_seated(n)
    Wd.table_layer(world, f.T, night)
    for n in [n for n in names if SEATS[n][2] in ('end', 'couch')]:
        draw_seated(n)
    d = ImageDraw.Draw(world)
    d.rounded_rectangle((14, 226, 104, 248), 5, fill=(46, 90, 110, 255) if not night else (16, 30, 40, 255), outline=(14, 30, 40, 255))
    # console
    if console:                                    # Ep05 ending: Nick takes the Dark Tap away
        Wd.console(world, *Wd.CONSOLE_POS, f.T, dark, untap, console_glow * (1.6 if night else 1))
    # free-standing actors + monsters, sorted by depth
    drawables = []
    for item in standing:
        n, x, y = item[:3]
        kw = item[3] if len(item) > 3 else {}
        drawables.append((y, 'g', (n, x, y, kw)))
    drawables.sort(key=lambda d_: d_[0])
    for y, kind, (n, x, yy, kw) in drawables:
        p = kw.get('pose', 'idle')
        if f.talking(n) and 'pose' not in kw:
            p = talk_pose(f, n)
        img, an = actor(f, n, kw.get('expr', 'neutral'), p, kw.get('marks', ()), look=kw.get('look', 0), legs=True, bob=kw.get('bob', 0))
        target = focus_layer if (focus and n in focus) else world
        place(target, img, an, x, yy - kw.get('hop', 0), 'feet', flip=kw.get('flip', False), scale=kw.get('scale', 1))
    if monsters:
        draw_monsters(f, world, mon_upto, frozen)
    for e in extras_front:
        e(world, focus_layer)
    if light:
        L = Wd.room_lights(f.T, night, console_glow, lights_extra)
        world = Wd.apply_light(world, L, .78 if not night else .9)
    return world, focus_layer

def zzz(img, x, y, t):
    d = ImageDraw.Draw(img)
    for i in range(3):
        ph = (t * .45 + i / 3) % 1
        xx, yy = x + ph * 12 + i * 2, y - ph * 20
        s = 2 + i
        a = int(255 * (1 - ph))
        d.line((xx, yy, xx + s, yy), fill=(200, 220, 255, a)); d.line((xx + s, yy, xx, yy + s), fill=(200, 220, 255, a)); d.line((xx, yy + s, xx + s, yy + s), fill=(200, 220, 255, a))

# ======================================================================= camera
def camera(world, cx, cy, zoom, focus_layer=None, dof=0.0, dutch=0.0):
    """Crop world around (cx,cy) at zoom; optional depth-of-field blur on non-focus layer."""
    zoom = max(1.0, zoom)
    w_, h_ = W / zoom, H / zoom
    x0 = min(max(0, cx - w_ / 2), W - w_)
    y0 = min(max(0, cy - h_ / 2), H - h_)
    box = (x0, y0, x0 + w_, y0 + h_)
    out = world.resize((W, H), Image.NEAREST, box=box)
    if dof > 0:
        out = out.filter(ImageFilter.GaussianBlur(dof))
    if focus_layer is not None:
        fl = focus_layer.resize((W, H), Image.NEAREST, box=box)
        out.alpha_composite(fl)
    if dutch:
        out = out.rotate(dutch, Image.NEAREST, expand=False, fillcolor=(0, 0, 0, 255))
    return out

# ======================================================================= abstract anime backgrounds
def bg_solid(c):
    return Image.new('RGBA', (W, H), tuple(c) + (255,))

def speed_radial(img, t, cx, cy, color, n=90, inner=80, seed=0):
    d = ImageDraw.Draw(img)
    rnd = random.Random(int(t * 12) + seed)
    for i in range(n):
        a = rnd.random() * math.tau
        r0 = inner + rnd.random() * 60
        wdt = rnd.choice((1, 1, 2, 3))
        d.line((cx + math.cos(a) * r0, cy + math.sin(a) * r0, cx + math.cos(a) * 600, cy + math.sin(a) * 600), fill=color, width=wdt)

def speed_h(img, t, color, n=50, speed=900, seed=0):
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    for i in range(n):
        y = rnd.randrange(H)
        ln = rnd.randint(30, 180)
        x = (rnd.random() * (W + 300) - t * speed * (.6 + rnd.random())) % (W + 300) - 150
        d.line((x, y, x + ln, y), fill=color, width=rnd.choice((1, 1, 2)))

def sparkles(img, t, n=30, seed=5, color=(255, 255, 255)):
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    for i in range(n):
        x, y = rnd.randrange(W), rnd.randrange(H)
        k = 1 + int((math.sin(t * 9 + i) + 1) * 1.6)
        d.line((x - k, y, x + k, y), fill=color); d.line((x, y - k, x, y + k), fill=color)

def bg_grad(c0, c1):
    return Wd.vgrad(W, H, [(0, c0), (1, c1)])

def portrait(f, bg, name, expr='neutral', pose=None, marks=(), scale=4, x=W // 2, y=None, legs=False, look=0, flip=False, bob=0, mouth=None):
    """Big character over an abstract background (anime reaction shot)."""
    img = bg.copy() if bg is not None else blank()
    p = pose or talk_pose(f, name)
    ch, an = FC.character(name, p, expr, mouth=f.mouth(name) if mouth is None else mouth, t=f.T, look=look, legs=legs, marks=marks, bob=bob)
    if flip:
        ch = ch.transpose(Image.FLIP_LEFT_RIGHT)
    big = iscale(ch, scale)
    breathe = int((math.sin(f.T * 2.2) + 1) * .5 * scale * .5)
    if y is None:
        yy = 30 - an['head_top'][1] * scale
        yy = max(yy, H - big.height + scale * 4) if big.height + yy < H else yy
    else:
        yy = y
    paste(img, big, x - big.width / 2, yy + breathe)
    return img

# ======================================================================= hi-res overlays
def sfx_text(f, x, y, s, size=64, fill=(255, 255, 255), stroke=(0, 0, 0), sw=5, rot=0, shake=0, alpha=255):
    def fn(hd):
        rnd = random.Random(int(f.T * 30))
        dx = rnd.randint(-shake, shake) if shake else 0
        dy = rnd.randint(-shake, shake) if shake else 0
        fnt = sfx_font(size)
        tmp = Image.new('RGBA', (int(fnt.getlength(s) + sw * 4 + 20), size + sw * 4 + 30), (0, 0, 0, 0))
        dd = ImageDraw.Draw(tmp)
        dd.text((sw * 2 + 10, sw * 2 + 5), s, font=fnt, fill=fill + (alpha,), stroke_width=sw, stroke_fill=stroke + (alpha,))
        if rot:
            tmp = tmp.rotate(rot, Image.BICUBIC, expand=True)
        hd.alpha_composite(tmp, (int(x - tmp.width / 2 + dx), int(y - tmp.height / 2 + dy)))
    f.hi.append(fn)

def title_text(f, x, y, s, size, fill=(255, 255, 255), stroke=(0, 0, 0), sw=4, fnt=None, anchor='mm'):
    def fn(hd):
        d = ImageDraw.Draw(hd)
        d.text((x, y), s, font=fnt or ui_font(size), fill=fill, stroke_width=sw, stroke_fill=stroke, anchor=anchor)
    f.hi.append(fn)

# ======================================================================= post
def post(img, f):
    a = np.asarray(img.convert('RGB')).astype(np.float32)
    if f.impact:
        g = a.mean(-1, keepdims=True)
        m = (g > 90).astype(np.float32)
        a = m * np.array([255, 255, 255]) + (1 - m) * np.array([10, 0, 20])
        a = np.repeat(a, 1, axis=0)
    if f.grade is not None:
        mul, add = f.grade
        a = a * np.array(mul) + np.array(add)
    if f.flash > 0:
        a = a * (1 - min(1, f.flash)) + np.array(f.flash_c) * min(1, f.flash)
    a = np.clip(a, 0, 255)
    # upscale x2 nearest
    a = a.repeat(2, 0).repeat(2, 1)
    if f.bloom > 0:
        small = a[::4, ::4]
        lum = small.mean(-1, keepdims=True)
        bright = np.clip(small - 150, 0, 255) * (lum > 150)
        bl = gaussian_filter(bright, sigma=(6, 6, 0))
        bl = bl.repeat(4, 0).repeat(4, 1)[:a.shape[0], :a.shape[1]]
        a = a + bl * f.bloom
    if f.vignette > 0:
        yy, xx = np.mgrid[:OH, :OW]
        r = np.sqrt(((xx - OW / 2) / (OW / 2)) ** 2 + ((yy - OH / 2) / (OH / 2)) ** 2)
        a = a * (1 - f.vignette * np.clip(r - .55, 0, 1)[..., None] ** 1.5)
    a = np.clip(a, 0, 255).astype(np.uint8)
    out = Image.fromarray(a).convert('RGBA')
    if f.letterbox:
        d = ImageDraw.Draw(out)
        d.rectangle((0, 0, OW, f.letterbox), fill=(0, 0, 0, 255))
        d.rectangle((0, OH - f.letterbox, OW, OH), fill=(0, 0, 0, 255))
    for fn in f.hi:
        fn(out)
    return out.convert('RGB')

def shake_xy(T, amp, seed=0):
    if amp <= 0:
        return 0, 0
    rnd = random.Random(int(T * 30) + seed)
    return rnd.randint(-amp, amp), rnd.randint(-amp, amp)

def render_frame(ep, T):
    for start, dur, fn, lines in ep.shots:
        if start <= T < start + dur:
            break
    f = F(ep, T, T - start, dur, lines)
    img = fn(f)
    if f.shake:
        dx, dy = shake_xy(T, f.shake)
        im2 = Image.new('RGBA', img.size, (0, 0, 0, 255))
        im2.paste(img, (dx, dy))
        img = im2
    return post(img, f)

# ======================================================================= subtitles (ASS, fansub style)
def ass_time(t):
    t = max(0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'

def ass_color(rgb):
    r, g, b = rgb
    return f'&H00{b:02X}{g:02X}{r:02X}'

def write_ass(ep, path, colors):
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: JP,Rounded Mplus 1c ExtraBold,62,&H00FFFFFF,&H000000FF,&H00101010,&H90000000,0,0,0,0,100,100,1,0,1,5,2,2,80,80,122,1
Style: EN,Rounded Mplus 1c Bold,42,&H0090F0FF,&H000000FF,&H00101010,&H90000000,0,0,0,0,100,100,0,0,1,3.5,1.5,2,80,80,52,1
Style: SIGN,Rounded Mplus 1c ExtraBold,40,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,0,8,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for i, l in enumerate(ep.lines):
        nxt = ep.lines[i + 1].start if i + 1 < len(ep.lines) else l.end + 2
        end = min(max(l.end + .35, l.start + 1.3), nxt - .02)
        oc = colors.get(l.who, (16, 16, 16))
        oc = tuple(int(c * .35) for c in oc)
        import re as _re
        def censor(s, restore):
            return _re.sub('■+', lambda m: '{\\c&H000000&\\3c&HC8C8C8&}' + '■' * len(m.group(0)) + '{\\r' + restore + '}', s)
        jp_txt = l.jp
        if len(jp_txt) > 34:                         # long Japanese line: break at the punctuation nearest the middle (else it runs off-screen)
            cuts = [i + 1 for i, ch in enumerate(jp_txt[:-1]) if ch in '。、！？…'] or [len(jp_txt) // 2]
            c = min(cuts, key=lambda i: abs(i - len(jp_txt) / 2))
            jp_txt = jp_txt[:c] + '\\N' + jp_txt[c:]
        jp = censor(jp_txt, '\\3c' + ass_color(oc))
        en = censor(l.en, '')
        mv = 170 if len(l.en) > 74 else 0
        ev.append(f'Dialogue: 0,{ass_time(l.start - .05)},{ass_time(end)},JP,{l.who},0,0,{mv},,{{\\3c{ass_color(oc)}}}{jp}')
        ev.append(f'Dialogue: 1,{ass_time(l.start - .05)},{ass_time(end)},EN,{l.who},0,0,0,,{en}')
    for s, e, txt in ep.sub_extra:
        ev.append(f'Dialogue: 2,{ass_time(s)},{ass_time(e)},SIGN,,0,0,0,,{txt}')
    open(path, 'w', encoding='utf-8').write(head + '\n'.join(ev) + '\n')

# ======================================================================= audio mix
def build_audio(ep, total, M):
    n = int(total * V.SR) + V.SR
    music = np.zeros((n, 2))
    seq_cues = sorted([m for m in ep.music if not m['overlay']], key=lambda m: m['t'])
    for k, m in enumerate(ep.music):
        if m['arr'] is None:
            continue
        x = m['arr']
        nxt = [c['t'] for c in seq_cues if c['t'] > m['t'] + 1e-3]
        if not m['overlay'] and nxt:
            keep = int((nxt[0] - m['t']) * V.SR)
            if keep < len(x):
                x = M.fade(x[:keep], 0, min(.6, (nxt[0] - m['t']) * .3))
        if m['fin'] or m['fout']:
            x = M.fade(x, m['fin'], m['fout'] if len(x) == len(m['arr']) else 0)
        g = m['gain']
        if m['rms']:
            g *= m['rms'] / (np.sqrt((x ** 2).mean()) + 1e-9)
        i = int(m['t'] * V.SR); j = min(n, i + len(x))
        if j > i:
            music[i:j] += x[:j - i] * g
    duck = np.ones(n)
    for l in ep.lines:
        i, j = int((l.start - .1) * V.SR), int((l.end + .1) * V.SR)
        duck[max(0, i):j] = np.minimum(duck[max(0, i):j], .55)
    from scipy.signal import lfilter
    a_ = math.exp(-2 * math.pi * 4 / V.SR)
    duck = lfilter([1 - a_], [1, -a_], duck)
    master = music * duck[:, None]
    for t, name, g in ep.sfx:
        x = M.sfx(name, seed=int(t * 100))
        i = int(t * V.SR); j = min(n, i + len(x))
        if j > i:
            master[i:j] += (x[:j - i] * g * .6)[:, None]
    for l in ep.lines:
        x = l.audio * 1.5
        i = int(l.start * V.SR); j = min(n, i + len(x))
        master[i:j] += x[:j - i, None]
        # censor bleeps over ■ portion: approximate position by character ratio
        if '■' in l.jp:
            idx = l.jp.index('■'); cnt = l.jp.count('■')
            s0 = l.start + l.dur * idx / max(1, len(l.jp)); s1 = s0 + l.dur * cnt / max(1, len(l.jp)) + .15
            b = M.sfx('bleep')[:int((s1 - s0) * V.SR)]
            i = int(s0 * V.SR); j = min(n, i + len(b))
            master[i:j, :] *= .15
            master[i:j] += (b[:j - i] * .9)[:, None]
    return master[:int(total * V.SR)]

def encode(ep, out, M, colors, start=0.0, end=None, threads=8):
    total = ep.t
    end = end or total
    os.makedirs(BUILD, exist_ok=True)
    wav = os.path.join(BUILD, 'mix2.wav')
    ass = os.path.join(BUILD, 'subs2.ass')
    print('mixing audio…', flush=True)
    a = build_audio(ep, total, M)
    M.write_wav(wav, a[int(start * V.SR):int(end * V.SR)])
    # shift subs if partial render
    if start:
        for l in ep.lines:
            l.start -= start; l.end -= start
        ep.sub_extra = [(s - start, e - start, x) for s, e, x in ep.sub_extra]
    write_ass(ep, ass, colors)
    if start:
        for l in ep.lines:
            l.start += start; l.end += start
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    clean = os.path.join(BUILD, 'clean_master.mkv')
    cmd = [ff, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '10', '-tune', 'animation', '-pix_fmt', 'yuv444p', clean]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nframes = int(round((end - start) * FPS))
    for i in range(nframes):
        T = start + i / FPS
        p.stdin.write(render_frame(ep, T).tobytes())
        if i % (FPS * 10) == 0:
            print(f'  {T:6.1f}s / {end:.1f}s', flush=True)
    p.stdin.close()
    p.wait()
    burn(clean, wav, ass, out)

def burn(clean, wav, ass, out):
    """Fast pass: upscale the clean master, burn fansub subtitles, add audio."""
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    vf = f"scale=1920:1080:flags=neighbor,subtitles={ass}:fontsdir={FONTS}"
    cmd = [ff, '-y', '-loglevel', 'error', '-i', clean, '-i', wav, '-vf', vf, '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
           '-tune', 'animation', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '256k', '-shortest', '-movflags', '+faststart', out]
    subprocess.run(cmd, check=True)
    print('wrote', out, flush=True)
