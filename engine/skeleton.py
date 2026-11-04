"""Proper pixel skeleton bodies with posable joints, outline and shading."""
import math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw

# bone base colours (sampled from each PFP skull)
BONE = {
    'giulio': (104, 134, 92), 'taras': (112, 160, 72), 'uh': (92, 130, 84), 'noside': (110, 150, 100),
    'chops': (205, 205, 196), 'pedrox': (205, 205, 205), 'quin': (232, 228, 214), 'slaughter': (225, 225, 225),
    'jeff': (150, 100, 60), 'cheesus': (70, 170, 60), 'colin': (130, 112, 210), 'pondering': (130, 112, 210),
    'errorgarden': (176, 82, 82), 'elegy': (64, 172, 186), 'luke': (196, 172, 30), 'deepcode': (92, 92, 96),
    'bb': (200, 200, 190),
    'hammallama': (79, 126, 79),        # Ep03
    'bodacious': (128, 98, 150),        # Ep03 — Bodacious Pirate
}
BUST = {'jeff', 'cheesus'}   # PFP already includes torso + arms
# clothed characters: (torso colour, sleeve colour, legs colour)
CLOTHES = {
    'jeff': ((205, 60, 60), (205, 60, 60), (150, 100, 60)),
    'cheesus': ((200, 192, 175), (200, 192, 175), (70, 170, 60)),
    'slaughter': ((44, 44, 50), (44, 44, 50), (60, 60, 66)),
}

def shade(c, k):
    return tuple(int(max(0, min(255, v * k))) for v in c)

# poses: angles in degrees, 0 = straight down, positive = outward (away from body)
# arm: (shoulder, elbow) ; leg: (hip, knee)
POSES = {
    'idle':    dict(la=(12, -6), ra=(12, -6), ll=(4, 0), rl=(4, 0)),
    'relaxed': dict(la=(18, -30), ra=(8, 0), ll=(6, 0), rl=(2, 0)),
    'talk_a':  dict(la=(14, -8), ra=(60, -70), ll=(4, 0), rl=(4, 0)),
    'talk_b':  dict(la=(14, -8), ra=(45, -95), ll=(4, 0), rl=(4, 0)),
    'shrug':   dict(la=(70, -110), ra=(70, -110), ll=(4, 0), rl=(4, 0)),
    'cheer':   dict(la=(160, 10), ra=(160, 10), ll=(10, 0), rl=(10, 0)),
    'shock':   dict(la=(120, 40), ra=(120, 40), ll=(14, 0), rl=(14, 0)),
    'point':   dict(la=(12, -6), ra=(95, 0), ll=(4, 0), rl=(4, 0)),
    'fist':    dict(la=(12, -6), ra=(150, -150), ll=(6, 0), rl=(6, 0)),
    'press':   dict(la=(12, -6), ra=(80, -40), ll=(4, 0), rl=(4, 0)),
    'press2':  dict(la=(80, -40), ra=(80, -40), ll=(6, 0), rl=(6, 0)),
    'crossed': dict(la=(25, -125), ra=(25, -125), ll=(4, 0), rl=(4, 0)),
    'facepalm': dict(la=(12, -6), ra=(40, -150), ll=(4, 0), rl=(4, 0)),
    'slump':   dict(la=(4, 0), ra=(4, 0), ll=(2, 0), rl=(2, 0)),
    'run_a':   dict(la=(-40, -60), ra=(45, -70), ll=(-35, 40), rl=(30, -10)),
    'run_b':   dict(la=(45, -70), ra=(-40, -60), ll=(30, -10), rl=(-35, 40)),
    'tiptoe_a': dict(la=(50, -100), ra=(30, -60), ll=(-15, 25), rl=(15, -5)),
    'tiptoe_b': dict(la=(30, -60), ra=(50, -100), ll=(15, -5), rl=(-15, 25)),
    'table':   dict(la=(30, -80), ra=(30, -80), ll=(4, 0), rl=(4, 0)),   # forearms resting forward
    'hold_cards': dict(la=(35, -110), ra=(35, -110), ll=(4, 0), rl=(4, 0)),
    'smoke':   dict(la=(12, -6), ra=(30, -150), ll=(4, 0), rl=(4, 0)),
    'thumb':   dict(la=(12, -6), ra=(70, -100), ll=(4, 0), rl=(4, 0)),
    'hero':    dict(la=(20, -20), ra=(150, -150), ll=(14, 0), rl=(14, 0)),
}

def lerp_pose(a, b, k):
    pa, pb = POSES[a] if isinstance(a, str) else a, POSES[b] if isinstance(b, str) else b
    return {j: tuple(pa[j][i] * (1 - k) + pb[j][i] * k for i in range(2)) for j in pa}

