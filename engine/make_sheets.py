"""Generate the series-bible reference sheets (cast lineup, per-ghoul model sheets, monsters, console).

    engine/.venv/bin/python engine/make_sheets.py
Writes into series_bible/model_sheets/.
"""
import os, glob
from PIL import Image, ImageDraw, ImageFont
import paths
import face as FC
import skeleton as K
import world as Wd
import voice as V

OUT = os.path.join(paths.ROOT, 'series_bible', 'model_sheets')
CAST = ['giulio', 'quin', 'chops', 'colin', 'uh', 'pedrox', 'slaughter', 'elegy', 'taras', 'jeff', 'luke',
        'noside', 'errorgarden', 'pondering', 'cheesus', 'deepcode', 'bb', 'hammallama', 'bodacious']
EXPRS = ['neutral', 'shock', 'angry', 'happy', 'sparkle', 'worried', 'serious', 'sad', 'sleep', 'deadpan', 'evil', 'smug']
POSES = ['idle', 'talk_a', 'shrug', 'cheer', 'shock', 'point', 'fist', 'press2', 'crossed', 'facepalm', 'run_a', 'hero']
MARKS = {'shock': ('!', 'sweat'), 'angry': ('anger',), 'worried': ('sweat',), 'happy': ('sparkles',)}
BG = (44, 36, 60, 255)

def font(size, bold=True):
    return ImageFont.truetype(os.path.join(paths.FONTS, 'MPLUSRounded1c-ExtraBold.ttf' if bold else 'MPLUSRounded1c-Bold.ttf'), size)

def up(im, k):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)

def original_file(name):
    for f in glob.glob(os.path.join(paths.ORIG_GHOULS, name + '.*')):
        return f

