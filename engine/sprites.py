"""Turn the Based Ghoul PFPs into transparent native-res pixel sprites."""
import os, glob
import numpy as np
from PIL import Image
from grid import native
from cutout import flood, to_rgba

import paths
OUT = paths.SPRITES

def edge_seeds(H, W, bottom=False):
    s = [(y, x) for y in range(H) for x in (0, W - 1)] + [(0, x) for x in range(W)]
    if bottom:
        s += [(H - 1, x) for x in range(W)]
    return s

def components(mask):
    H, W = mask.shape
    lab = np.zeros((H, W), int); n = 0
    for y in range(H):
        for x in range(W):
            if mask[y, x] and not lab[y, x]:
                n += 1; st = [(y, x)]; lab[y, x] = n
                while st:
                    cy, cx = st.pop()
                    for dy, dx in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                        ny, nx = cy+dy, cx+dx
                        if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not lab[ny, nx]:
                            lab[ny, nx] = n; st.append((ny, nx))
    return lab, n

def keep_largest(fg, k=1, min_size=0):
    lab, n = components(fg)
    sizes = sorted(((lab == i).sum(), i) for i in range(1, n + 1))[::-1]
    keep = np.zeros_like(fg)
    for s, i in sizes[:k]:
        if s >= min_size:
            keep |= lab == i
    return keep

def simple(path, tol=30):
    arr, _, _ = native(path)
    H, W, _ = arr.shape
    bg = flood(arr, tol=tol, seeds=edge_seeds(H, W))
    fg = keep_largest(~bg, k=3, min_size=4)
    return arr, fg

def chops(path):
    """Skull filled row by row (keeps sockets/teeth, drops the checkerboard), brown hair, and the one-eyed critter incl. its eye."""
    arr, _, _ = native(path)
    a = arr.astype(int); H, W, _ = a.shape
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = a.sum(2); sat = a.max(2) - a.min(2)
    yy, xx = np.mgrid[:H, :W]
    fg = np.zeros((H, W), bool)
    grey = (sat < 45) & (lum > 240) & (lum < 700) & (xx >= 6) & (xx <= 23) & (yy >= 11)
    grey &= ~((yy >= 20) & ((xx < 8) | (xx > 20)))            # lower rows: the checkerboard starts right next to the jaw
    for y in range(11, H):                                   # skull: span between leftmost and rightmost grey pixel
        xs = np.where(grey[y])[0]
        if len(xs) >= 2:
            fg[y, xs.min():xs.max() + 1] = True
    hair = (r > g) & (g > b) & (lum < 260) & (r < 140) & (xx >= 7) & (xx <= 16) & (yy >= 5) & (yy <= 14)
    fg |= hair
    critter = (xx >= 15) & (xx <= 23) & (yy >= 3) & (yy <= 13)
    frog = critter & (g > 95) & (r > 75) & (g >= r) & (g > b + 20)
    eye = critter & (xx >= 16) & (xx <= 20) & (yy >= 6) & (yy <= 8) & ((lum > 600) | (lum < 90))
    fg |= frog | eye
    return arr, keep_largest(fg, k=3, min_size=2)

def quin(path):
    arr, _, _ = native(path)
    arr = arr[1:37, 5:33]
    a = arr.astype(int); H, W, _ = a.shape
    bg = flood(arr, tol=45, seeds=edge_seeds(H, W), local=False)
    # protect the face interior from the black flood (mouth / eye sockets)
    yy, xx = np.mgrid[:H, :W]
    face = ((yy - 22) / 10.5) ** 2 + ((xx - 15) / 8.0) ** 2 <= 1
    jaw = (yy >= 26) & (xx >= 7) & (xx <= 18)
    lum = a.sum(2)
    bg &= ~(face & (lum > 0))
    fg = ~bg
    fg = keep_largest(fg, k=1)
    # restore 1px black outline around the figure
    out = fg.copy()
    for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
        out |= np.roll(np.roll(fg, dy, 0), dx, 1)
    arr = arr.copy(); arr[out & ~fg] = (8, 8, 8)
    return arr, out