def _limb(d, x, y, a1, a2, l1, l2, side, w):
    """Two-segment limb from (x,y). side=-1 left, +1 right (screen). returns joints."""
    ang1 = math.radians(a1) * side
    ex, ey = x + math.sin(ang1) * l1, y + math.cos(ang1) * l1
    ang2 = ang1 + math.radians(a2) * side
    hx, hy = ex + math.sin(ang2) * l2, ey + math.cos(ang2) * l2
    return (x, y), (ex, ey), (hx, hy), ang2

HANDS = {}      # filled by body_image: {'la': (x, y), 'ra': (x, y)} hand centres of the last body drawn (body-image coords)

def body_image(name, pose='idle', u=1.0, legs=True, clothes=None):
    """Return (RGBA image, neck_xy) of the skeleton body at native pixel scale."""
    p = POSES[pose] if isinstance(pose, str) else pose
    bone = BONE.get(name, (210, 210, 200))
    cl = CLOTHES.get(name) if clothes is None else clothes
    S = 1
    Wd, Ht = int(70 * u), int(70 * u)
    cx, cy = Wd // 2, int(22 * u)          # neck base inside canvas (room above for raised arms)
    mask = Image.new('L', (Wd, Ht), 0)      # 0 empty, 1 interior dark, 2 bone, 3 cloth, 4 sleeve, 5 leg cloth
    d = ImageDraw.Draw(mask)
    U = lambda v: v * u
    torso_h = U(19)
    sh_w = U(9.5)
    hip_y = cy + torso_h + U(3)
    if name in BUST:
        hip_y = cy + U(2)
    # ---- legs first (behind pelvis)
    if legs:
        for side, key in ((-1, 'll'), (1, 'rl')):
            a1, a2 = p[key]
            (x0, y0), (kx, ky), (fx, fy), ang = _limb(d, cx + side * U(3.5), hip_y + U(1), a1, a2, U(9), U(9), side, 2)
            lw = max(2, round(U(2)))
            col = 5 if cl else 2
            d.line((x0, y0, kx, ky), fill=col, width=lw)
            d.line((kx, ky, fx, fy), fill=col, width=lw)
            d.ellipse((kx - U(1.4), ky - U(1.4), kx + U(1.4), ky + U(1.4)), fill=col)
            # foot (bone) pointing outward-forward
            d.line((fx, fy, fx + side * U(3), fy + U(.3)), fill=2, width=max(2, round(U(1.6))))
    bust = name in BUST
    if bust:
        # PFP already shows the torso: only legs (and a pelvis-coloured waist) below
        m = np.zeros((Ht, Wd), np.uint8)
    # ---- torso
    if bust:
        pass
    elif cl:
        d.polygon([(cx - sh_w - U(1), cy + U(1)), (cx + sh_w + U(1), cy + U(1)), (cx + U(8), hip_y + U(1)), (cx - U(8), hip_y + U(1))], fill=3)
        d.line((cx, cy + U(2), cx, hip_y), fill=1, width=1)
    else:
        # ribcage interior
        d.ellipse((cx - U(8), cy + U(2), cx + U(8), cy + U(15)), fill=1)
        # spine
        d.line((cx, cy, cx, hip_y), fill=2, width=max(2, round(U(2))))
        # sternum
        d.line((cx, cy + U(2), cx, cy + U(10)), fill=2, width=max(2, round(U(2.2))))
        # ribs: 4 pairs, each arcs out and down from sternum
        for i in range(4):
            y = cy + U(3 + i * 3.1)
            w = U(8.2 - i * .9)
            for side in (-1, 1):
                pts = [(cx, y), (cx + side * w * .55, y - U(.6)), (cx + side * w, y + U(1.2)), (cx + side * w * .92, y + U(2.4))]
                d.line(pts, fill=2, width=1)
        # pelvis
        py = hip_y - U(2)
        d.polygon([(cx - U(7), py), (cx - U(2), py - U(1)), (cx, py + U(1.5)), (cx + U(2), py - U(1)), (cx + U(7), py),
                   (cx + U(5), py + U(4.5)), (cx + U(1.5), py + U(5)), (cx, py + U(3.5)), (cx - U(1.5), py + U(5)), (cx - U(5), py + U(4.5))], fill=2)
        d.ellipse((cx - U(4.5), py + U(1), cx - U(2), py + U(3)), fill=1)
        d.ellipse((cx + U(2), py + U(1), cx + U(4.5), py + U(3)), fill=1)
    if bust:
        d.rounded_rectangle((cx - U(6), cy - U(2), cx + U(6), hip_y + U(3)), 2, fill=5)
    # clavicles
    if not bust:
      d.line((cx - sh_w, cy + U(1.5), cx - U(1), cy + U(.5)), fill=2 if not cl else 3, width=max(1, round(U(1.5))))
      d.line((cx + sh_w, cy + U(1.5), cx + U(1), cy + U(.5)), fill=2 if not cl else 3, width=max(1, round(U(1.5))))
    # ---- arms (in front)
    for side, key in (() if bust else ((-1, 'la'), (1, 'ra'))):
        a1, a2 = p[key]
        (x0, y0), (ex, ey), (hx, hy), ang = _limb(d, cx + side * sh_w, cy + U(2), a1, a2, U(8), U(7.5), side, 2)
        aw = max(2, round(U(2)))
        col = 4 if cl else 2
        d.ellipse((x0 - U(1.6), y0 - U(1.6), x0 + U(1.6), y0 + U(1.6)), fill=col)
        d.line((x0, y0, ex, ey), fill=col, width=aw)
        d.line((ex, ey, hx, hy), fill=col, width=aw)
        d.ellipse((ex - U(1.2), ey - U(1.2), ex + U(1.2), ey + U(1.2)), fill=col)
        HANDS[key] = (hx, hy)
        # hand + three fingers
        hr = U(1.5)
        d.ellipse((hx - hr, hy - hr, hx + hr, hy + hr), fill=2)
        for f in (-1, 0, 1):
            fa = ang + f * .45 * side
            d.line((hx, hy, hx + math.sin(fa) * U(2.6), hy + math.cos(fa) * U(2.6)), fill=2, width=1)
    m = np.asarray(mask)
    out = np.zeros((Ht, Wd, 4), np.uint8)
    base = np.array(bone)
    pal = {1: shade(bone, .22), 2: bone}
    if cl:
        pal[3] = cl[0]; pal[4] = cl[1]; pal[5] = cl[2]
    for k, c in pal.items():
        sel = m == k
        out[sel, :3] = c
        out[sel, 3] = 255
    solid = m >= 2
    # shading: light from upper-left
    up = np.roll(solid, 1, 0); left = np.roll(solid, 1, 1)
    dn = np.roll(solid, -1, 0); rt = np.roll(solid, -1, 1)
    hl = solid & (~up | ~left)
    sh = solid & (~dn | ~rt)
    for k in (2, 3, 4, 5):
        if k not in pal:
            continue
        sel = (m == k)
        out[sel & hl, :3] = shade(pal[k], 1.18)
        out[sel & sh & ~hl, :3] = shade(pal[k], .68)
    # outline around everything opaque
    any_ = m > 0
    grow = any_ | np.roll(any_, 1, 0) | np.roll(any_, -1, 0) | np.roll(any_, 1, 1) | np.roll(any_, -1, 1)
    edge = grow & ~any_
    out[edge, :3] = shade(bone if not cl else cl[0], .18)
    out[edge, 3] = 255
    return Image.fromarray(out), (cx, cy)