def model_sheet(name, jp, en):
    W_, H_ = 1800, 1120
    sh = Image.new('RGBA', (W_, H_), BG)
    d = ImageDraw.Draw(sh)
    d.text((40, 30), f'{jp}  /  {en}', font=font(56), fill=(255, 255, 255))
    vc = V.CAST[name]['normal'][0]
    d.text((40, 100), f'key: {name}    voice: VOICEVOX {dict(V.CREDITS).get(jp, "?")} (style id {vc})    '
                      f'eyes: {K.FACE[name]["kind"]}    bone: {K.BONE.get(name)}', font=font(24, False), fill=(200, 200, 230))
    # original PFP
    of = original_file(name)
    if of:
        o = Image.open(of).convert('RGBA'); o.thumbnail((300, 300))
        sh.alpha_composite(o, (40, 160))
        d.text((40, 470), 'original PFP', font=font(20, False), fill=(180, 180, 200))
    # native sprite x8
    sp = up(FC.head_sprite(name), 8)
    sh.alpha_composite(sp, (380, 160))
    d.text((380, 160 + sp.height + 6), 'native sprite (x8)', font=font(20, False), fill=(180, 180, 200))
    # full body x5
    ch, an = FC.character(name, 'idle', 'neutral', t=.3, blink=False)
    big = up(ch, 5)
    sh.alpha_composite(big, (720, 140))
    d.text((720, 140 + big.height), 'full body (x5) — neck aligned to spine', font=font(20, False), fill=(180, 180, 200))
    # expressions
    y0 = 830
    d.text((40, y0 - 40), 'Expressions', font=font(30), fill=(255, 220, 140))
    for i, e in enumerate(EXPRS):
        ch, an = FC.character(name, 'idle', e, mouth=2 if e in ('shock', 'angry') else 0, t=.3, marks=MARKS.get(e, ()), blink=False, legs=False)
        im = up(ch, 3)
        sh.alpha_composite(im, (40 + i * 145, y0))
        d.text((40 + i * 145, y0 + 230), e, font=font(18, False), fill=(200, 200, 230))
    # poses
    y1 = 900
    d.text((1240, 140), 'Poses', font=font(30), fill=(255, 220, 140))
    for i, p in enumerate(POSES):
        ch, an = FC.character(name, p, 'neutral', t=.3, blink=False)
        im = up(ch, 2)
        x = 1240 + (i % 4) * 135; y = 190 + (i // 4) * 200
        sh.alpha_composite(im.crop((0, 0, im.width, min(im.height, 190))), (x, y))
        d.text((x, y + 172), p, font=font(16, False), fill=(200, 200, 230))
    sh.convert('RGB').save(os.path.join(OUT, f'{name}.png'))

def lineup(names, jp):
    cell = 110
    sh = Image.new('RGBA', (cell * len(names) + 40, 470), BG)
    d = ImageDraw.Draw(sh)
    d.text((20, 14), 'GhoulGate — cast lineup (game scale x3)', font=font(30), fill=(255, 255, 255))
    for i, n in enumerate(names):
        ch, an = FC.character(n, 'idle', 'neutral', t=.3, blink=False)
        im = up(ch, 3)
        x = 20 + i * cell + (cell - im.width) // 2
        sh.alpha_composite(im, (x, 400 - im.height))
        d.text((20 + i * cell + cell // 2, 420), jp[n], font=font(16 if len(jp[n]) <= 6 else 11), fill=(255, 255, 255), anchor='mm')
        d.text((20 + i * cell + cell // 2, 446), n, font=font(14, False), fill=(190, 190, 220), anchor='mm')
    sh.convert('RGB').save(os.path.join(OUT, '00_cast_lineup.png'))

def monsters():
    files = sorted(glob.glob(os.path.join(paths.SPRITES, 'monsters', 'monster*.png')), key=lambda f: int(os.path.basename(f)[7:-4]))
    cols = 7
    sh = Image.new('RGBA', (cols * 200 + 40, ((len(files) + cols - 1) // cols) * 220 + 80), BG)
    d = ImageDraw.Draw(sh)
    d.text((20, 14), 'Dark Tap monsters (summoned by tapping) — sprite x3', font=font(30), fill=(255, 255, 255))
    for i, f in enumerate(files):
        im = up(Image.open(f).convert('RGBA'), 3)
        x, y = 20 + (i % cols) * 200, 70 + (i // cols) * 220
        sh.alpha_composite(im, (x + (190 - im.width) // 2, y + max(0, 180 - im.height)))
        d.text((x + 95, y + 200), os.path.basename(f)[:-4], font=font(18, False), fill=(200, 200, 230), anchor='mm')
    sh.convert('RGB').save(os.path.join(OUT, '01_monsters.png'))

def console_sheet():
    im = Wd.vgrad(480, 200, [(0, (26, 14, 40)), (1, (8, 4, 14))])
    Wd.console(im, 130, 196, 1.0, 0, 0, 1.2, 4)
    Wd.console(im, 330, 196, 1.0, 1, 0, 2.6, 4)
    im = up(im, 2)
    d = ImageDraw.Draw(im)
    d.text((20, 10), 'The Dark Tap console — TAP (violet dome) / UNTAP (bone white). Left idle, right TAP pressed + glowing',
           font=font(18, False), fill=(255, 255, 255))
    im.convert('RGB').save(os.path.join(OUT, '02_dark_tap_console.png'))

def demon_sheet():
    import demon as DM
    sh = Image.new('RGBA', (4 * 340 + 40, 640), BG)
    d = ImageDraw.Draw(sh)
    d.text((20, 14), 'BTC Demon (Ep02) — poses idle / open / magic / point (x2) + lila flame asset', font=font(28), fill=(255, 255, 255))
    for i, (p, e, m) in enumerate((('idle', 'glow', 0), ('open', 'wide', 2), ('magic', 'glow', 3), ('point', 'closed', 0))):
        im, _ = DM.demon_image(p, e, m)
        sh.alpha_composite(up(im, 2), (20 + i * 340, 70))
        d.text((20 + i * 340 + 160, 600), f'{p} / eyes {e}', font=font(18, False), fill=(200, 200, 230), anchor='mm')
    for k in range(10):
        DM.flame(sh, 60 + k * 135, 590, k * .3, 4, k)
    sh.convert('RGB').save(os.path.join(OUT, '03_btc_demon.png'))

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    jp = {jp_name: None for jp_name, _ in V.CREDITS}
    import shots
    for n in CAST:
        model_sheet(n, shots.JPN[n], shots.ENN[n])
    lineup(CAST, shots.JPN)
    monsters()
    console_sheet()
    demon_sheet()
    print('sheets in', OUT)
