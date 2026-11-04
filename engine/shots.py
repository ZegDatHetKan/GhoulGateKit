"""Reusable shot helpers + CLI shared by every GhoulGate episode script.

Episode scripts do `from shots import *` and define build() -> Ep.
"""
import os, sys, math, random, argparse
import numpy as np
from PIL import Image, ImageDraw
import paths
import render as E
from render import W, H, ease, ease_out, lerp, paste, iscale
import world as Wd
import face as FC
import skeleton as K
import music as M
import voice as V

COL = {
    'giulio': (255, 170, 210), 'colin': (150, 130, 255), 'luke': (255, 220, 60), 'noside': (255, 110, 170),
    'pondering': (170, 150, 255), 'taras': (250, 210, 90), 'chops': (255, 70, 70), 'elegy': (90, 210, 225),
    'errorgarden': (240, 120, 120), 'pedrox': (220, 220, 220), 'quin': (255, 230, 170), 'slaughter': (255, 90, 120),
    'uh': (130, 220, 120), 'jeff': (255, 140, 100), 'cheesus': (120, 230, 120), 'deepcode': (80, 230, 190), 'bb': (240, 130, 220),
    'hammallama': (255, 170, 90), 'bodacious': (255, 120, 60),
}
JPN = {'giulio': 'ジュリオ', 'colin': 'コリン', 'luke': 'ルーク', 'noside': 'ノーサイド', 'pondering': 'ポンダリング', 'taras': 'タラス',
       'chops': 'チョップス', 'elegy': 'エレジー', 'errorgarden': 'エラーガーデン', 'pedrox': 'ペドロックス', 'quin': 'クイン',
       'slaughter': 'スローターメロン軍曹', 'uh': 'アー', 'jeff': 'ジェフ', 'cheesus': 'チーザス', 'deepcode': 'ディープコード', 'bb': 'ビービー', 'hammallama': 'ハマラマ', 'bodacious': 'ボディシャス・パイレーツ'}
ENN = {'giulio': 'GIULIO', 'colin': 'COLIN', 'luke': 'LUKE', 'noside': 'NOSIDE', 'pondering': 'PONDERING', 'taras': 'TARAS',
       'chops': 'CHOPS', 'elegy': 'ELEGY', 'errorgarden': 'ERRORGARDEN', 'pedrox': 'PEDROX', 'quin': 'QUINCREDIBLE',
       'slaughter': 'SGT. SLAUGHTERMELON', 'uh': 'UH', 'jeff': 'JEFF', 'cheesus': 'CHEESUS', 'deepcode': 'DEEPCODE', 'bb': 'BB', 'hammallama': 'HAMMALLAMA', 'bodacious': 'BODACIOUS PIRATE'}

# ---------------------------------------------------------------- back view of a ghoul (for shots from behind)
_back_cache = {}
def back_char(name, pose='idle', t=0.0):
    key = (name, pose)
    head = FC.head_sprite(name)
    a = np.asarray(head).astype(int).copy()
    h, w = a.shape[:2]
    bc = np.array(K.BONE.get(name, (200, 200, 190)))
    alpha = a[..., 3] > 0
    for y in range(h):
        for x in range(w):
            if not alpha[y, x]:
                continue
            c = a[y, x, :3]
            if y < h * .38 and np.abs(c - bc).sum() > 150 and c.sum() > 90:
                continue
            a[y, x, :3] = np.clip(bc * (.78 + .2 * (1 - x / max(1, w - 1))), 0, 255)
    m = alpha
    edge = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
    a[edge, :3] = (a[edge, :3] * .4).astype(int)
    hb = Image.fromarray(a.astype(np.uint8))
    u = K.FACE[name]['face_w'] / 18
    body, (nx, ny) = K.body_image(name, pose, u)
    nkx, _ = FC.neck_info(name)
    half = max(nkx, w - nkx)
    img = Image.new('RGBA', (int(max(body.width, 2 * half + 10)), h + body.height - ny), (0, 0, 0, 0))
    cx = img.width // 2
    E.paste(img, body, cx - nx, h - 3 - ny)
    E.paste(img, hb, int(round(cx - nkx)), 0)
    return img