# ---------------------------------------------------------------- face metadata
# eyes: native sprite coords of eye centres; kind: socket|eyes|glasses|visor|plush
# jaw: row where the jaw splits for talking; head box used for marks
FACE = {
    'giulio':      dict(eyes=[(8, 14), (14, 14)], kind='glasses', jaw=20, face_w=18),
    'colin':       dict(eyes=[(6, 14), (13, 14)], kind='visor', jaw=21, face_w=16),
    'luke':        dict(eyes=[(13, 22), (21, 22)], kind='socket', jaw=28, face_w=20),
    'noside':      dict(eyes=[(11, 12), (18, 12)], kind='eyes', jaw=19, face_w=20),
    'pondering':   dict(eyes=[(5, 10), (13, 10)], kind='socket', jaw=17, face_w=17),
    'taras':       dict(eyes=[(11, 15), (18, 15)], kind='socket', jaw=22, face_w=18),
    'chops':       dict(eyes=[(7, 13), (14, 13)], kind='socket', jaw=20, face_w=17),
    'elegy':       dict(eyes=[(9, 15), (16, 15)], kind='eyes', jaw=22, face_w=18),
    'errorgarden': dict(eyes=[(9, 10), (16, 10)], kind='eyes', jaw=16, face_w=18),
    'pedrox':      dict(eyes=[(10, 10), (15, 10)], kind='visor', jaw=15, face_w=17),
    'quin':        dict(eyes=[(11, 23), (18, 23)], kind='socket', jaw=27, face_w=20),
    'slaughter':   dict(eyes=[(10, 16), (19, 16)], kind='glasses', jaw=21, face_w=20),
    'uh':          dict(eyes=[(8, 13), (15, 13)], kind='glasses', jaw=19, face_w=17),
    'jeff':        dict(eyes=[(15, 13), (21, 13)], kind='plush', jaw=17, face_w=26),
    'cheesus':     dict(eyes=[(12, 12), (20, 12)], kind='plush', jaw=17, face_w=22),
    'deepcode':    dict(eyes=[(7, 10), (13, 10)], kind='socket', jaw=15, face_w=17),
    'bb':          dict(eyes=[(8, 10), (14, 10)], kind='visor', jaw=15, face_w=17),
    'hammallama':  dict(eyes=[(7, 10), (14, 10)], kind='socket', jaw=17, face_w=18),       # Ep03
    'bodacious':   dict(eyes=[(8, 14), (16, 14)], kind='glasses', jaw=20, face_w=18),      # Ep03 — mirrored sunset shades
}
