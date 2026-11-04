"""Recover the native pixel grid of each PFP so sprites match the originals."""
import numpy as np
from PIL import Image

def fit_axis(edge, lo=12, hi=30):
    n = len(edge)
    best = (0, None, None)
    m = edge.mean() + 1e-6
    for p in np.arange(lo, hi, 0.02):
        for off in np.arange(0, p, 0.5):
            idx = np.round(np.arange(off, n - 1, p)).astype(int)
            idx = idx[(idx >= 0) & (idx < n)]
            if len(idx) < 8:
                continue
            # include neighbour to tolerate jpeg/rounding
            sc = np.maximum(edge[idx], edge[np.clip(idx - 1, 0, n - 1)]).mean() / m
            if sc > best[0]:
                best = (sc, p, off)
    return best

def native(path, period=None):
    a = np.asarray(Image.open(path).convert('RGB')).astype(float)
    H, W, _ = a.shape
    dx = np.abs(np.diff(a, axis=1)).sum(2).sum(0)
    dy = np.abs(np.diff(a, axis=0)).sum(2).sum(1)
    sx, px, ox = fit_axis(dx)
    sy, py, oy = fit_axis(dy)
    if period:
        px = py = period
    p = (px + py) / 2
    # boundaries at off + k*p (edge index i means boundary between i and i+1)
    ox = (ox + 1) % p
    oy = (oy + 1) % p
    xs = [x for x in np.arange(ox - p, W, p) if x + p * .3 >= 0 and x + p * .7 <= W]
    ys = [y for y in np.arange(oy - p, H, p) if y + p * .3 >= 0 and y + p * .7 <= H]
    out = []
    for y0 in ys:
        row = []
        for x0 in xs:
            cx0, cx1 = int(max(0, x0 + p * .3)), int(min(W, x0 + p * .7))
            cy0, cy1 = int(max(0, y0 + p * .3)), int(min(H, y0 + p * .7))
            if cx1 <= cx0 or cy1 <= cy0:
                row.append(None); continue
            row.append(np.median(a[cy0:cy1, cx0:cx1].reshape(-1, 3), 0))
        out.append(row)
    arr = np.array(out).astype(np.uint8)
    return arr, p, (sx, sy)