# ---------------------------------------------------------------- reusable shot pieces
def room(f, cam=(240, 135, 1.0), dof=0.0, focus=None, **kw):
    w, fl = E.crypt_world(f, focus=focus, **kw)
    return E.camera(w, *cam, focus_layer=fl, dof=dof)

def pan(f, a, b, t0=0.0, t1=None, fn=ease):
    t1 = f.d if t1 is None else t1
    k = fn((f.t - t0) / max(1e-6, t1 - t0))
    return tuple(lerp(a[i], b[i], k) for i in range(3))

def handheld(f, amp=1.2):
    return math.sin(f.T * 1.3) * amp, math.sin(f.T * 1.7 + 1) * amp * .6

def door_reverse(f, name='giulio', expr='neutral', pose=None, marks=(), scale=3, push=0.0):
    bg = Wd.door_side(f.T)
    bg = Wd.apply_light(bg, Wd.door_lights(f.T), .8)
    p = pose or E.talk_pose(f, name)
    ch, an = FC.character(name, p, expr, mouth=f.mouth(name), t=f.T, marks=marks)
    big = iscale(ch, scale)
    img = bg.copy()
    paste(img, big, W / 2 - big.width / 2, H - big.height + 12 * scale)
    if push:
        img = E.camera(img, W / 2, H * .42, 1 + push)
    return img

