import numpy as np
from collections import deque

def flood(arr, tol=40, seeds=None, local=True):
    """Return background mask by flood-filling from the border.
    local=True compares neighbour-to-neighbour (handles gradients)."""
    H, W, _ = arr.shape
    a = arr.astype(int)
    bg = np.zeros((H, W), bool)
    q = deque()
    if seeds is None:
        seeds = [(y, x) for y in range(H) for x in (0, W - 1)] + [(y, x) for x in range(W) for y in (0,)]
    for s in seeds:
        q.append((s, a[s]))
    ref_colors = [a[s] for s in seeds]
    while q:
        (y, x), ref = q.popleft()
        if bg[y, x]:
            continue
        if np.abs(a[y, x] - ref).sum() > tol:
            continue
        bg[y, x] = True
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and not bg[ny, nx]:
                q.append(((ny, nx), a[y, x] if local else ref))
    return bg

def to_rgba(arr, bg):
    H, W, _ = arr.shape
    out = np.zeros((H, W, 4), np.uint8)
    out[..., :3] = arr
    out[..., 3] = np.where(bg, 0, 255)
    return out

def ascii_mask(rgba):
    return "\n".join("".join('#' if p[3] else '.' for p in row) for row in rgba)
