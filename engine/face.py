"""Anime expressions drawn at each ghoul's native pixel scale + full character compositor."""
import math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw
import skeleton as K

import os
import paths
SPR = paths.SPRITES

@lru_cache(None)
def head_sprite(name):
    return Image.open(os.path.join(SPR, name + '.png')).convert('RGBA')

# ---------------------------------------------------------------- neck detection
NECK_OVERRIDE = {'taras': 15, 'quin': 10, 'slaughter': 12}

@lru_cache(None)
def neck_info(name):
    """(x centre, width) of the neck that comes out of the bottom of the PFP skull."""
    a = np.asarray(head_sprite(name))
    h, w = a.shape[:2]
    if name in K.BUST:
        return w / 2, 0
    if name in NECK_OVERRIDE:
        return NECK_OVERRIDE[name], 3
    for y in range(h - 1, max(-1, h - 4), -1):
        xs = np.where(a[y, :, 3] > 0)[0]
        if len(xs):
            runs, s0, p = [], xs[0], xs[0]
            for x in xs[1:]:
                if x != p + 1:
                    runs.append((s0, p)); s0 = x
                p = x
            runs.append((s0, p))
            r = min(runs, key=lambda r: abs((r[0] + r[1]) / 2 - w / 2)) if len(runs) > 1 else runs[0]
            if r[1] - r[0] + 1 <= 8:
                return (r[0] + r[1] + 1) / 2, r[1] - r[0] + 1
    return w / 2, 3

# ---------------------------------------------------------------- tiny pixel marks (native scale)
def _ascii(rows, pal):
    h, w = len(rows), max(len(r) for r in rows)
    a = np.zeros((h, w, 4), np.uint8)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in pal:
                a[y, x] = pal[ch]
    return Image.fromarray(a)

MARK = {
    'sweat': _ascii([
        '..o..',
        '.oLo.',
        '.oLo.',
        'oLWLo',
        'oLLBo',
        'oLBBo',
        '.ooo.'], {'o': (30, 60, 120, 255), 'L': (150, 210, 255, 255), 'W': (255, 255, 255, 255), 'B': (90, 150, 230, 255)}),
    'anger': _ascii([
        '.RR.RR.',
        'RrR.RrR',
        'RR...RR',
        '.......',
        'RR...RR',
        'RrR.RrR',
        '.RR.RR.'], {'R': (230, 30, 50, 255), 'r': (255, 120, 120, 255)}),
    '!': _ascii([
        'oYYo',
        'oYYo',
        'oYYo',
        'oYYo',
        '.oo.',
        'oYYo',
        'oYYo'], {'o': (40, 20, 0, 255), 'Y': (255, 225, 60, 255)}),
    '?': _ascii([
        '.oBBo.',
        'oBo.Bo',
        '...oBo',
        '..oBo.',
        '..oBo.',
        '......',
        '..oBo.'], {'o': (10, 20, 60, 255), 'B': (90, 170, 255, 255)}),
    'note': _ascii([
        '..oo',
        '..oP',
        '..o.',
        'oPo.',
        'PPo.'], {'o': (40, 0, 40, 255), 'P': (255, 140, 220, 255)}),
    'heart': _ascii([
        '.oo.oo.',
        'oPPoPPo',
        'oPPPPPo',
        '.oPPPo.',
        '..oPo..',
        '...o...'], {'o': (90, 0, 30, 255), 'P': (255, 90, 140, 255)}),
    'steam': _ascii([
        '.WW..',
        'WWWW.',
        '.WWWW',
        '..WW.'], {'W': (240, 240, 240, 230)}),
    'spark': _ascii([
        '..W..',
        '..W..',
        'WWYWW',
        '..W..',
        '..W..'], {'W': (255, 255, 255, 255), 'Y': (255, 240, 120, 255)}),
}

# ---------------------------------------------------------------- expression overlays
DARK = (12, 6, 16, 255)

# From Ep03 the ghouls have no legs: the body ends at the hip and they levitate. Ep01/02 leave this False.
# opening_v2 / Ep03+ set `FC.FLOAT = True`; character() then drops the legs, adds a hover gap with a slow bob
# and a soft shadow, and `feet` becomes the shadow point on the ground, so every stand()/put() keeps working.
FLOAT = False
# props a ghoul always carries (held in the viewer-right hand). Ep03: Hammallama never goes anywhere without his GHOULIPS
# (director's icon assets/sprites/props/ghoulips.png — the icon is mandatory whenever the drink is shown).
PROPS = {'hammallama': 'ghoulips'}
@lru_cache(None)
def prop_sprite(kind):
    return Image.open(os.path.join(SPR, 'props', kind + '.png')).convert('RGBA')