def console_close(f, who='giulio', presses=(), untaps=(), frenzy=0, frenzy_btn='dark', glow=1.0, hands=('giulio',), sweat=False, s=5, second_hand=None):
    """Close-up on the Dark Tap console with a bony hand pressing a button."""
    img = Wd.vgrad(W, H, [(0, (26, 14, 40)), (1, (8, 4, 14))])
    Wd.bricks(img, (0, 0, W, 170), (34, 24, 50), (14, 8, 20), seed=21, bw=40, bh=20, var=6)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 170, W, H), fill=(20, 12, 28, 255))
    dark = 0.0
    for tt in presses:
        if tt <= f.t < tt + .22:
            dark = 1 - abs(f.t - tt - .11) / .11
    un = 0.0
    for tt in untaps:
        if tt <= f.t < tt + .22:
            un = 1 - abs(f.t - tt - .11) / .11
    if frenzy:
        ph = (math.sin(f.t * frenzy) + 1) / 2
        if frenzy_btn == 'dark':
            dark = ph
        else:
            un = ph
    (bx, by), (ux, uy) = Wd.console(img, W // 2 - 20, H + 60, f.T, dark, un, glow, s)
    L = np.zeros((H, W, 3), np.float32)
    Wd.glow(L, bx, by, 160, (180, 60, 255), .9 * glow * (.8 + .2 * math.sin(f.T * 3)))
    img = Wd.apply_light(img, L, .85)
    # hand over the pressed button
    tgt = (bx, by) if frenzy_btn == 'dark' or presses else (ux, uy)
    if untaps and not presses:
        tgt = (ux, uy)
    hover = 0
    if not frenzy and not presses and not untaps:
        hover = 20 + math.sin(f.t * 2) * 3
    lift = 0
    if frenzy:
        lift = (1 - (dark if frenzy_btn == 'dark' else un)) * 22
    else:
        nxt = [tt for tt in list(presses) + list(untaps) if tt >= f.t]
        prv = [tt for tt in list(presses) + list(untaps) if tt < f.t]
        if nxt:
            lift = min(26, (nxt[0] - f.t) * 60)
        elif prv:
            lift = min(26, (f.t - prv[-1] - .2) * 40) if f.t - prv[-1] > .2 else 0
    hand(img, tgt[0], tgt[1] - hover - lift - 2, hands[0], 4)
    if second_hand:
        n2, (sx_, sy_) = second_hand
        hand(img, sx_, sy_, n2, 4, from_='bl')
    if sweat:
        paste(img, iscale(FC.MARK['sweat'], 4), tgt[0] + 40, tgt[1] - 110)
    return img

def hand(img, x, y, name, s=5, from_='br'):
    """Pixel skeleton hand pressing down at (x,y) (fingertips), drawn at native res then scaled x s."""
    bone = K.BONE.get(name, (210, 210, 200))
    sleeve = K.CLOTHES[name][1] if name in K.CLOTHES else None
    if name in K.BUST:
        sleeve = {'jeff': (205, 60, 60), 'cheesus': (200, 192, 175)}[name]
    dark = tuple(int(c * .35) for c in bone)
    hi = tuple(min(255, int(c * 1.18)) for c in bone)
    w, h = 44, 64
    m = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(m)
    sx = 1 if from_ != 'bl' else -1
    # forearm: radius + ulna (or sleeve) coming from lower right, off-canvas
    ex, ey = 22 + sx * 24, -4
    wx, wy = 22, 30
    if sleeve:
        d.line((ex, ey, wx, wy + 2), fill=tuple(sleeve) + (255,), width=9)
    else:
        for o in (-2, 2):
            d.line((ex + o, ey, wx + o, wy + 2), fill=dark + (255,), width=4)
        for o in (-2, 2):
            d.line((ex + o, ey, wx + o, wy + 2), fill=bone + (255,), width=2)
    # carpals / palm
    d.rounded_rectangle((wx - 6, wy - 8, wx + 6, wy + 2), 3, fill=bone + (255,), outline=dark + (255,))
    d.line((wx - 4, wy - 7, wx + 3, wy - 7), fill=hi + (255,))
    # four fingers pointing down to the tips + thumb
    for i, fx in enumerate((wx - 5, wx - 2, wx + 1, wx + 4)):
        ln = (7, 9, 9, 7)[i]
        d.line((fx, wy + 2, fx, wy + 2 + ln), fill=dark + (255,), width=3)
        d.line((fx, wy + 2, fx, wy + 1 + ln), fill=bone + (255,), width=1)
        d.point((fx, wy + 2 + ln // 2), fill=dark + (255,))
    d.line((wx - 7 * sx, wy - 2, wx - 10 * sx, wy + 5), fill=dark + (255,), width=3)
    d.line((wx - 7 * sx, wy - 2, wx - 10 * sx, wy + 4), fill=bone + (255,), width=1)
    big = m.resize((w * s, h * s), Image.NEAREST)
    # fingertips (row wy+11) land at (x,y)
    E.paste(img, big, x - wx * s, y - (wy + 11) * s)

def basement_shot(f, door=0.0, runner=None, inside=None, slam_t=None):
    L, swing, fl = Wd.basement_lights(f.T, door)
    img = Wd.basement(f.T, door, inside)
    img = Wd.apply_light(img, L, .65)
    Wd.bulb(img, f.T, swing, fl)
    if runner is not None:
        k, pose_ph = runner
        bimg = back_char('giulio', 'run_a' if pose_ph else 'run_b')
        sc = lerp(5.0, 1.15, k)
        big = bimg.resize((int(bimg.width * sc), int(bimg.height * sc)), Image.NEAREST)
        foot = lerp(H + 120, 198, k)
        bobv = abs(math.sin(f.t * 18)) * 4 * sc / 2
        paste(img, big, 236 - big.width / 2, foot - big.height - bobv)
    return img


# ======================================================================= placement
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


# ======================================================================= small FX
def puff(img, x, y, k, color=(225, 225, 235)):
    if k <= 0:
        return
    d = ImageDraw.Draw(img)
    for dx, dy, r in ((0, 0, 12), (-14, 4, 9), (14, 3, 10), (-6, -10, 9), (8, -9, 8), (22, -2, 6), (-22, -1, 6)):
        rr = r * k
        d.ellipse((x + dx * k - rr - 1, y + dy * k - rr - 1, x + dx * k + rr + 1, y + dy * k + rr + 1), fill=(120, 120, 140, 200))
    for dx, dy, r in ((0, 0, 12), (-14, 4, 9), (14, 3, 10), (-6, -10, 9), (8, -9, 8), (22, -2, 6), (-22, -1, 6)):
        rr = r * k
        d.ellipse((x + dx * k - rr, y + dy * k - rr, x + dx * k + rr, y + dy * k + rr), fill=color + (220,))

def smoke_curl(img, x, y, t):
    d = ImageDraw.Draw(img)
    for i in range(14):
        ph = (t * .3 + i / 14) % 1
        xx = x + math.sin(ph * 9 + t) * 10 * ph
        yy = y - ph * 110
        r = 2 + ph * 5
        d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(170, 180, 200, int(150 * (1 - ph))))

def snot(img, x, y, t, s=3):
    k = (math.sin(t * 2.2) + 1) / 2
    r = (1 + k * 4) * s
    d = ImageDraw.Draw(img)
    d.ellipse((x, y - r, x + 2 * r, y + r), fill=(150, 210, 255, 120), outline=(190, 230, 255, 255))
    d.ellipse((x + r * .4, y - r * .6, x + r * .8, y - r * .2), fill=(255, 255, 255, 255))


# ======================================================================= command line (shared by all episodes)
def export_script(ep, path, title):
    """Write a human-readable script (shot list + every voiced line) for the bible/episode folder."""
    def ts(t):
        return f'{int(t // 60)}:{t % 60:05.2f}'
    out = [f'# {title}', '', f'Runtime: {ts(ep.t)} — {len(ep.shots)} shots, {len(ep.lines)} voiced lines', '',
           '| Time | Shot | Speaker | Emotion | Japanese | English |', '|---|---|---|---|---|---|']
    for s, d, fn, ls in ep.shots:
        name = getattr(fn, '__name__', '?')
        if not ls:
            out.append(f'| {ts(s)} | `{name}` ({d:.1f}s) | | | | |')
        for l in ls:
            out.append(f'| {ts(l.start)} | `{name}` | {JPN.get(l.who, l.who)} / {ENN.get(l.who, l.who)} | {l.emo} | {l.jp} | {l.en} |')
    open(path, 'w', encoding='utf-8').write('\n'.join(out) + '\n')

def cli(build, out_default, build_dir, title='GhoulGate'):
    E.BUILD = build_dir
    os.makedirs(build_dir, exist_ok=True)
    ap = argparse.ArgumentParser(description=title)
    ap.add_argument('--info', action='store_true', help='print the shot list and runtime')
    ap.add_argument('--stills', default='', help='comma separated times (s) to render as PNG into build/stills')
    ap.add_argument('--subs-only', action='store_true', help='re-burn subtitles onto the existing clean master (~5 min)')
    ap.add_argument('--export-script', default='', help='write the shot list + dialogue as markdown')
    ap.add_argument('--start', type=float, default=0)
    ap.add_argument('--end', type=float, default=None)
    ap.add_argument('--out', default=out_default)
    a = ap.parse_args()
    ep = build()
    if a.info:
        print(f'total {ep.t:.1f}s = {int(ep.t // 60)}:{ep.t % 60:04.1f}  lines={len(ep.lines)}')
        for s, d, fn, ls in ep.shots:
            print(f'{s:7.2f} {d:5.2f} {getattr(fn, "__name__", "?")}' + ('  ' + ' / '.join(l.who for l in ls) if ls else ''))
        return
    if a.export_script:
        export_script(ep, a.export_script, title)
        print('wrote', a.export_script)
        return
    if a.stills:
        sd = os.path.join(build_dir, 'stills')
        os.makedirs(sd, exist_ok=True)
        for tok in a.stills.split(','):
            T = float(tok)
            E.render_frame(ep, T).save(os.path.join(sd, f'{T:07.2f}.png'))
        print('stills in', sd)
        return
    if a.subs_only:
        ass = os.path.join(build_dir, 'subs2.ass')
        E.write_ass(ep, ass, COL)
        E.burn(os.path.join(build_dir, 'clean_master.mkv'), os.path.join(build_dir, 'mix2.wav'), ass, a.out)
        return
    E.encode(ep, a.out, M, COL, a.start, a.end)
