"""The GhoulGate OP (shared by every episode from Ep02 on).

add_opening(ep, title_jp, title_en) appends: black/silent beat, OP title slam, equal-time roll call of all 17 ghouls
(one beat each — director's rule), whole-gang shot, made-up "other episode" montage, Mars walk, montage + Dark Tap, title card.
Beat-synced to music.m_op() (150 bpm, 14 bars).
"""
from shots import *


def add_opening(ep, title_jp, title_en):
    def s_gap(f):
        return E.bg_solid((0, 0, 0))
    ep.shot(s_gap, dur=.7)
    ep.mus(np.zeros((10, 2)), 0)          # hard musical cut: silence before the OP hits
    op, op_len = M.m_op()
    beat = 60 / 150
    roll = ['giulio', 'quin', 'chops', 'colin', 'uh', 'pedrox', 'slaughter', 'elegy', 'taras', 'jeff', 'luke',
            'noside', 'errorgarden', 'pondering', 'cheesus', 'deepcode', 'bb']      # everyone gets exactly one beat
    roll_pose = {'giulio': ('thumb', 'smug'), 'quin': ('crossed', 'smug'), 'chops': ('point', 'serious'), 'colin': ('fist', 'evil'), 'uh': ('cheer', 'happy'),
                 'pedrox': ('thumb', 'happy'), 'slaughter': ('crossed', 'serious'), 'elegy': ('smoke', 'deadpan'), 'taras': ('shrug', 'worried'),
                 'jeff': ('idle', 'deadpan'), 'luke': ('cheer', 'sparkle'), 'noside': ('talk_b', 'sad'), 'errorgarden': ('shock', 'shock'),
                 'pondering': ('facepalm', 'serious'), 'cheesus': ('idle', 'happy'), 'deepcode': ('smoke', 'menace'), 'bb': ('hero', 'happy')}

    def op_title(f, final=False):
        img = E.bg_solid((34, 0, 52))
        E.speed_radial(img, f.T, W // 2, H // 2, (150, 40, 210), n=110, inner=50)
        # whole gang silhouettes along the bottom, bouncing on the beat
        x = 14
        for n in roll:
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
                def put(hd, logo=logo):
                    lg = logo.resize((logo.width * 2, logo.height * 2), Image.NEAREST)
                    hd.alpha_composite(lg, ((960 - lg.width) // 2, 320))
                f.hi.append(put)
            if f.t > .9:
                E.title_text(f, 480, 410, title_jp, 40, (255, 240, 130), (50, 0, 40), 5)
                E.title_text(f, 480, 452, title_en, 22, (255, 255, 255), (50, 0, 40), 3)
            if f.t > f.d - .5:
                f.flash = (f.t - (f.d - .5)) / .5; f.flash_c = (0, 0, 0)
        if f.t < .25:
            f.flash = 1 - f.t / .25
        return img
    ep.shot(op_title, dur=4 * beat)
    ep.mus(op, 0, rms=.16, fout=.6)
    ep.sub_extra.append((ep.cur + .2, ep.cur + 4.5, '{\\an9\\fs34}OPENING THEME 「GHOULGATE!」\\N{\\fs26}歌：骸骨少女隊'))

    def op_roll(f):
        i = min(len(roll) - 1, int(f.t / beat))
        lt = f.t - i * beat
        n = roll[i]
        col = COL[n]
        img = E.bg_solid(tuple(int(c * .32) for c in col))
        d = ImageDraw.Draw(img)
        off = int(f.t * 200) % 60
        for k in range(-2, 10):
            x0 = k * 60 + off - 60
            d.polygon([(x0, 0), (x0 + 30, 0), (x0 - 40, H), (x0 - 70, H)], fill=tuple(int(c * .5) for c in col) + (255,))
        E.speed_h(img, f.T, tuple(min(255, int(c * 1.1)) for c in col), n=24, speed=1400, seed=i)
        p, e = roll_pose[n]
        k = ease_out(lt / .14)
        x = lerp(560, 330, k)
        ch, an = FC.character(n, p, e, t=f.T, marks=('sparkles',) if e in ('happy', 'sparkle') else (), blink=False)
        big = iscale(ch, 3)
        paste(img, big, x - big.width / 2, H - big.height + 40)
        # whip smear on entry
        if lt < .08:
            img = img.resize((W // 6, H), Image.BILINEAR).resize((W, H), Image.NEAREST)
        E.title_text(f, 70, 330, JPN[n], 64 if len(JPN[n]) <= 6 else 42, (255, 255, 255), tuple(int(c * .25) for c in col), 6, fnt=E.sfx_font(64 if len(JPN[n]) <= 6 else 42), anchor='lm')
        E.title_text(f, 74, 392, ENN[n], 26, col, (0, 0, 0), 4, anchor='lm')
        credits_ = [('原作', 'BASED GHOULS'), ('監督', '骨川 夜一'), ('キャラクターデザイン', '髑髏谷 ミカ'), ('ドット作画監督', '灰原 点')]
        r, nm = credits_[min(3, int(f.t / (17 * beat / 4)))]
        E.title_text(f, 40, 40, r, 20, (255, 255, 255), (20, 0, 30), 3, anchor='lm')
        E.title_text(f, 40, 72, nm, 34, (255, 255, 255), (20, 0, 30), 4, anchor='lm')
        return img
    ep.shot(op_roll, dur=17 * beat)

    def op_gang(f):
        """The whole gang, equal billing: three rows popping in on the beat, then all cheering together."""
        img = E.bg_solid((255, 170, 210))
        E.speed_radial(img, f.T, 240, 120, (255, 220, 235), n=100, inner=70)
        E.sparkles(img, f.T, 20)
        b = int(f.t / beat)
        rows = [roll[0:6], roll[6:12], roll[12:17]]
        for r, names in enumerate(rows):
            if b < r:
                continue
            for i, n in enumerate(names):
                ch, an = FC.character(n, 'cheer' if (b + i) % 2 else 'hero', 'happy', t=f.T, blink=False, legs=False)
                big = iscale(ch, 2)
                x = W * (i + .5) / len(names) + (14 if r == 1 else 0)
                y = 30 + r * 74 - an['head_top'][1] * 2 + (0 if (b + i) % 2 else 4)
                paste(img, big, x - big.width / 2, y)
        E.title_text(f, 40, 40, 'シリーズ構成・脚本', 20, (255, 255, 255), (60, 0, 40), 3, anchor='lm')
        E.title_text(f, 40, 72, '墓田 静香', 34, (255, 255, 255), (60, 0, 40), 4, anchor='lm')
        return img
    ep.shot(op_gang, dur=7 * beat)

    # made-up scenes from "other episodes" (OP montage)
    def fake_beach(f, lt):
        img = Wd.vgrad(W, H, [(0, (255, 150, 190)), (.45, (255, 200, 150)), (.62, (90, 170, 220)), (1, (240, 210, 150))])
        d = ImageDraw.Draw(img)
        d.ellipse((330, 20, 380, 70), fill=(255, 240, 220, 255)); d.ellipse((392, 44, 414, 66), fill=(255, 210, 200, 255))
        for i in range(8):
            y = 170 + i * 5
            x0 = (i * 37 + lt * 60) % 80
            for x in range(-80, W, 80):
                d.line((x + x0, y, x + x0 + 30, y), fill=(220, 240, 255, 255))
        d.rectangle((0, 200, W, H), fill=(236, 206, 150, 255))
        d.polygon([(90, 120), (150, 104), (210, 120)], fill=(255, 90, 120, 255)); d.line((150, 110, 150, 236), fill=(240, 240, 240, 255), width=2)
        for i, (n, x) in enumerate((('uh', 120), ('bb', 196))):
            ch, an = FC.character(n, 'relaxed', 'happy', t=f.T)
            ch = ch.rotate(90 if i else -90, expand=True)
            paste(img, ch, x - ch.width / 2, 236 - ch.height)
        ch, an = FC.character('giulio', 'thumb', 'happy', t=f.T, marks=('sparkles',))
        d.polygon([(318, 150), (330, 146), (346, 250), (334, 254)], fill=(80, 200, 230, 255), outline=(20, 60, 80, 255))
        paste(img, iscale(ch, 2), 300 - ch.width, 262 - ch.height * 2)
        return E.camera(img, 220 + lt * 30, 140, 1.15)
    def fake_rain(f, lt):
        img = Wd.vgrad(W, H, [(0, (6, 8, 24)), (1, (30, 30, 70))])
        d = ImageDraw.Draw(img)
        rnd = random.Random(4)
        for i in range(14):
            x0 = i * 36; h_ = rnd.randint(60, 160)
            d.rectangle((x0, H - h_ - 50, x0 + 30, H), fill=(14, 14, 34, 255))
            for k in range(10):
                if rnd.random() < .5:
                    d.rectangle((x0 + 4 + (k % 3) * 8, H - h_ - 40 + (k // 3) * 12, x0 + 8 + (k % 3) * 8, H - h_ - 36 + (k // 3) * 12), fill=rnd.choice([(255, 80, 200), (80, 220, 255), (255, 220, 120)]) + (255,))
        d.rectangle((0, 214, W, H), fill=(26, 24, 40, 255))
        ch, an = FC.character('colin', 'slump', 'sad', t=f.T)
        paste(img, iscale(ch, 3), 300 - ch.width * 1.5, 230 - ch.height * 3 + 30)
        for i in range(160):
            x = (rnd.random() * (W + 100) + lt * 120) % (W + 100) - 50
            y = (rnd.random() * H + lt * 600 + i * 7) % H
            d.line((x, y, x - 4, y + 12), fill=(150, 170, 230, 160))
        if .3 < lt < .38:
            f.flash = .6
        return img
    def fake_karaoke(f, lt):
        img = Wd.vgrad(W, H, [(0, (40, 0, 60)), (1, (10, 0, 20))])
        L = np.zeros((H, W, 3), np.float32)
        for i, c in enumerate(((255, 80, 200), (80, 200, 255), (255, 220, 80))):
            Wd.glow(L, 120 + i * 120 + math.sin(f.T * 3 + i) * 30, 40, 150, c, .7)
        d = ImageDraw.Draw(img)
        d.rectangle((0, 200, W, H), fill=(60, 30, 70, 255))
        d.line((210, 120, 210, 200), fill=(180, 180, 190, 255), width=2); d.ellipse((205, 112, 215, 124), fill=(60, 60, 70, 255))
        ch, an = FC.character('uh', 'cheer', 'happy', mouth=2 + int(f.T * 8) % 2, t=f.T, marks=('note',))
        paste(img, iscale(ch, 2), 210 - ch.width - 30, 210 - ch.height * 2 + 10)
        ch, an = FC.character('chops', 'press2', 'happy', t=f.T, marks=('note',))
        paste(img, iscale(ch, 2), 340 - ch.width, 210 - ch.height * 2 + 10)
        d.polygon([(318, 168), (370, 150), (374, 160), (322, 178)], fill=(200, 40, 40, 255))
        for i in range(10):
            hx = 20 + i * 48
            d.ellipse((hx, 236 - abs(math.sin(f.T * 9 + i)) * 6, hx + 30, 270), fill=(14, 0, 22, 255))
        return Wd.apply_light(img, L, .9)
    def fake_festival(f, lt):
        img = Wd.vgrad(W, H, [(0, (8, 6, 30)), (1, (40, 16, 50))])
        d = ImageDraw.Draw(img)
        rnd = random.Random(11)
        for b in range(3):
            cx, cy = 100 + b * 150, 60 + (b % 2) * 30
            r = ((lt + b * .3) % 1) * 70
            col = [(255, 120, 80), (120, 220, 255), (255, 230, 120)][b]
            for k in range(24):
                a = k * math.tau / 24
                d.point((cx + math.cos(a) * r, cy + math.sin(a) * r), fill=col + (255,))
                d.point((cx + math.cos(a) * r * .8, cy + math.sin(a) * r * .8), fill=col + (200,))
        pts = [(x, 130 + 10 * math.sin(x / 50)) for x in range(0, W, 30)]
        d.line(pts, fill=(30, 20, 20, 255))
        L = np.zeros((H, W, 3), np.float32)
        for x, y in pts:
            d.ellipse((x - 5, y, x + 5, y + 12), fill=(230, 60, 40, 255))
            Wd.glow(L, x, y + 6, 30, (255, 120, 60), .5)
        img = Wd.apply_light(img, L, .9)
        for i, n in enumerate(('cheesus', 'noside', 'pondering', 'errorgarden')):
            ch, an = FC.character(n, 'cheer' if i % 2 else 'idle', 'happy', t=f.T, marks=('sparkles',) if i == 0 else ())
            paste(img, iscale(ch, 2), 90 + i * 100 - ch.width, 270 - ch.height * 2 + 30)
        return img
    def fake_space(f, lt):
        img = E.bg_solid((4, 4, 12))
        d = ImageDraw.Draw(img)
        rnd = random.Random(2)
        for i in range(80):
            d.point((rnd.randrange(W), rnd.randrange(160)), fill=(230, 230, 230, 255))
        d.ellipse((60, 30, 84, 54), fill=(60, 120, 230, 255)); d.ellipse((66, 34, 76, 44), fill=(80, 190, 90, 255))
        d.rectangle((0, 180, W, H), fill=(170, 70, 40, 255))
        for x in range(0, W, 23):
            d.ellipse((x, 190 + (x * 7) % 50, x + 10, 194 + (x * 7) % 50), fill=(140, 50, 30, 255))
        d.line((300, 90, 300, 210), fill=(200, 200, 200, 255), width=2)
        wave = int(math.sin(f.T * 6) * 3)
        d.polygon([(302, 92), (352, 96 + wave), (302, 120)], fill=(255, 90, 210, 255))
        Wd.tiny(img, 308, 100, 'BASED', (255, 255, 255, 255), 2)
        for i, n in enumerate(('giulio', 'slaughter', 'pedrox')):
            ch, an = FC.character(n, 'thumb' if i == 0 else 'idle', 'happy', t=f.T)
            big = iscale(ch, 2)
            x = 120 + i * 70
            paste(img, big, x - big.width / 2, 222 - big.height)
            hx, hy = x, 222 - big.height + an['center'][1] * 2
            d.ellipse((hx - 34, hy - 36, hx + 34, hy + 30), outline=(200, 230, 255, 255), width=2)
            d.arc((hx - 26, hy - 30, hx + 10, hy - 4), 200, 260, fill=(255, 255, 255, 255), width=2)
        return E.camera(img, 240, 135 - lt * 10, 1.05)
    def fake_rodeo(f, lt):
        img = E.bg_solid((250, 200, 120))
        E.speed_h(img, f.T, (255, 230, 170), n=50, speed=1500)
        m = E.mon_sprite(14, 3.2)
        bounce = abs(math.sin(f.T * 12)) * 20
        paste(img, m, 240 - m.width / 2, 270 - m.height - bounce + 20)
        ch, an = FC.character('giulio', 'hero', 'happy', t=f.T, marks=('sparkles',))
        paste(img, iscale(ch, 2), 240 - ch.width, 270 - m.height - bounce - ch.height * 2 + 60)
        E.sfx_text(f, 760, 120, 'ヒャッハー！', 72, (255, 255, 255), (200, 60, 0), 6, rot=-10, shake=3)
        return img

    def op_montage_a(f):
        scenes_ = (fake_beach, fake_rain, fake_karaoke, fake_festival)
        i = min(3, int(f.t / (2 * beat)))
        lt = f.t - i * 2 * beat
        img = scenes_[i](f, lt)
        if lt < .05:
            f.flash = .7
        E.title_text(f, 40, 40, '音楽', 20, (255, 255, 255), (30, 0, 40), 3, anchor='lm')
        E.title_text(f, 40, 72, '鳴神 響八', 34, (255, 255, 255), (30, 0, 40), 4, anchor='lm')
        return img
    ep.shot(op_montage_a, dur=8 * beat)

    def op_mars(f):
        img = Wd.vgrad(W, H, [(0, (8, 6, 24)), (.55, (46, 16, 64)), (1, (160, 60, 64))])
        d = ImageDraw.Draw(img)
        rnd = random.Random(9)
        for i in range(90):
            x, y = rnd.randrange(W), rnd.randrange(int(H * .6))
            v = int(120 + 135 * (math.sin(f.T * 3 + i) + 1) / 2)
            d.point((x, y), fill=(v, v, v, 255))
        cx, cy, r = 360, 70, 40
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(200, 70, 40, 255))
        d.ellipse((cx - r + 8, cy - r + 6, cx + r - 3, cy + r - 8), fill=(226, 100, 56, 255))
        for (ox, oy, rr) in ((-12, -10, 8), (10, 8, 5), (-4, 16, 4)):
            d.ellipse((cx + ox - rr, cy + oy - rr, cx + ox + rr, cy + oy + rr), fill=(160, 50, 30, 255))
        pts = [(x, 206 + int(8 * math.sin(x / 31) + 3 * math.sin(x / 9))) for x in range(0, W + 4, 4)]
        d.polygon(pts + [(W, H), (0, H)], fill=(110, 40, 30, 255))
        # the gang walks in a line across the ridge (anime OP)
        walk = f.t * 46
        for i, n in enumerate(roll):
            x = -30 + walk - i * 27 + 300
            x = x % (W + 500) - 60
            if -40 < x < W + 40:
                ch, an = FC.character(n, 'run_a' if int(f.t * 6 + i) % 2 else 'run_b', 'happy', t=f.T)
                paste(img, ch, x - an['feet'][0], 210 - an['feet'][1] + int(8 * math.sin(x / 31)) - 1)
        E.title_text(f, 40, 40, '美術監督', 20, (255, 255, 255), (30, 0, 40), 3, anchor='lm')
        E.title_text(f, 40, 72, '地下室 蓮', 34, (255, 255, 255), (30, 0, 40), 4, anchor='lm')
        return img
    ep.shot(op_mars, dur=8 * beat)

    def op_tap(f):
        b = int(f.t / beat)
        img = console_close(f, 'giulio', presses=[k * beat * 2 + beat for k in range(4)], glow=1.8)
        for i in range(min(b + 1, 8)):
            m = E.mon_sprite(i + 1, 1.6)
            sil = Image.fromarray(np.where(np.asarray(m)[..., 3:] > 0, np.array([70 + i * 12, 0, 110 + i * 14, 255], np.uint8), 0).astype(np.uint8))
            ang = i * .78 + f.t * .4
            paste(img, sil, 240 + math.cos(ang) * 190 - sil.width / 2, 110 + math.sin(ang) * 80 - sil.height / 2)
        if f.t % beat < .06:
            f.flash = .4; f.flash_c = (180, 80, 255)
        E.title_text(f, 40, 40, '主題歌「GHOULGATE!」', 20, (255, 255, 255), (30, 0, 40), 3, anchor='lm')
        E.title_text(f, 40, 72, '骸骨少女隊', 34, (255, 255, 255), (30, 0, 40), 4, anchor='lm')
        return img
    def op_montage_b(f):
        if f.t < 2 * beat:
            img = fake_space(f, f.t)
        elif f.t < 4 * beat:
            img = fake_rodeo(f, f.t - 2 * beat)
        else:
            g = E.F(ep, f.T, f.t - 4 * beat, 4 * beat, [])
            img = op_tap(g)
            f.hi.extend(g.hi); f.flash = g.flash; f.flash_c = g.flash_c
            return img
        if (f.t % (2 * beat)) < .05:
            f.flash = .7
        E.title_text(f, 40, 40, '主題歌「GHOULGATE!」', 20, (255, 255, 255), (30, 0, 40), 3, anchor='lm')
        E.title_text(f, 40, 72, '骸骨少女隊', 34, (255, 255, 255), (30, 0, 40), 4, anchor='lm')
        return img
    ep.shot(op_montage_b, dur=8 * beat)
    ep.shot(lambda f: op_title(f, True), dur=4 * beat + 1.6)
    return ep


def add_ending(ep, title_jp, title_en, next_title_jp, next_line_jp, next_line_en, extra_cast=(), ed_len=None, preview_by='giulio', roll_extra=()):
    """ED (ballad + scrolling staff/voice credits over the Mars ridge) + 次回予告 voiced by Giulio + 0.8 s black.
    extra_cast: [(jp_role_name, en_name)] for non-ghoul voices (narrator, demon …) — credited with their VOICEVOX voice."""
    # ------------------------------------------------------------- ENDING
    roll_all = ['giulio', 'quin', 'chops', 'colin', 'uh', 'pedrox', 'slaughter', 'elegy', 'taras', 'jeff', 'luke',
                'noside', 'errorgarden', 'pondering', 'cheesus', 'deepcode', 'bb'] + list(roll_extra)
    credits_ = [
        ('', 'ゴールゲート', 'GHOULGATE', 64),
        ('', title_jp, title_en, 34),
        ('原作', 'BASED GHOULS', 'Original Work', 34),
        ('監督', '骨川 夜一', 'Director  Honekawa Yoichi', 34),
        ('シリーズ構成・脚本', '墓田 静香', 'Script  Hakada Shizuka', 34),
        ('キャラクターデザイン', '髑髏谷 ミカ', 'Character Design  Dokuroya Mika', 34),
        ('ドット作画監督', '灰原 点', 'Pixel Animation Director  Haibara Ten', 34),
        ('美術監督', '地下室 蓮', 'Art Director  Chikamuro Ren', 34),
        ('色彩設計', '紫藤 あかね', 'Color Design  Shido Akane', 34),
        ('撮影監督', '闇野 光', 'Compositing  Yamino Hikaru', 34),
        ('音楽', '鳴神 響八', 'Music  Narukami Kyohachi', 34),
        ('音響監督', '叩井 守', 'Sound Director  Tatakii Mamoru', 34),
        ('OP主題歌「GHOULGATE!」', '骸骨少女隊', 'Gaikotsu Shojo-tai', 34),
        ('ED主題歌「ダークタップ・ララバイ」', '夜更 ねむ', 'Yofuke Nemu', 34),
        ('キャスト', '', 'CAST', 34),
    ] + [('', f'{JPN[n]} ……… VOICEVOX:{dict(V.CREDITS).get(JPN[n], "")}', ENN[n], 20) for n in roll_all] + \
      [('', f'{jp} ……… VOICEVOX:{dict(V.CREDITS).get(jp, "")}', en, 20) for jp, en in extra_cast] + [
        ('アニメーション制作', 'スタジオ・クリプト', 'Studio Crypt', 34),
        ('製作', 'ゴールゲート製作委員会', 'GhoulGate Production Committee', 34),
    ]
    ED_LEN = 24.0 if ed_len is None else ed_len
    credits_h = 0
    for role, jp_, en, size in credits_:
        credits_h += (30 if role else 0) + (size + 10 if jp_ else 0) + 26 + (34 if size >= 30 else 10)

    def s_ed(f):
        img = Wd.vgrad(W, H, [(0, (8, 6, 24)), (.5, (46, 16, 64)), (1, (170, 70, 64))])
        d = ImageDraw.Draw(img)
        rnd = random.Random(9)
        for i in range(90):
            x, y = rnd.randrange(W), rnd.randrange(int(H * .6))
            v = int(120 + 135 * (math.sin(f.T * 2 + i) + 1) / 2)
            d.point((x, y), fill=(v, v, v, 255))
        cx, cy, r = 400, 60, 36
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(200, 70, 40, 255))
        pts = [(x, 214 + int(6 * math.sin(x / 31))) for x in range(0, W + 4, 4)]
        d.polygon(pts + [(W, H), (0, H)], fill=(100, 36, 28, 255))
        # the gang sitting on the ridge, monsters snoozing among them
        for i, n in enumerate(roll_all):
            x = 18 + i * 26.5
            ch, an = FC.character(n, 'relaxed', 'happy' if (i + int(f.T / 3)) % 5 == 0 else 'neutral', t=f.T)
            paste(img, ch, x - an['feet'][0], 222 - an['feet'][1] + int(6 * math.sin(x / 31)))
        for i, n in enumerate((1, 6, 15, 18)):
            m = E.mon_sprite(n, .8)
            paste(img, m, 30 + i * 125, 262 - m.height)
        def roll_fn(hd, t=f.t):
            CLIP = 280
            lay = Image.new('RGBA', (960, CLIP), (0, 0, 0, 0))
            y = CLIP + 10 - t * (credits_h + CLIP * .5) / (ED_LEN - 1.5)
            dd = ImageDraw.Draw(lay)
            for role, jp_, en, size in credits_:
                if role:
                    if -40 < y < CLIP + 40:
                        dd.text((480, y), role, font=E.ui_font(20), fill=(255, 200, 230), stroke_width=2, stroke_fill=(20, 0, 30), anchor='mm')
                    y += 30
                if jp_ and -60 < y < CLIP + 60:
                    dd.text((480, y), jp_, font=E.ui_font(size), fill=(255, 255, 255), stroke_width=3, stroke_fill=(20, 0, 30), anchor='mm')
                if jp_:
                    y += size + 10
                if en and -40 < y < CLIP + 40:
                    dd.text((480, y), en, font=E.ui_font(18), fill=(200, 200, 230), stroke_width=2, stroke_fill=(20, 0, 30), anchor='mm')
                y += 26 + (34 if size >= 30 else 10)
            a = np.asarray(lay).copy()
            fh = 40
            a[CLIP - fh:, :, 3] = (a[CLIP - fh:, :, 3] * np.linspace(1, 0, fh)[:, None]).astype(np.uint8)
            a[:fh, :, 3] = (a[:fh, :, 3] * np.linspace(0, 1, fh)[:, None]).astype(np.uint8)
            hd.alpha_composite(Image.fromarray(a), (0, 0))
        f.hi.append(roll_fn)
        if f.t < 1.0:
            f.flash = 1 - f.t; f.flash_c = (0, 0, 0)
        if f.t > f.d - 1.0:
            f.flash = (f.t - (f.d - 1.0)); f.flash_c = (0, 0, 0)
        return E.camera(img, 240 + math.sin(f.t * .2) * 6, 135, 1.03)
    ep.shot(s_ed, dur=ED_LEN)
    ep.mus(M.m_ed(ED_LEN + .5), 0, rms=.11, fout=1.5)

    def s_prev(f):
        img = E.bg_solid((255, 236, 120))
        d = ImageDraw.Draw(img)
        for i in range(0, W + H, 24):
            o = int(f.t * 40) % 24
            d.line((i - o, 0, i - H - o, H), fill=(255, 214, 80, 255), width=8)
        b = int(f.t / .45)
        for i in range(min(8, b + 1)):
            m = E.mon_sprite([1, 5, 8, 11, 14, 15, 18, 4][i], 1.2)
            paste(img, m, 50 + (i % 4) * 110 - m.width / 2 + 30, 80 + (i // 4) * 90 - m.height / 2 + int(math.sin(f.T * 6 + i) * 4))
        E.title_text(f, 40, 50, '次回予告', 64, (255, 255, 255), (200, 30, 60), 6, fnt=E.sfx_font(64), anchor='lm')
        E.title_text(f, 480, 330, next_title_jp, 42, (200, 30, 60), (255, 255, 255), 5)
        if f.t > f.d - .5:
            f.flash = (f.t - (f.d - .5)) / .5; f.flash_c = (0, 0, 0)
        return img
    ep.shot(s_prev, lines=[(preview_by, next_line_jp, next_line_en, {'emo': 'normal', 'at': .3})], post=.8)
    ep.mus(M.m_preview(ep.shots[-1][1]), 0, rms=.11)
    ep.shot(lambda f: E.bg_solid((0, 0, 0)), dur=.8)
    return ep