HOVER = 9          # native px between hip and ground (scaled by face width)


def _bone_of(name):
    return K.BONE.get(name, (210, 210, 200))

def _px(d, x, y, c):
    d.point((x, y), fill=c)

def apply_expr(name, expr, mouth=0, t=0.0, look=0, blink=False):
    """Return RGBA head with expression + mouth. Native resolution."""
    base = head_sprite(name)
    meta = K.FACE[name]
    kind = meta['kind']
    eyes = meta['eyes']
    jaw = meta['jaw']
    im = base.copy()
    w, h = im.size
    alpha = np.asarray(base)[..., 3] > 0
    d = ImageDraw.Draw(im)
    bone = _bone_of(name)
    lid = tuple(int(c * 1.0) for c in bone) + (255,)
    lidsh = tuple(int(c * .7) for c in bone) + (255,)
    pupil_dx = look

    def on(x, y):
        return 0 <= x < w and 0 <= y < h and alpha[y, x]

    def brows(style):
        # style: 'angry' inner-down, 'worried' inner-up, 'flat'
        for i, (ex, ey) in enumerate(eyes):
            side = -1 if i == 0 else 1          # left eye, right eye
            by = ey - (3 if kind in ('glasses', 'visor') else 3)
            pts = [(ex - 2, by), (ex - 1, by), (ex, by), (ex + 1, by), (ex + 2, by)]
            for j, (x, y) in enumerate(pts):
                inner = (j >= 3) if side == -1 else (j <= 1)
                outer = (j <= 1) if side == -1 else (j >= 3)
                dy = 0
                if style == 'angry':
                    dy = 1 if inner else (-1 if outer else 0)
                elif style == 'worried':
                    dy = -1 if inner else (1 if outer else 0)
                if 0 <= x < w and 0 <= y + dy < h:
                    _px(d, x, y + dy, DARK)

    def shadow_upper(k=.55, color=(40, 0, 60)):
        a = np.asarray(im).astype(float)
        cut = max(eyes[0][1], eyes[1][1]) + 1
        rows = slice(0, cut)
        m = a[rows, :, 3] > 0
        sub = a[rows, :, :3]
        sub[m] = sub[m] * (1 - k) + np.array(color) * k
        a[rows, :, :3] = sub
        return Image.fromarray(a.astype(np.uint8))

    def gloom():
        cut = max(eyes[0][1], eyes[1][1]) - 1
        a = np.asarray(im).astype(float)
        for x in range(1, w, 2):
            for y in range(0, cut):
                if a[y, x, 3] > 0 and (x * 7 + y) % 9 < 7:
                    a[y, x, :3] = a[y, x, :3] * .45 + np.array((60, 80, 200)) * .55
        return Image.fromarray(a.astype(np.uint8))

    def fill_eye(ex, ey, col, r=1):
        for yy in range(ey - r, ey + r + 1):
            for xx in range(ex - r - (1 if kind in ('glasses', 'visor') else 0), ex + r + 1 + (1 if kind in ('glasses', 'visor') else 0)):
                if on(xx, yy):
                    _px(d, xx, yy, col)

    closed = blink and kind in ('eyes', 'plush', 'socket')

    if expr in ('shock', 'scared'):
        for ex, ey in eyes:
            if kind in ('glasses', 'visor'):
                fill_eye(ex, ey, (250, 250, 255, 255))
                _px(d, ex - 1, ey - 1, (190, 220, 255, 255))
            else:
                fill_eye(ex, ey, DARK)
                _px(d, ex, ey, (255, 255, 255, 255))
        im = gloom(); d = ImageDraw.Draw(im)
    elif expr == 'angry':
        for ex, ey in eyes:
            if kind in ('glasses', 'visor'):
                fill_eye(ex, ey, (255, 40, 40, 255))
                _px(d, ex, ey, (255, 220, 200, 255))
            else:
                fill_eye(ex, ey, DARK)
                _px(d, ex, ey, (255, 50, 40, 255))
        brows('angry')
    elif expr in ('happy', 'hype'):
        for ex, ey in eyes:
            col = (255, 255, 255, 255) if kind in ('glasses', 'visor') else lid
            if kind not in ('glasses', 'visor'):
                fill_eye(ex, ey, lidsh)
            for x, y in ((ex - 1, ey + 1 if False else ey), (ex, ey - 1), (ex + 1, ey)):
                pass
            # '^' shape
            for x, y in ((ex - 2, ey + 1), (ex - 1, ey), (ex, ey - 1), (ex + 1, ey), (ex + 2, ey + 1)):
                if on(x, y):
                    _px(d, x, y, DARK if kind not in ('glasses', 'visor') else col)
        # blush
        for ex, ey in eyes:
            for dx in (-1, 1):
                if on(ex + dx, ey + 2):
                    _px(d, ex + dx, ey + 2, (255, 120, 170, 255))
    elif expr == 'sparkle':
        for ex, ey in eyes:
            fill_eye(ex, ey, DARK)
            for x, y in ((ex, ey - 1), (ex - 1, ey), (ex, ey), (ex + 1, ey), (ex, ey + 1)):
                if on(x, y):
                    _px(d, x, y, (255, 245, 150, 255))
            _px(d, ex, ey, (255, 255, 255, 255))
    elif expr == 'worried':
        for ex, ey in eyes:
            if kind in ('glasses', 'visor'):
                pass
            else:
                fill_eye(ex, ey, DARK)
                _px(d, ex + pupil_dx, ey + 1, (230, 230, 255, 255))
        brows('worried')
    elif expr in ('serious', 'menace'):
        im = shadow_upper(.6 if expr == 'menace' else .4); d = ImageDraw.Draw(im)
        ex, ey = eyes[1]
        glint = (255, 60, 60, 255) if kind in ('socket', 'eyes') else (255, 255, 255, 255)
        if kind in ('glasses', 'visor'):
            for k in range(3):
                if on(ex - 1 + k, ey - 1 + k):
                    _px(d, ex - 1 + k, ey - 1 + k, (255, 255, 255, 255))
        else:
            for ex2, ey2 in eyes:
                _px(d, ex2, ey2, glint)
    elif expr == 'smug':
        for ex, ey in eyes:
            for x in range(ex - 2, ex + 3):
                if on(x, ey - 1):
                    _px(d, x, ey - 1, lid if kind not in ('glasses', 'visor') else DARK)
                if on(x, ey - 2) and kind in ('glasses', 'visor'):
                    pass
        brows('flat')
    elif expr == 'sad':
        brows('worried')
        for ex, ey in eyes:
            if kind not in ('glasses', 'visor'):
                fill_eye(ex, ey, DARK)
                _px(d, ex, ey, (200, 220, 255, 255))
            for k in range(3):
                if on(ex + 1, ey + 2 + k + int(t * 6) % 2):
                    _px(d, ex + 1, ey + 2 + k + int(t * 6) % 2, (120, 190, 255, 255))
    elif expr == 'sleep' or closed:
        for ex, ey in eyes:
            if kind in ('glasses', 'visor') and expr == 'sleep':
                fill_eye(ex, ey, (30, 30, 40, 255))
                continue
            if kind in ('glasses', 'visor'):
                continue
            fill_eye(ex, ey, lid)
            for x in range(ex - 2, ex + 3):
                if on(x, ey + (0 if abs(x - ex) < 2 else -1)):
                    _px(d, x, ey + (0 if abs(x - ex) < 2 else -1), DARK)
    elif expr == 'deadpan':
        for ex, ey in eyes:
            if kind in ('glasses', 'visor'):
                fill_eye(ex, ey, (20, 20, 24, 255))
            else:
                fill_eye(ex, ey, DARK)
            for x in range(ex - 2, ex + 3):
                if on(x, ey - 1):
                    _px(d, x, ey - 1, DARK)
    elif expr == 'evil':
        im = shadow_upper(.7, (20, 0, 30)); d = ImageDraw.Draw(im)
        for ex, ey in eyes:
            fill_eye(ex, ey, (20, 0, 20, 255) if kind not in ('glasses', 'visor') else (0, 220, 255, 255))
            _px(d, ex, ey, (255, 255, 255, 255))
    # mouth
    if mouth > 0:
        im = open_jaw(im, name, mouth)
    return im