def luke(path):
    arr, _, _ = native(path)
    a = arr.astype(int); H, W, _ = a.shape
    lum = a.sum(2)
    mx, mn = a.max(2), a.min(2)
    sat = mx - mn
    black = lum < 70
    red = (a[..., 0] > 150) & (a[..., 1] < 90)
    yellow = (a[..., 0] > 90) & (a[..., 1] > 70) & (a[..., 2] < 60)
    fg = black | red | yellow
    yy, xx = np.mgrid[:H, :W]
    # photo shadows at the bottom are dark but not pure black
    fg &= ~((yy > 23) & ~((xx >= 10) & (xx <= 28)))
    fg = keep_largest(fg, k=2, min_size=20)
    return arr, fg

def taras(path):
    arr, _, _ = native(path)
    H, W, _ = arr.shape
    bg = flood(arr, tol=60, seeds=edge_seeds(H, W))
    fg = keep_largest(~bg, k=1)
    return arr, fg

def hires_cut(im, tol=60, bottom=False):
    """Background mask at full res: pixels near a border colour and connected to the border."""
    from scipy import ndimage
    a = np.asarray(im.convert('RGB')).astype(int)
    H, W, _ = a.shape
    border = np.concatenate([a[0], a[:, 0], a[:, -1]] + ([a[-1]] if bottom else []))
    # cluster border colours coarsely
    keys = {}
    for c in border[::3]:
        k = tuple((c // 32))
        keys.setdefault(k, []).append(c)
    tot = sum(len(v) for v in keys.values())
    ranked = sorted(keys.values(), key=len, reverse=True)
    refs = [np.mean(v, 0) for i, v in enumerate(ranked) if i == 0 or len(v) > .25 * tot]
    near = np.zeros((H, W), bool)
    for r in refs:
        near |= np.abs(a - r).sum(2) < tol
    lab, n = ndimage.label(near)
    edge_labels = set(np.unique(np.concatenate([lab[0], lab[:, 0], lab[:, -1]] + ([lab[-1]] if bottom else [])))) - {0}
    bg = np.isin(lab, list(edge_labels))
    fg = ~bg
    fg = ndimage.binary_opening(fg, iterations=2)
    lab, n = ndimage.label(fg)
    if n:
        sizes = ndimage.sum(fg, lab, range(1, n + 1))
        keep = [i + 1 for i, sz in enumerate(sizes) if sz >= max(sizes.max() * .15, fg.size * .01)]
        fg = np.isin(lab, keep)
    fg = ndimage.binary_fill_holes(fg)
    return fg

def pixelate(im, fg, n, colors):
    W, H = im.size
    s = n / max(W, H)
    size = (max(1, round(W * s)), max(1, round(H * s)))
    small = im.convert('RGB').resize(size, Image.BOX)
    small = small.quantize(colors, method=Image.Quantize.MEDIANCUT).convert('RGB')
    al = Image.fromarray((fg * 255).astype(np.uint8)).resize(size, Image.BOX)
    arr = np.asarray(small).copy()
    return arr, np.asarray(al) > 110

def flat_plush(path, n=40, colors=20):
    im = Image.open(path).convert('RGB')
    small = im.resize((n, n), Image.BOX)
    small = small.quantize(colors, method=Image.Quantize.MEDIANCUT).convert('RGB')
    arr = np.asarray(small).copy()
    H, W, _ = arr.shape
    bg = flood(arr, tol=60, seeds=edge_seeds(H, W))
    return arr, keep_largest(~bg, k=1)

def plush(path, n=40, colors=20):
    """Non-pixel PFPs (Jeff, Cheesus) get pixelated to sit with the others."""
    im = Image.open(path).convert('RGB')
    fg = hires_cut(im, tol=70)
    return pixelate(im, fg, n, colors)

def bb(path):
    arr, fg = simple(path)
    a = arr.astype(int); H, W, _ = a.shape
    yy, xx = np.mgrid[:H, :W]
    cy, cx = H * .52, W * .5
    inside = ((yy - cy) / (H * .47)) ** 2 + ((xx - cx) / (W * .36)) ** 2 <= 1
    sat = a.max(2) - a.min(2)
    smoke = (sat < 30) & (a.sum(2) < 480)
    fg &= inside | ~smoke
    fg &= ~(smoke & ~inside)
    return arr, keep_largest(fg, k=1)

def deepcode(path):
    arr, fg = simple(path)
    a = arr.astype(int); H, W, _ = a.shape
    yy, xx = np.mgrid[:H, :W]
    sat = a.max(2) - a.min(2)
    trail = (xx > W * .72) & (yy < H * .74) & (sat < 25)
    fg &= ~trail
    return arr, keep_largest(fg, k=1)

def cheesus(path, n=40):
    """Plush mouse on a dark doodle background: mask = everything not connected-dark from the border; more colours, no muddy edges."""
    from scipy import ndimage
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(int)
    lum = a.sum(2)
    dark = lum < 150
    lab, _ = ndimage.label(dark)
    border = set(np.unique(np.concatenate([lab[0], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(border))
    fg = ~bg
    fg = ndimage.binary_closing(fg, iterations=12)            # bridge the dark collar / zipper between head and hoodie
    fg = ndimage.binary_fill_holes(fg)
    fg = ndimage.binary_opening(fg, iterations=3)
    lab2, n2 = ndimage.label(fg)
    sizes = ndimage.sum(fg, lab2, range(1, n2 + 1))
    fg = np.isin(lab2, [i + 1 for i, v in enumerate(sizes) if v > sizes.max() * .08])
    W0, H0 = im.size
    size = (n, n)
    small = im.resize(size, Image.LANCZOS)
    small = small.quantize(40, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
    al = np.asarray(Image.fromarray((fg * 255).astype(np.uint8)).resize(size, Image.BOX)) > 120
    al = al.copy()
    for x in range(int(n * .3), int(n * .7)):                  # the shadow under the chin belongs to the character
        ys = np.where(al[:, x])[0]
        if len(ys):
            al[ys.min():ys.max() + 1, x] = True
    return np.asarray(small).copy(), al

def _recut(arr, fg, clear):
    """Clear a hand-picked region from the mask and close the new edge with the PFP's black outline."""
    H, W = fg.shape
    yy, xx = np.mgrid[:H, :W]
    fg = fg & ~clear(yy, xx)
    fg = keep_largest(fg, k=1)
    pad = np.pad(fg, 1)
    grow = pad.copy()
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        grow |= np.roll(np.roll(pad, dy, 0), dx, 1)            # padded: no wrap-around
    out = grow[1:-1, 1:-1]
    arr = arr.copy()
    edge = out & ~fg
    arr[edge] = (8, 8, 8)
    return arr, out

def quin_clean(path):
    """Ep03 recut: drop the frame bits (black bar on top, dotted line on the left, brown corner at the bottom-left)."""
    arr, fg = quin(path)
    ys, xs = np.where(fg)
    oy, ox = ys.min(), xs.min()
    def clear(yy, xx):
        y, x = yy - oy, xx - ox
        return ((y <= 0) & (x < 9)) | ((y == 21) & (x <= 4)) | ((y >= 32) & (x <= 9)) | ((y >= 31) & (x <= 5))
    return _recut(arr, fg, clear)

def taras_clean(path):
    """Ep03 recut: keep the green skull, crown and hair; drop the masked face and the hand behind him and stray background dots."""
    arr, fg = taras(path)
    ys, xs = np.where(fg)
    oy, ox = ys.min(), xs.min()
    def clear(yy, xx):
        y, x = yy - oy, xx - ox
        return (((x >= 25) & (y <= 14)) | ((x >= 28) & (y >= 14)) | ((x >= 22) & (y >= 22)) | ((x >= 19) & (y >= 27)) | ((x == 4) & (y <= 3))
                | ((y == 0) & (x >= 20)))
    return _recut(arr, fg, clear)

BODACIOUS_ROWS = {3: (16, 18), 4: (14, 18), 5: (12, 18), 6: (11, 18), 7: (10, 19), 8: (9, 19), 9: (8, 20), 10: (7, 21), 11: (7, 22),
                  12: (6, 22), 13: (6, 22), 14: (6, 23), 15: (5, 22), 16: (6, 21), 17: (6, 21), 18: (6, 21), 19: (6, 21), 20: (7, 21),
                  21: (7, 21), 22: (7, 20), 23: (8, 20), 24: (8, 20), 25: (9, 20), 26: (10, 20), 27: (11, 19), 28: (11, 18),
                  29: (11, 14), 30: (11, 14), 31: (11, 14)}

def bodacious(path):
    """Ep03 (Bodacious Pirate): the PFP background is a busy sunset, so the head is cut by a hand-measured row profile
    (mohawk, purple skull, mirrored shades, jaw, neck) and closed with a black outline."""
    arr, _, _ = native(path)
    H, W, _ = arr.shape
    fg = np.zeros((H, W), bool)
    for y, (x0, x1) in BODACIOUS_ROWS.items():
        fg[y, x0:x1 + 1] = True
    return _recut(arr, fg, lambda yy, xx: np.zeros_like(yy, bool))

def hammallama(path, tol=30):
    """Ep03: skull only — the drink cup in the PFP is a separate component and is left out of the head sprite."""
    arr, _, _ = native(path)
    H, W, _ = arr.shape
    bg = flood(arr, tol=tol, seeds=edge_seeds(H, W))
    fg = keep_largest(~bg, k=1, min_size=4)
    return arr, fg

CHARS = {
    'giulio': ('giulio.png', simple),
    'colin': ('colin.jpg', simple),
    'luke': ('luke.jpg', luke),
    'noside': ('noside.jpg', simple),
    'pondering': ('pondering.jpg', simple),
    'taras': ('taras.jpg', taras_clean),
    'chops': ('chops.jpg', chops),
    'elegy': ('elegy.jpg', simple),
    'errorgarden': ('errorgarden.jpg', simple),
    'pedrox': ('pedrox.jpg', simple),
    'quin': ('quin.jpg', quin_clean),
    'slaughter': ('slaughter.jpg', simple),
    'uh': ('uh.jpg', simple),
    'jeff': ('jeff.jpg', flat_plush),
    'cheesus': ('cheesus.jpg', cheesus),
    'deepcode': ('deepcode.jpg', deepcode),
    'bb': ('bb.jpg', bb),
    'hammallama': ('hammallama.jpg', hammallama),          # Ep03 (Based Ghouls holder)
    'bodacious': ('bodacious.jpg', bodacious),              # Ep03 (Based Ghouls holder) — Bodacious Pirate
}

def crop_alpha(rgba):
    ys, xs = np.where(rgba[..., 3] > 0)
    return rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

def build():
    os.makedirs(OUT, exist_ok=True)
    chars = dict(CHARS)
    for name, (f, fn) in chars.items():
        arr, fg = fn(os.path.join(paths.ORIG_GHOULS, f))
        rgba = to_rgba(arr, ~fg)
        Image.fromarray(crop_alpha(rgba)).save(os.path.join(OUT, name + '.png'))
    return sorted(chars)

def monster_mask(im, tol=34, ui_bars=False):
    """Background = pixels close to the dominant border colour AND connected to the border. Keeps black line art and white eyes."""
    from scipy import ndimage
    a = np.asarray(im.convert('RGB')).astype(int)
    border = np.concatenate([a[0], a[:, 0], a[:, -1], a[-1]])
    q = (border // 24)
    vals, counts = np.unique(q, axis=0, return_counts=True)
    ref = border[(q == vals[counts.argmax()]).all(1)].mean(0)
    near = np.abs(a - ref).sum(2) < tol * 3
    lab, _ = ndimage.label(near)
    edge = set(np.unique(np.concatenate([lab[0], lab[:, 0], lab[:, -1], lab[-1]]))) - {0}
    fg = ~np.isin(lab, list(edge))
    fg = ndimage.binary_closing(fg, iterations=4)        # rejoin parts separated by black line art (eyes, mouths)
    fg = ndimage.binary_fill_holes(fg)
    fg = ndimage.binary_opening(fg, iterations=2)
    blue_ui = (a[..., 2] > a[..., 0] + 70) & (a[..., 2] > a[..., 1] + 30) & ui_bars   # Telegram/screenshot UI bars only
    lab_b, _ = ndimage.label(blue_ui)
    bottom = set(np.unique(np.concatenate([lab_b[-1], lab_b[-2], lab_b[-6]]))) - {0}
    fg &= ~np.isin(lab_b, list(bottom))
    fg = ndimage.binary_opening(fg, iterations=2)
    lab2, n2 = ndimage.label(fg)
    if n2:
        sizes = ndimage.sum(fg, lab2, range(1, n2 + 1))
        keep = []
        for k, v in enumerate(sizes):
            ys, xs = np.where(lab2 == k + 1)
            thin = (xs.max() - xs.min()) < a.shape[1] * .04 or (ys.max() - ys.min()) < a.shape[0] * .04
            if v > sizes.max() * .06 and not thin:
                keep.append(k + 1)
        fg = np.isin(lab2, keep)
    return fg

def monster_sprite(im, fg, n, colors=32):
    """Downsample (box for colour, majority for alpha), quantize without dithering, 1px dark outline."""
    W0, H0 = im.size
    sc = n / max(W0, H0)
    size = (max(1, round(W0 * sc)), max(1, round(H0 * sc)))
    small = im.convert('RGB').resize(size, Image.LANCZOS)
    small = small.quantize(colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
    al = np.asarray(Image.fromarray((fg * 255).astype(np.uint8)).resize(size, Image.BOX)) > 110
    rgba = to_rgba(np.asarray(small).copy(), ~al)
    m = rgba[..., 3] > 0
    pad = np.pad(m, 1)
    grow = pad[1:-1, 1:-1] | pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
    out = np.pad(rgba, ((1, 1), (1, 1), (0, 0)))
    om = np.pad(grow & ~m, 1)
    out[om] = (14, 10, 16, 255)
    return crop_alpha(out)

def build_monsters():
    """monsters/  = in-world sprites (~48 px, same sizes as before)  ·  monsters_hd/ = close-up sprites (~120 px)."""
    out = os.path.join(OUT, 'monsters'); os.makedirs(out, exist_ok=True)
    out_hd = os.path.join(OUT, 'monsters_hd'); os.makedirs(out_hd, exist_ok=True)
    files = sorted(glob.glob(os.path.join(paths.ORIG_MONSTERS, 'monster*.png')))
    for f in files:
        b = os.path.basename(f)
        im = Image.open(f).convert('RGB')
        W, H = im.size
        a = np.asarray(im).copy()
        bgc = np.median(np.concatenate([a[0], a[:, 0], a[:, -1]]), 0)
        if b in ('monster19.png', 'monster02.png', 'monster03.png', 'monster04.png'):   # telegram screenshots
            a[int(H * .8):, int(W * .55):] = bgc
        if b == 'monster18.png':
            wy, wx = np.where(a.sum(2) > 700)
            a = a[wy.min():wy.max() + 1, wx.min():wx.max() + 1]
        a[-3:, :] = bgc                                                                  # crop UI strips touching the bottom edge
        im = Image.fromarray(a)
        if b == 'monster11.png':                                                          # thin frame line on the right edge
            ys_, xs_ = np.where((np.asarray(im).astype(int).sum(2) < 120)[:, int(W * .8):].sum(0, keepdims=True) > H * .5)
            if len(xs_):
                im = im.crop((0, 0, int(W * .8) + xs_.min() - 2, H))
        fg = monster_mask(im, ui_bars=b in ('monster02.png', 'monster03.png', 'monster04.png', 'monster19.png'))
        key = 'monster%d' % int(b[7:9])
        Image.fromarray(monster_sprite(im, fg, 48, 24)).save(os.path.join(out, key + '.png'))
        Image.fromarray(monster_sprite(im, fg, 120, 40)).save(os.path.join(out_hd, key + '.png'))

if __name__ == '__main__':
    print(build())
    build_monsters()