def open_jaw(im, name, amount):
    meta = K.FACE[name]
    j = meta['jaw']
    w, h = im.size
    amount = int(amount)
    out = Image.new('RGBA', (w, h + amount), (0, 0, 0, 0))
    out.paste(im.crop((0, 0, w, j)), (0, 0))
    out.paste(im.crop((0, j, w, h)), (0, j + amount))
    a = np.asarray(im)
    row = a[j]
    xs = np.where(row[:, 3] > 0)[0]
    if len(xs):
        span = xs.max() - xs.min()
        x0, x1 = xs.min() + span // 4, xs.max() - span // 4
        dr = ImageDraw.Draw(out)
        dr.rectangle((x0, j, x1, j + amount - 1), fill=(40, 6, 14, 255))
        if amount >= 2:
            dr.line((x0 + 1, j + amount - 1, x1 - 1, j + amount - 1), fill=(150, 40, 60, 255))
    return out

# ---------------------------------------------------------------- full character
def character(name, pose='idle', expr='neutral', mouth=0, t=0.0, look=0, legs=True, blink=None, marks=(), bob=0, shadow=True):
    """Compose head + skeleton body at native scale.
    Returns (img, anchors) — anchors in image coords: feet, neck, head_top, temple, forehead, center."""
    if blink is None:
        ph = (t * 0.31 + len(name) * .17) % 1.0
        blink = ph < 0.04
    if FLOAT:
        legs = False
    head = apply_expr(name, expr, mouth, t, look, blink)
    meta = K.FACE[name]
    u = meta['face_w'] / 18
    K.HANDS.clear()
    body, (nx, ny) = K.body_image(name, pose, u, legs=legs)
    hands = dict(K.HANDS)
    if FLOAT and name in K.BUST:
        body = Image.new('RGBA', body.size, (0, 0, 0, 0))     # the PFP already ends at the waist
    bh = head_sprite(name)
    nkx, nkw = neck_info(name)
    half = max(nkx, bh.width - nkx)
    W_ = int(max(body.width, 2 * half + 16))
    top_pad = 10
    Hh = top_pad + bh.height - 3 + (body.height - ny)
    img = Image.new('RGBA', (W_, Hh + 4), (0, 0, 0, 0))
    cx = W_ // 2
    hx = int(round(cx - nkx))     # the PFP's own neck lines up with the spine
    hy = top_pad + bob
    bust = name in K.BUST
    neck = 0 if bust else max(3, round(3 * u))      # visible cervical vertebrae between skull and clavicles
    bx = cx - nx
    by = top_pad + bh.height + neck - ny - (3 if bust else 1)
    img = Image.new('RGBA', (W_, Hh + 4 + neck), (0, 0, 0, 0))
    _paste(img, body, bx, by)
    if neck:
        bone = K.BONE.get(name, (210, 210, 200))
        dark = tuple(int(c * .3) for c in bone) + (255,)
        hl = tuple(min(255, int(c * 1.15)) for c in bone) + (255,)
        sh = tuple(int(c * .7) for c in bone) + (255,)
        d = ImageDraw.Draw(img)
        y0, y1 = top_pad + bh.height - 4, by + ny + 1
        wv = int(max(2, min(5, nkw if nkw else round(2 * u))))
        d.rectangle((cx - wv // 2 - 1, y0, cx + (wv - wv // 2), y1), fill=dark)
        for yy in range(y0, y1 + 1):
            seg = (yy - y0) % 3
            col = dark if seg == 2 else (hl if seg == 0 else sh)
            d.line((cx - wv // 2, yy, cx + wv - wv // 2 - 1, yy), fill=col)
            if seg == 1:
                d.point((cx - wv // 2 - 1, yy), fill=sh); d.point((cx + wv - wv // 2, yy), fill=sh)
    _paste(img, head, hx, hy)
    if name in PROPS and 'ra' in hands:
        pr = prop_sprite(PROPS[name])
        px, py = hands['ra']
        _paste(img, pr, int(round(bx + px - pr.width / 2)), int(round(by + py - pr.height * .6)))
    # feet = lowest opaque row
    a = np.asarray(img)[..., 3]
    rows = np.where(a.max(1) > 0)[0]
    feet_y = rows.max() if len(rows) else img.height
    anchors = dict(
        feet=(cx, feet_y), neck=(cx, top_pad + bh.height - 3), head_top=(cx, hy),
        temple=(hx + bh.width - 2, hy + int(bh.height * .3)),
        forehead=(hx + int(bh.width * .72), hy + 2),
        center=(cx, hy + bh.height // 2),
        eyes=[(hx + ex, hy + ey) for ex, ey in meta['eyes']],
    )
    for m in marks:
        add_mark(img, anchors, m, t)
    if FLOAT:
        img, anchors = _levitate(img, anchors, name, u, t, shadow)
    return img, anchors

def _levitate(img, anchors, name, u, t, shadow):
    """Hip-cut body hovering over the ground: slow bob + soft shadow. `feet` = shadow centre on the ground."""
    gap = int(round(HOVER * u))
    amp = 1.6 * u
    ph = (t * .55 + len(name) * .37) % 1.0
    lift = int(round(amp * (1 - math.cos(ph * 2 * math.pi)) / 2))   # 0 .. amp, upward
    hip_y = anchors['feet'][1]
    H2 = hip_y + 1 + gap + 3
    out = Image.new('RGBA', (img.width, H2), (0, 0, 0, 0))
    gy = hip_y + 1 + gap                                            # ground row
    if shadow:
        sw = img.width * .34 * (1 - .12 * lift / max(1, amp))
        sh = Image.new('RGBA', out.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(sh)
        cx = anchors['feet'][0]
        d.ellipse((cx - sw, gy - 1.5, cx + sw, gy + 1.5), fill=(10, 4, 18, 90))
        d.ellipse((cx - sw * .6, gy - 1, cx + sw * .6, gy + 1), fill=(10, 4, 18, 110))
        out.alpha_composite(sh)
    _paste(out, img, 0, -lift)
    an = {}
    for k, v in anchors.items():
        if k == 'eyes':
            an[k] = [(x, y - lift) for x, y in v]
        elif k == 'feet':
            an[k] = (v[0], gy)
        else:
            an[k] = (v[0], v[1] - lift)
    an['hip'] = (anchors['feet'][0], hip_y - lift)
    return out, an

def _paste(dst, im, x, y):
    x0, y0 = max(0, -x), max(0, -y)
    x1, y1 = min(im.width, dst.width - x), min(im.height, dst.height - y)
    if x1 > x0 and y1 > y0:
        dst.alpha_composite(im.crop((x0, y0, x1, y1)), (x + x0, y + y0))

def add_mark(img, anchors, m, t):
    if m == 'sweat':
        x, y = anchors['temple']
        _paste(img, MARK['sweat'], x - 1, y - 2 + (int(t * 3) % 2))
    elif m == 'anger':
        x, y = anchors['forehead']
        k = 1 if int(t * 6) % 2 else 0
        _paste(img, MARK['anger'], x - 3 - k, y - 3 - k)
    elif m in ('!', '?'):
        x, y = anchors['head_top']
        hop = int(max(0, 1 - t * 5) * 4)
        _paste(img, MARK[m], x + 6, max(0, y - 9 - hop))
    elif m == 'steam':
        x, y = anchors['head_top']
        ph = int(t * 8) % 3
        _paste(img, MARK['steam'], x - 10 - ph, max(0, y - 2 - ph))
        _paste(img, MARK['steam'], x + 6 + ph, max(0, y - 2 - ph))
    elif m == 'note':
        x, y = anchors['head_top']
        _paste(img, MARK['note'], x + 8, max(0, y - 6 - int(t * 4) % 3))
    elif m == 'heart':
        x, y = anchors['head_top']
        _paste(img, MARK['heart'], x + 7, max(0, y - 7))
    elif m == 'sparkles':
        x, y = anchors['head_top']
        for i, (dx, dy) in enumerate(((-12, 4), (11, 0), (13, 14))):
            if (int(t * 6) + i) % 3:
                _paste(img, MARK['spark'], x + dx, max(0, y + dy))

def expr_sheet(path, names, exprs):
    rows = []
    cell = 70
    sh = Image.new('RGBA', (cell * len(exprs), cell * len(names)), (60, 50, 80, 255))
    for i, n in enumerate(names):
        for j, e in enumerate(exprs):
            marks = {'shock': ('!', 'sweat'), 'angry': ('anger',), 'worried': ('sweat',), 'happy': ('sparkles',), 'sleep': ()}.get(e, ())
            im, an = character(n, 'idle', e, mouth=2 if e in ('shock', 'angry') else 0, t=0.3, marks=marks, blink=False)
            im = im.crop((0, 0, im.width, min(im.height, cell)))
            sh.alpha_composite(im, (j * cell + (cell - im.width) // 2, i * cell))
    sh = sh.resize((sh.width * 3, sh.height * 3), Image.NEAREST)
    sh.save(path)
