"""GhoulGate v2 score + SFX: anime-style arrangements rendered from a General MIDI
soundfont (MuseScore_General.sf2) through tinysoundfont. No chiptune timbres."""
import math, random, wave
import numpy as np
from scipy.signal import lfilter, fftconvolve
import tinysoundfont

SR = 44100
import paths
SF2 = paths.SF2

# ======================================================================= DSP helpers
def lowpass(x, fc):
    a = math.exp(-2 * math.pi * fc / SR)
    return lfilter([1 - a], [1, -a], x, axis=0)

def highpass(x, fc):
    return x - lowpass(x, fc)

def bandpass(x, lo, hi):
    return lowpass(highpass(x, lo), hi)

def noise(n, seed=0):
    return np.random.default_rng(seed).uniform(-1, 1, n)

def env_exp(n, tau):
    return np.exp(-np.arange(n) / SR / tau)

def fade(buf, fin=0.0, fout=0.0):
    b = buf.copy()
    n = len(b)
    if fin:
        k = min(n, int(fin * SR)); b[:k] *= np.linspace(0, 1, k)[:, None] if b.ndim == 2 else np.linspace(0, 1, k)
    if fout:
        k = min(n, int(fout * SR)); b[n - k:] *= np.linspace(1, 0, k)[:, None] if b.ndim == 2 else np.linspace(1, 0, k)
    return b

_IR = {}
def _ir(length, bright, seed=1):
    key = (round(length, 2), bright, seed)
    if key not in _IR:
        n = int(length * SR)
        t = np.arange(n) / SR
        out = np.zeros((n, 2))
        for ch in range(2):
            nz = noise(n, seed + ch)
            # darker as it decays
            early = lowpass(nz, bright)
            late = lowpass(nz, bright * .35)
            mix = np.exp(-t * 3)
            out[:, ch] = (early * mix + late * (1 - mix)) * np.exp(-t * 6.9 / length)
        out[:int(.012 * SR)] *= np.linspace(0, 1, int(.012 * SR))[:, None]
        out /= np.sqrt((out ** 2).sum(0))[None, :] + 1e-9
        _IR[key] = out
    return _IR[key]

def reverb(buf, mix=.25, length=2.2, bright=5000):
    """Convolution reverb with a synthetic decaying-noise impulse response."""
    if buf.ndim == 1:
        buf = np.stack([buf, buf], 1)
    ir = _ir(length, bright)
    wet = np.zeros((len(buf) + len(ir) - 1, 2))
    for ch in range(2):
        wet[:, ch] = fftconvolve(buf[:, ch], ir[:, ch])
    out = np.zeros_like(wet)
    out[:len(buf)] += buf
    out += wet * mix
    return out[:len(buf) + int(length * SR * .6)]

def mono(buf):
    return buf.mean(1) if buf.ndim == 2 else buf

def norm(buf, peak=.9):
    p = np.abs(buf).max()
    if p < 1e-9:
        return buf
    return buf * (peak / p)

def soft(buf, drive=1.0):
    return np.tanh(buf * drive) / np.tanh(drive)

def write_wav(path, buf):
    if buf.ndim == 1:
        buf = np.stack([buf, buf], 1)
    x = np.tanh(buf * 1.1) * .95
    x = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(x.tobytes())

# ======================================================================= soundfont engine
_SYN = None
_SFID = None

def _synth():
    global _SYN, _SFID
    if _SYN is None:
        _SYN = tinysoundfont.Synth(samplerate=SR, gain=0)
        _SFID = _SYN.sfload(SF2, gain=6.0, max_voices=384)
    return _SYN, _SFID

NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

def n2m(s):
    s = s.strip()
    base = NOTE[s[0].upper()]
    i = 1
    while i < len(s) and s[i] in '#b':
        base += 1 if s[i] == '#' else -1
        i += 1
    return base + 12 * (int(s[i:]) + 1)

CHORD = {
    '': [0, 4, 7], 'm': [0, 3, 7], '7': [0, 4, 7, 10], 'm7': [0, 3, 7, 10], 'maj7': [0, 4, 7, 11],
    'm9': [0, 3, 7, 10, 14], 'maj9': [0, 4, 7, 11, 14], '13': [0, 4, 10, 14, 21], '7b9': [0, 4, 7, 10, 13],
    'sus4': [0, 5, 7], 'dim': [0, 3, 6], 'add9': [0, 4, 7, 14], 'm7b5': [0, 3, 6, 10], '9': [0, 4, 7, 10, 14],
    '5': [0, 7, 12], 'b2': [0, 1, 7],
}

def chord(name, octave=4):
    root = name[0]
    i = 1
    acc = 0
    while i < len(name) and name[i] in '#b':
        acc += 1 if name[i] == '#' else -1; i += 1
    r = NOTE[root] + acc + 12 * (octave + 1)
    return [r + iv for iv in CHORD[name[i:]]]

# GM programs used
P = dict(piano=0, ep=4, celesta=8, glock=9, musicbox=10, vibes=11, xylo=13, bells=14, nylon=24, steel=25,
         jazzgtr=26, od=29, dist=30, fbass=33, pbass=34, violin=40, cello=42, contra=43, pizz=45, harp=46,
         timp=47, strings=48, slowstr=49, choir=52, orchhit=55, trumpet=56, tuba=58, horns=60, brass=61,
         oboe=68, bassoon=70, clarinet=71, flute=73, whistle=78, warmpad=89, taiko=116, revcym=119)
KIT = dict(standard=0, room=8, power=16, jazz=32, brush=40, orch=48)
DR = dict(kick=36, kick2=35, snare=38, rim=37, clap=39, esnare=40, hh=42, ped=44, oh=46, crash=49, crash2=57,
          ride=51, bell=53, splash=55, china=52, tom1=50, tom2=48, tom3=47, tom4=45, tom5=43, tom6=41,
          tri=81, mtri=80, wood_hi=76, wood_lo=77, tamb=54, cowbell=56, chimes=84, shaker=82, timpani=47)

class Song:
    """Collects MIDI-ish events in seconds, renders them through the soundfont."""
    def __init__(self, bpm=120, seed=0):
        self.bpm = bpm
        self.beat = 60.0 / bpm
        self.ev = []           # (t, order, kind, args)
        self.setup = {}        # chan -> (bank, preset, drums, vol, pan, expr)
        self.rnd = random.Random(seed)

    def inst(self, ch, prog, vol=100, pan=64, drums=False, kit=0):
        if drums:
            self.setup[ch] = (128, kit, True, vol, pan)
        else:
            self.setup[ch] = (0, prog, False, vol, pan)

    def note_t(self, t, dur, key, vel, ch, human=True):
        if key < 0 or key > 127:
            return
        if human:
            t += self.rnd.uniform(-.004, .004)
            vel = vel + self.rnd.randint(-6, 6)
        vel = int(max(1, min(127, vel)))
        t = max(0.0, t)
        self.ev.append((t, 1, 'on', (ch, key, vel)))
        self.ev.append((t + max(.02, dur), 0, 'off', (ch, key)))

    def note(self, beat, dur, key, vel, ch, human=True):
        self.note_t(beat * self.beat, dur * self.beat, key, vel, ch, human)

    def notes(self, beat, dur, keys, vel, ch, strum=0.0):
        for i, k in enumerate(keys):
            self.note_t(beat * self.beat + i * strum, dur * self.beat - i * strum, k, vel, ch)

    def hit(self, beat, key, vel, ch=9):
        self.note(beat, .5, key, vel, ch)

    def cc_t(self, t, ch, cc, val):
        self.ev.append((max(0.0, t), 2, 'cc', (ch, cc, int(max(0, min(127, val))))))

    def bend_t(self, t, ch, val):
        self.ev.append((max(0.0, t), 2, 'bend', (ch, int(max(0, min(16383, val))))))

    def alloff_t(self, t):
        self.ev.append((max(0.0, t), -1, 'alloff', ()))

    def mel(self, beat, spec, ch, vel=96, unit=.5, tp=0, legato=.95):
        """spec: 'A4:2 C5:1 -:1' durations in `unit` beats; '+' joins chord tones."""
        b = beat
        for tok in spec.split():
            name, _, ln = tok.partition(':')
            ln = float(ln or 1)
            if name not in ('-', '.'):
                for nm in name.split('+'):
                    self.note(b, ln * unit * legato, n2m(nm) + tp, vel, ch)
            b += ln * unit
        return b

    def render(self, dur, tail=0.0):
        syn, sf = _synth()
        for ch in range(16):
            syn.sounds_off(ch)
            syn.control_change(ch, 121, 0)    # reset controllers
        for ch, (bank, preset, drums, vol, pan) in self.setup.items():
            syn.program_select(ch, sf, bank, preset, is_drums=drums)
            syn.control_change(ch, 7, vol)
            syn.control_change(ch, 10, pan)
            syn.control_change(ch, 11, 127)
            syn.pitchbend(ch, 8192)
        total = int((dur + tail) * SR)
        out = np.zeros((total, 2), np.float32)
        ev = sorted(self.ev, key=lambda e: (e[0], e[1]))
        pos = 0
        def gen_to(target):
            nonlocal pos
            target = min(target, total)
            while pos < target:
                k = min(target - pos, 8192)
                buf = np.frombuffer(syn.generate(k), dtype=np.float32).reshape(-1, 2)
                out[pos:pos + k] = buf
                pos += k
        for t, _, kind, a in ev:
            gen_to(int(t * SR))
            if pos >= total:
                break
            if kind == 'on':
                syn.noteon(*a)
            elif kind == 'off':
                syn.noteoff(*a)
            elif kind == 'cc':
                syn.control_change(*a)
            elif kind == 'bend':
                syn.pitchbend(*a)
            elif kind == 'alloff':
                for ch in range(16):
                    syn.notes_off(ch)
        gen_to(total)
        for ch in range(16):
            syn.sounds_off(ch)
        return out.astype(np.float64)

def finish(buf, rev=.22, length=2.2, peak=.9, fin=0.0, fout=0.0, dur=None, bright=5000):
    x = reverb(buf, rev, length, bright) if rev else buf
    if dur is not None:
        n = int(dur * SR)
        if len(x) < n:
            x = np.concatenate([x, np.zeros((n - len(x), 2))])
        x = x[:n]
    x = fade(x, fin, fout)
    return norm(soft(norm(x, 1.0), 1.3), peak)

def crackle(n, seed=11, density=22):
    rnd = np.random.default_rng(seed)
    c = np.zeros(n)
    idx = rnd.integers(0, n, int(n / SR * density))
    c[idx] = rnd.uniform(-.5, .5, len(idx))
    c = lowpass(c, 4000)
    hiss = lowpass(noise(n, seed + 1), 2500) * .01
    return c * .35 + hiss

def crickets(n, seed=3, level=.05):
    t = np.arange(n) / SR
    out = np.zeros(n)
    rnd = random.Random(seed)
    for k in range(3):
        f = 4200 + rnd.uniform(-300, 300)
        rate = 26 + rnd.uniform(-3, 3)
        gate = (np.sin(2 * np.pi * rate * t + k) > .55) * (np.sin(2 * np.pi * (.6 + .2 * k) * t + k * 2) > .25)
        out += np.sin(2 * np.pi * f * t) * gate * level
    return lowpass(out, 6000)

# ======================================================================= score
def m_basement(dur):
    s = Song(60, seed=1)
    s.inst(0, P['contra'], 110); s.inst(1, P['slowstr'], 70); s.inst(2, P['choir'], 50); s.inst(3, P['piano'], 70)
    s.note_t(0, dur, n2m('C2'), 80, 0)
    s.note_t(0, dur, n2m('C3'), 60, 1); s.note_t(1.0, dur, n2m('Db3'), 50, 1)
    s.note_t(1.5, dur, n2m('G4'), 40, 2); s.note_t(2.5, dur, n2m('Ab4'), 34, 2)
    s.note_t(.3, 3, n2m('C1'), 70, 3); s.note_t(.3, 3, n2m('Db1'), 60, 3)
    x = s.render(dur, 2)
    n = len(x)
    t = np.arange(n) / SR
    wind = lowpass(noise(n, 9), 260) * (0.6 + 0.4 * np.sin(t * .7)) * .6
    x += wind[:, None]
    # heartbeat that speeds up as Giulio approaches
    tt, gap = 1.0, 1.0
    while tt < dur - .3:
        hb = sfx('heartbeat')
        i = int(tt * SR); j = min(n, i + len(hb))
        x[i:j] += hb[:j - i, None] * .9
        gap = max(.42, gap * .9); tt += gap
    return finish(x, .3, 2.5, .85, fin=1.0, dur=dur)

def m_chill(dur, bpm=82):
    s = Song(bpm, seed=2)
    s.inst(0, P['ep'], 100, 58); s.inst(1, P['fbass'], 105); s.inst(2, P['vibes'], 78, 80)
    s.inst(3, P['jazzgtr'], 70, 40); s.inst(9, 0, 90, drums=True, kit=KIT['jazz'])
    bars = int(math.ceil(dur / (4 * s.beat))) + 1
    prog = ['Dm9', 'G13', 'Cmaj9', 'A7b9']
    roots = {'Dm9': 'D2', 'G13': 'G1', 'Cmaj9': 'C2', 'A7b9': 'A1'}
    sw = .17
    for b in range(bars):
        c = prog[b % 4]; b0 = b * 4
        voic = chord(c, 3 if c in ('G13', 'A7b9') else 4)[:4]
        s.notes(b0, 1.4, voic, 70, 0, strum=.012)
        s.notes(b0 + 1.5 + sw, 2.3, voic, 62, 0, strum=.012)
        r = n2m(roots[c]) + 12
        for p, iv, ln in ((0, 0, 1.3), (1.5 + sw, 7, .45), (2, 12, 1.0), (3.5 + sw, 10 if c != 'Cmaj9' else 11, .45)):
            s.note(b0 + p, ln, r + iv, 92, 1)
        s.hit(b0, DR['kick'], 88); s.hit(b0 + 2.5 + sw, DR['kick'], 70)
        s.hit(b0 + 1, DR['rim'], 70); s.hit(b0 + 3, DR['snare'], 58)
        for k in range(8):
            s.hit(b0 + k * .5 + (sw if k % 2 else 0), DR['ride'] if k % 2 == 0 else DR['hh'], 52 if k % 2 else 62)
        if b % 4 in (2, 3) and b >= 2:
            s.mel(b0, ['-:1 F5:1 A5:1 C6:2 A5:1 G5:1 F5:1', 'E5:3 D5:1 C5:2 -:2'][b % 2], 2, 80)
        if b % 4 == 1 and b >= 4:
            s.mel(b0 + 2, 'A4:.5 C5:.5 D5:.5 F5:.5 A5:2', 3, 64)
    x = s.render(dur, 2.5)
    n = len(x)
    x = lowpass(x, 7000)                      # lo-fi roll-off
    x += crackle(n)[:, None]
    return finish(x, .18, 1.8, .85, fin=.3, fout=1.0, dur=dur)

def m_op():
    bpm = 150
    s = Song(bpm, seed=3)
    beat = s.beat
    GTR, LEAD, BASS, PNO, STR, BRS, HIT = 0, 1, 2, 3, 4, 5, 6
    s.inst(GTR, P['dist'], 92, 44); s.inst(LEAD, P['od'], 104, 76); s.inst(BASS, P['pbass'], 112)
    s.inst(PNO, P['piano'], 84, 84); s.inst(STR, P['strings'], 92, 52); s.inst(BRS, P['brass'], 90, 70)
    s.inst(HIT, P['orchhit'], 110); s.inst(9, 0, 112, drums=True, kit=KIT['power'])
    s.inst(7, P['timp'], 100)
    # bar 0: hit + crash + tom fill
    s.notes(0, 1.5, chord('Am', 4), 120, HIT)
    s.notes(0, 1.5, [n2m('A2'), n2m('E3'), n2m('A3')], 120, GTR)
    s.note(0, 2, n2m('A1'), 110, BASS)
    s.hit(0, DR['crash'], 120); s.hit(0, DR['kick'], 120); s.note(0, 1, n2m('A2'), 120, 7)
    for k in range(6):
        s.hit(2 + k * .25, DR['snare'], 70 + k * 9)
    for k, tm in enumerate((DR['tom1'], DR['tom2'], DR['tom3'], DR['tom5'])):
        s.hit(3.5 + k * .125, tm, 110)
    verse = ['Am', 'F', 'G', 'E']
    chorus = ['F', 'G', 'Em', 'Am', 'F', 'G', 'E', 'Am']

    def drums(b0, full, last=False):
        for k in range(4):
            s.hit(b0 + k, DR['kick'], 112 if k % 2 == 0 else (100 if full else 0))
            if full:
                s.hit(b0 + k + .5, DR['kick'], 70 if k == 1 else 0)
            if k % 2:
                s.hit(b0 + k, DR['snare'], 112)
        for k in range(8):
            s.hit(b0 + k * .5, DR['oh'] if (full and k % 2) else DR['hh'], 82 if k % 2 else 66)
        if last:
            for k in range(4):
                s.hit(b0 + 3 + k * .25, [DR['tom1'], DR['tom2'], DR['tom3'], DR['tom5']][k], 110)

    def power(c, octave=2):
        r = chord(c, octave)[0]
        return [r, r + 7, r + 12]

    # verse: palm-muted 8th power chords + piano arps + bass
    for i, c in enumerate(verse):
        b0 = 4 + i * 4
        for k in range(8):
            s.notes(b0 + k * .5, .3, power(c), 92 if k % 4 == 0 else 74, GTR)
        cn = chord(c, 4)
        arp = [cn[0], cn[1], cn[2], cn[0] + 12, cn[2], cn[1], cn[0] + 12, cn[2]]
        for k in range(8):
            s.note(b0 + k * .5, .45, arp[k] + 12, 70, PNO)
        r = chord(c, 1)[0]
        for k in range(8):
            s.note(b0 + k * .5, .45, r + 12 * (k % 2), 100, BASS)
        drums(b0, False, last=(i == 3))
        s.notes(b0, 4, chord(c, 4), 52, STR)
    s.note(4 * 4 + 3.5, .5, n2m('E2'), 110, 7)
    # chorus
    mel = ['C5:2 C5:1 D5:1 E5:2 F5:2', 'G5:3 F5:1 E5:2 D5:2', 'E5:2 D5:1 C5:1 B4:2 G4:2', 'A4:2 C5:2 E5:4',
           'F5:2 E5:1 F5:1 G5:2 A5:2', 'B5:2 A5:1 G5:1 D5:2 G5:2', 'G#5:2 A5:1 B5:1 D6:2 B5:2', 'C6:3 B5:1 A5:4']
    for i, c in enumerate(chorus):
        b0 = 20 + i * 4
        s.mel(b0, mel[i], LEAD, 108, legato=.98)
        s.mel(b0, mel[i], STR, 86, tp=12, legato=1.0)
        s.notes(b0, 2, power(c), 104, GTR); s.notes(b0 + 2, 2, power(c), 98, GTR)
        for p in (0, .5, 1, 1.5, 2, 2.5, 3, 3.5):
            s.notes(b0 + p, .4, chord(c, 4), 64 if p % 1 else 76, PNO)
        r = chord(c, 1)[0]
        for k in range(8):
            s.note(b0 + k * .5, .45, r + 12 * (k % 2), 108, BASS)
        drums(b0, True, last=(i in (3, 7)))
        if i in (0, 4):
            s.hit(b0, DR['crash'], 118)
        if i in (3, 7):
            s.notes(b0 + 2, 2, chord(c, 4), 92, BRS)
    # final bar: F . G . | Am
    b0 = 52
    for p, c, ln in ((0, 'F', 1.2), (1.5, 'G', 1.2), (3, 'Am', 4)):
        s.notes(b0 + p, ln, chord(c, 4), 120, HIT)
        s.notes(b0 + p, ln, chord(c, 4), 110, BRS)
        s.notes(b0 + p, ln, power(c), 118, GTR)
        s.note(b0 + p, ln, chord(c, 1)[0], 115, BASS)
        s.hit(b0 + p, DR['kick'], 124); s.hit(b0 + p, DR['crash'], 120 if p == 3 else 100)
        s.note(b0 + p, 1, chord(c, 2)[0], 120, 7)
    op_len = 14 * 4 * beat
    x = s.render(op_len, 2.4)
    return finish(x, .16, 1.8, .9, fout=.6), op_len

def m_op2():
    """OP v2 (Ep03+): same song, but a real ending — fill, then one big held A-minor chord that rings out (no stop-time stabs)."""
    bpm = 150
    s = Song(bpm, seed=3)
    beat = s.beat
    GTR, LEAD, BASS, PNO, STR, BRS, HIT = 0, 1, 2, 3, 4, 5, 6
    s.inst(GTR, P['dist'], 92, 44); s.inst(LEAD, P['od'], 104, 76); s.inst(BASS, P['pbass'], 112)
    s.inst(PNO, P['piano'], 84, 84); s.inst(STR, P['strings'], 92, 52); s.inst(BRS, P['brass'], 90, 70)
    s.inst(HIT, P['orchhit'], 110); s.inst(9, 0, 112, drums=True, kit=KIT['power'])
    s.inst(7, P['timp'], 100)
    # bar 0: hit + crash + tom fill
    s.notes(0, 1.5, chord('Am', 4), 120, HIT)
    s.notes(0, 1.5, [n2m('A2'), n2m('E3'), n2m('A3')], 120, GTR)
    s.note(0, 2, n2m('A1'), 110, BASS)
    s.hit(0, DR['crash'], 120); s.hit(0, DR['kick'], 120); s.note(0, 1, n2m('A2'), 120, 7)
    for k in range(6):
        s.hit(2 + k * .25, DR['snare'], 70 + k * 9)
    for k, tm in enumerate((DR['tom1'], DR['tom2'], DR['tom3'], DR['tom5'])):
        s.hit(3.5 + k * .125, tm, 110)
    verse = ['Am', 'F', 'G', 'E']
    chorus = ['F', 'G', 'Em', 'Am', 'F', 'G', 'E', 'Am']

    def drums(b0, full, last=False):
        for k in range(4):
            s.hit(b0 + k, DR['kick'], 112 if k % 2 == 0 else (100 if full else 0))
            if full:
                s.hit(b0 + k + .5, DR['kick'], 70 if k == 1 else 0)
            if k % 2:
                s.hit(b0 + k, DR['snare'], 112)
        for k in range(8):
            s.hit(b0 + k * .5, DR['oh'] if (full and k % 2) else DR['hh'], 82 if k % 2 else 66)
        if last:
            for k in range(4):
                s.hit(b0 + 3 + k * .25, [DR['tom1'], DR['tom2'], DR['tom3'], DR['tom5']][k], 110)

    def power(c, octave=2):
        r = chord(c, octave)[0]
        return [r, r + 7, r + 12]

    # verse: palm-muted 8th power chords + piano arps + bass
    for i, c in enumerate(verse):
        b0 = 4 + i * 4
        for k in range(8):
            s.notes(b0 + k * .5, .3, power(c), 92 if k % 4 == 0 else 74, GTR)
        cn = chord(c, 4)
        arp = [cn[0], cn[1], cn[2], cn[0] + 12, cn[2], cn[1], cn[0] + 12, cn[2]]
        for k in range(8):
            s.note(b0 + k * .5, .45, arp[k] + 12, 70, PNO)
        r = chord(c, 1)[0]
        for k in range(8):
            s.note(b0 + k * .5, .45, r + 12 * (k % 2), 100, BASS)
        drums(b0, False, last=(i == 3))
        s.notes(b0, 4, chord(c, 4), 52, STR)
    s.note(4 * 4 + 3.5, .5, n2m('E2'), 110, 7)
    # chorus
    mel = ['C5:2 C5:1 D5:1 E5:2 F5:2', 'G5:3 F5:1 E5:2 D5:2', 'E5:2 D5:1 C5:1 B4:2 G4:2', 'A4:2 C5:2 E5:4',
           'F5:2 E5:1 F5:1 G5:2 A5:2', 'B5:2 A5:1 G5:1 D5:2 G5:2', 'G#5:2 A5:1 B5:1 D6:2 B5:2', 'C6:3 B5:1 A5:4']
    for i, c in enumerate(chorus):
        b0 = 20 + i * 4
        s.mel(b0, mel[i], LEAD, 108, legato=.98)
        s.mel(b0, mel[i], STR, 86, tp=12, legato=1.0)
        s.notes(b0, 2, power(c), 104, GTR); s.notes(b0 + 2, 2, power(c), 98, GTR)
        for p in (0, .5, 1, 1.5, 2, 2.5, 3, 3.5):
            s.notes(b0 + p, .4, chord(c, 4), 64 if p % 1 else 76, PNO)
        r = chord(c, 1)[0]
        for k in range(8):
            s.note(b0 + k * .5, .45, r + 12 * (k % 2), 108, BASS)
        drums(b0, True, last=(i in (3, 7)))
        if i in (0, 4):
            s.hit(b0, DR['crash'], 118)
        if i in (3, 7):
            s.notes(b0 + 2, 2, chord(c, 4), 92, BRS)
    # ending: tom fill already closes the last chorus -> beat 52: everything lands on Am and HOLDS (lead on A5, strings tremolo,
    # timpani roll, crash), a last 'jan!' on beat 55 and the chord rings into the reverb
    b0 = 52
    s.notes(b0, 3.0, chord('Am', 4), 124, HIT)
    s.notes(b0, 7.0, chord('Am', 4) + [chord('Am', 5)[0]], 112, BRS)
    s.notes(b0, 7.0, chord('Am', 4) + [chord('Am', 5)[0]], 100, STR)
    s.notes(b0, 7.0, power('Am'), 120, GTR)
    s.note(b0, 7.0, n2m('A5'), 112, LEAD)
    s.note(b0, 7.0, n2m('A1'), 118, BASS)
    s.notes(b0, 7.0, chord('Am', 3) + chord('Am', 5), 96, PNO)
    s.hit(b0, DR['kick'], 126); s.hit(b0, DR['crash'], 124); s.hit(b0, DR['crash2'], 110)
    for k in range(16):                                   # timpani roll, swelling into the last hit
        s.note(b0 + k * .17, .2, n2m('A2'), 70 + k * 3, 7)
    s.hit(b0 + 3, DR['kick'], 126); s.hit(b0 + 3, DR['crash'], 126); s.hit(b0 + 3, DR['china'], 100)
    s.notes(b0 + 3, 4.0, chord('Am', 4), 124, HIT)
    s.note(b0 + 3, 4.0, n2m('A1'), 124, 7)
    op_len = 14 * 4 * beat
    x = s.render(op_len + 2.4, 2.4)                       # let the held chord ring past the last bar
    x = finish(x, .2, 2.4, .9)[:int(25.2 * SR)]
    n = int(1.2 * SR); x[-n:] *= np.linspace(1, 0, n)[:, None]   # the ring-out fades to silence exactly at the end
    return x, op_len

def m_tension(dur, bpm=66):
    s = Song(bpm, seed=4)
    PNO, STR, CH, TIMP, CB, CELLO, HRN = 0, 1, 2, 3, 4, 5, 6
    s.inst(PNO, P['piano'], 96, 50); s.inst(STR, P['slowstr'], 100, 70); s.inst(CH, P['choir'], 92, 64)
    s.inst(TIMP, P['timp'], 110); s.inst(CB, P['contra'], 100); s.inst(CELLO, P['cello'], 90, 40)
    s.inst(HRN, P['horns'], 84, 80)
    bars = int(math.ceil(dur / (4 * s.beat))) + 1
    prog = ['Dm', 'Bb', 'Gm', 'A7']
    for b in range(bars):
        c = prog[b % 4]; b0 = b * 4
        grow = min(1.0, b / 8)
        cn = chord(c, 3)
        arp = [cn[0], cn[1], cn[2], cn[0] + 12, cn[1] + 12, cn[2], cn[1], cn[0] + 12]
        for k in range(8):
            s.note(b0 + k * .5, .9, arp[k], 64 + int(20 * grow), PNO)
        s.notes(b0, 4, chord(c, 3)[:3], 64 + int(30 * grow), STR)
        s.note(b0, 4, chord(c, 1)[0] + 12, 90, CB)
        s.note(b0, 1, chord(c, 2)[0], 70 + int(40 * grow), TIMP)
        if b >= 2:
            top = {'Dm': 'A5', 'Bb': 'F5', 'Gm': 'G5', 'A7': 'C#6'}[c]
            s.note(b0, 4, n2m(top) - 12, 60 + int(40 * grow), CH)
            s.note(b0, 4, n2m(top) - 24, 50 + int(40 * grow), CH)
        if b >= 4:
            for k in range(8):
                s.note(b0 + k * .5, .45, chord(c, 2)[0] + (7 if k % 2 else 0), 70 + int(20 * grow), CELLO)
        if b >= 6:
            s.note(b0 + 2, 1, chord(c, 2)[0], 80, TIMP)
            s.notes(b0, 4, [chord(c, 3)[0], chord(c, 3)[2]], 70, HRN)
    x = s.render(dur, 3)
    return finish(x, .32, 2.8, .85, fin=.6, fout=1.2, dur=dur, bright=4000)

def m_hopeful(dur, bpm=72):
    s = Song(bpm, seed=5)
    PNO, STR, FL, BASS, HARP = 0, 1, 2, 3, 4
    s.inst(PNO, P['piano'], 100, 56); s.inst(STR, P['strings'], 84, 70); s.inst(FL, P['flute'], 92, 74)
    s.inst(BASS, P['contra'], 80); s.inst(HARP, P['harp'], 80, 90)
    bars = int(math.ceil(dur / (4 * s.beat))) + 1
    prog = ['F', 'G', 'Em', 'Am']
    mel = ['A5:4 G5:2 F5:2', 'G5:4 D5:4', 'E5:2 G5:2 B5:4', 'A5:6 -:2']
    for k, m in enumerate(('C5', 'F5', 'A5', 'C6', 'F6')):
        s.note(k * .12, 2, n2m(m), 70, HARP)
    for b in range(bars):
        c = prog[b % 4]; b0 = b * 4
        cn = chord(c, 4)
        s.notes(b0, 4, chord(c, 3), 70, STR)
        s.note(b0, 4, chord(c, 2)[0], 76, BASS)
        pat = [chord(c, 2)[0], cn[0], cn[1], cn[2], cn[0] + 12, cn[2], cn[1], cn[0]]
        for k in range(8):
            s.note(b0 + k * .5, .9, pat[k], 66 if k else 78, PNO)
        if b >= 4:
            s.mel(b0, mel[b % 4], FL, 84)
    x = s.render(dur, 3)
    return finish(x, .28, 2.4, .85, fin=.5, fout=.6, dur=dur)

def m_panic(dur, bpm=184):
    s = Song(bpm, seed=6)
    PZ, XY, TUBA, WH = 0, 1, 2, 3
    s.inst(PZ, P['pizz'], 110); s.inst(XY, P['xylo'], 104, 80); s.inst(TUBA, P['tuba'], 100, 50)
    s.inst(WH, P['whistle'], 90, 64); s.inst(9, 0, 100, drums=True, kit=KIT['orch'])
    total = int(dur / s.beat) + 2
    for k in range(total * 2):
        s.note(k * .5, .4, 88 - (k % 12) - 2 * ((k // 12) % 3), 96, XY)
        s.note(k * .5, .3, 64 + ((k * 5) % 12), 84, PZ)
    for k in range(total):
        s.note(k, .6, [40, 47, 43, 47][k % 4], 104, TUBA)
        s.hit(k, DR['kick'], 100)
        if k % 2:
            s.hit(k, DR['snare'], 96)
        s.hit(k + .5, DR['snare'], 50)
    # slide whistle glides
    for st in np.arange(0, dur, 1.3):
        s.note_t(st, .5, 72, 96, WH)
        for j in range(12):
            s.bend_t(st + j * .04, WH, 8192 + int(8000 * (j / 11)) * (1 if int(st) % 2 else -1))
        s.bend_t(st + .55, WH, 8192)
    x = s.render(dur, .6)
    return finish(x, .1, 1.2, .85, fout=.15, dur=dur)

def m_night(dur, bpm=68):
    s = Song(bpm, seed=7)
    MB, CEL, PAD, HARP = 0, 1, 2, 3
    s.inst(MB, P['musicbox'], 100); s.inst(CEL, P['celesta'], 70, 84); s.inst(PAD, P['warmpad'], 72); s.inst(HARP, P['harp'], 60, 40)
    mel = ['E5:2 G5:2 C6:2 B5:2', 'A5:2 G5:2 E5:4', 'F5:2 A5:2 G5:2 E5:2', 'D5:6 -:2']
    bars = int(math.ceil(dur / (4 * s.beat))) + 1
    for b in range(bars):
        c = ['C', 'Am', 'F', 'G'][b % 4]
        s.mel(b * 4, mel[b % 4], MB, 92, tp=12)
        s.notes(b * 4, 4, chord(c, 3), 54, PAD)
        cn = chord(c, 4)
        for k in range(4):
            s.note(b * 4 + k, 1, cn[k % 3] + 12, 46, CEL)
        s.note(b * 4, 2, chord(c, 2)[0], 50, HARP)
    x = s.render(dur, 3)
    x += crickets(len(x), level=.025)[:, None]
    return finish(x, .35, 2.8, .7, fin=.4, fout=.8, dur=dur)

def m_sneak(dur, bpm=104):
    s = Song(bpm, seed=8)
    PZ, BSN, CL = 0, 1, 2
    s.inst(PZ, P['pizz'], 110, 54); s.inst(BSN, P['bassoon'], 96, 72); s.inst(CL, P['clarinet'], 80, 90)
    s.inst(9, 0, 70, drums=True, kit=KIT['brush'])
    line = 'E3:1 -:1 G3:1 -:1 A3:1 -:1 A#3:1 B3:1'
    bars = int(math.ceil(dur / (4 * s.beat))) + 1
    for b in range(bars):
        s.mel(b * 4, line, PZ, 100, legato=.5)
        if b % 2:
            s.mel(b * 4, '-:5 E4:1 F4:1 E4:1', BSN, 92, legato=.6)
        else:
            s.mel(b * 4, '-:6 B4:1 A#4:1', CL, 70, legato=.6)
        s.hit(b * 4 + 1, DR['ped'], 50); s.hit(b * 4 + 3, DR['ped'], 50)
    x = s.render(dur, 1)
    return finish(x, .2, 1.6, .7, fout=.3, dur=dur)

def m_chaos(sections, bpm=168):
    """Back-to-back sections (dur, mode, transpose); boundaries are sample-accurate."""
    total = sum(d for d, _, _ in sections)
    s = Song(bpm, seed=9)
    beat = s.beat
    BASS, GTR, STR, BRS, HIT, CH, TIMP, STRH, TRP = 0, 1, 2, 3, 4, 5, 6, 7, 8
    s.inst(BASS, P['pbass'], 112); s.inst(GTR, P['dist'], 96, 40); s.inst(STR, P['strings'], 96, 70)
    s.inst(BRS, P['brass'], 100, 80); s.inst(HIT, P['orchhit'], 104); s.inst(CH, P['choir'], 88)
    s.inst(TIMP, P['timp'], 110); s.inst(STRH, P['violin'], 84, 90); s.inst(TRP, P['trumpet'], 104, 60)
    s.inst(9, 0, 112, drums=True, kit=KIT['power'])
    riff = [40, 40, 41, 40, 43, 40, 41, 38]
    t0 = 0.0
    for dur, mode, tp in sections:
        nb = int(round(dur / beat))
        T = lambda b: t0 + b * beat
        if mode in ('calm', 'stop'):
            s.alloff_t(t0)
            if mode == 'calm':
                s.note_t(t0 + .05, dur - .1, 28 + 12 + tp, 46, STR)
                s.note_t(t0 + .05, dur - .1, 28 + tp, 60, BASS)
        elif mode == 'hero':
            s.alloff_t(t0)
            fan = 'G4:1 C5:1 E5:1 G5:3 E5:1 G5:5 -:1 A5:1 B5:1 C6:1 D6:6'
            b = 0.0
            for tok in fan.split():
                nm, _, ln = tok.partition(':'); ln = float(ln) * .5
                if nm != '-':
                    k = n2m(nm) + tp
                    s.note_t(T(b), ln * beat * .95, k, 112, TRP)
                    s.note_t(T(b), ln * beat * .95, k - 12, 104, BRS)
                    s.note_t(T(b), ln * beat * .95, k - 5, 96, BRS)
                b += ln
            for k in range(nb * 4):
                s.note_t(T(k * .25), .1, DR['snare'], 50 + int(70 * k / (nb * 4)), 9)
            for k in range(nb):
                s.note_t(T(k), .2, DR['kick'], 110, 9)
                s.note_t(T(k), beat, 36 + tp + (0 if k < nb / 2 else 7), 100, BASS)
                s.note_t(T(k), beat * .9, 40 + tp + (0 if k < nb / 2 else 7), 104, TIMP)
            s.note_t(T(0), .3, DR['crash'], 120, 9)
            s.notes(0, 0, [], 0, STR)
            s.note_t(T(0), dur, 48 + tp, 90, STR); s.note_t(T(0), dur, 55 + tp, 90, STR); s.note_t(T(0), dur, 64 + tp, 90, STR)
        else:
            lvl = mode
            if t0 > 0:
                s.alloff_t(t0)
            for k in range(nb * 2):
                key = riff[k % 8] + tp
                s.note_t(T(k * .5), .45 * beat, key, 108, BASS)
                if lvl >= 1:
                    s.note_t(T(k * .5), .4 * beat, key + 12, 76 + 10 * (lvl >= 3), STR)
                if lvl >= 2:
                    s.note_t(T(k * .5), .4 * beat, key + 12, 90, GTR); s.note_t(T(k * .5), .4 * beat, key + 19, 86, GTR)
            for k in range(nb):
                s.note_t(T(k), .2, DR['kick'], 116, 9)
                if lvl >= 4:
                    s.note_t(T(k + .5), .2, DR['kick'], 100, 9)
                if lvl >= 2 and k % 2:
                    s.note_t(T(k), .2, DR['snare'], 118, 9)
                s.note_t(T(k), .1, DR['hh'], 80, 9); s.note_t(T(k + .5), .1, DR['oh' if lvl >= 3 else 'hh'], 70, 9)
                if lvl >= 3 and k % 4 == 0:
                    s.note_t(T(k), .3, DR['crash'], 110, 9)
                    s.note_t(T(k), .4, riff[0] + tp + 12, 112, HIT); s.note_t(T(k), .4, riff[0] + tp + 19, 112, HIT)
                if lvl >= 3 and k % 4 == 2:
                    s.note_t(T(k + .5), beat * .4, 52 + tp, 104, BRS); s.note_t(T(k + .5), beat * .4, 59 + tp, 104, BRS)
            if lvl >= 4:
                for k in range(nb * 4):
                    s.note_t(T(k * .25), .22 * beat, (71 if (k // 2) % 2 else 72) + tp + 12 * ((k // 16) % 2), 80, STRH)
                b = 0
                while b < nb:
                    for tok in 'E5:2 F5:2 G5:2 A#5:2 B5:4 A#5:2 G5:2'.split():
                        nm, _, ln = tok.partition(':'); ln = float(ln) * .5
                        if b < nb:
                            s.note_t(T(b), ln * beat * .95, n2m(nm) + tp, 108, TRP)
                        b += ln
                    b = math.ceil(b)
                s.note_t(T(0), dur, 64 + tp, 80, CH); s.note_t(T(0), dur, 71 + tp, 80, CH)
        t0 += dur
    x = s.render(total, 0)
    n = int(round(total * SR))
    x = x[:n]
    # crickets in calm sections, and keep each section's boundary sharp
    t0 = 0.0
    for dur, mode, tp in sections:
        i, j = int(round(t0 * SR)), int(round((t0 + dur) * SR))
        if mode == 'calm':
            x[i:j] += crickets(j - i, level=.035)[:, None]
        if mode == 'stop':
            x[i:j] = 0
        t0 += dur
    y = reverb(x, .12, 1.4)[:n]
    return norm(soft(norm(y, 1.0), 1.4), .9)

def m_ed(dur, bpm=88):
    s = Song(bpm, seed=10)
    beat = s.beat
    GT, PNO, STR, BASS, FL = 0, 1, 2, 3, 4
    s.inst(GT, P['steel'], 96, 44); s.inst(PNO, P['piano'], 90, 74); s.inst(STR, P['strings'], 76, 64)
    s.inst(BASS, P['fbass'], 96); s.inst(FL, P['flute'], 100, 70); s.inst(9, 0, 80, drums=True, kit=KIT['brush'])
    cyc = ['D', 'A', 'Bm', 'F#m', 'G', 'D', 'G', 'A']
    mel = ['F#5:2 E5:2 D5:2 E5:2', 'C#5:4 E5:4', 'D5:2 C#5:2 B4:2 C#5:2', 'A4:4 C#5:4',
           'B4:2 D5:2 G5:2 F#5:2', 'F#5:4 A5:4', 'G5:2 F#5:2 E5:2 D5:2', 'E5:6 C#5:2']
    bar = 4 * beat
    nb = max(4, int(round((dur - 2.0) / bar)))
    for i in range(nb):
        last = i == nb - 1
        c = 'D' if last else cyc[i % 8]
        b0 = i * 4
        cn = chord(c, 3)
        pat = [cn[0], cn[2], cn[1] + 12, cn[2], cn[0] + 12, cn[2], cn[1] + 12, cn[2]]
        if not last:
            for k in range(8):
                s.note(b0 + k * .5, 1.2, pat[k], 70, GT)
            s.notes(b0, 4, chord(c, 4), 52, PNO)
            s.note(b0, 3.8, chord(c, 1)[0] + 12, 90, BASS)
            s.notes(b0, 4, chord(c, 4), 56 + min(30, i * 4), STR)
            if i >= 1:
                s.hit(b0, DR['kick'], 70); s.hit(b0 + 2.5, DR['kick'], 56)
                s.hit(b0 + 1, DR['snare'], 52); s.hit(b0 + 3, DR['snare'], 52)
                for k in range(8):
                    s.hit(b0 + k * .5, DR['hh'], 40)
            s.mel(b0, mel[i % 8], FL, 90)
        else:
            s.notes(b0, 6, [n2m('D3'), n2m('A3'), n2m('D4'), n2m('F#4'), n2m('A4')], 76, GT, strum=.05)
            s.notes(b0, 6, chord('D', 4), 64, PNO); s.notes(b0, 6, chord('D', 4), 70, STR)
            s.note(b0, 6, n2m('D2'), 90, BASS); s.note(b0, 4, n2m('F#5'), 80, FL)
            s.note(b0 + 2, 3, n2m('D6'), 60, PNO)
    x = s.render(dur, 1)
    return finish(x, .26, 2.4, .85, fin=.2, fout=1.6, dur=dur)

def m_eyecatch():
    s = Song(120, seed=11)
    s.inst(0, P['glock'], 110); s.inst(1, P['harp'], 90); s.inst(2, P['strings'], 80); s.inst(3, P['celesta'], 90)
    for i, m in enumerate(('C5', 'E5', 'G5', 'C6', 'E6', 'G6')):
        s.note_t(i * .07, .5, n2m(m), 90, 1)
    for i, m in enumerate(('G5', 'C6', 'E6')):
        s.note_t(.45 + i * .1, .4, n2m(m), 100, 0)
    s.note_t(.8, 1.5, n2m('G6'), 112, 0); s.note_t(.8, 1.5, n2m('C6'), 90, 3)
    s.notes(0, 0, [], 0, 2)
    for m in chord('Cmaj7', 4):
        s.note_t(.8, 1.6, m, 70, 2)
    x = s.render(2.6, 0)
    return finish(x, .3, 2.0, .8, fout=.5, dur=2.6)

def m_preview(dur):
    s = Song(150, seed=12)
    LEAD, GTR, BASS, STR = 0, 1, 2, 3
    s.inst(LEAD, P['od'], 104, 76); s.inst(GTR, P['dist'], 90, 44); s.inst(BASS, P['pbass'], 110)
    s.inst(STR, P['strings'], 90); s.inst(9, 0, 108, drums=True, kit=KIT['power'])
    mel = ['F5:2 E5:1 F5:1 G5:2 A5:2', 'B5:2 A5:1 G5:1 D5:2 G5:2', 'G#5:2 A5:1 B5:1 D6:2 B5:2', 'C6:3 B5:1 A5:4']
    for i, c in enumerate(['F', 'G', 'E', 'Am']):
        b0 = i * 4
        s.mel(b0, mel[i], LEAD, 108); s.mel(b0, mel[i], STR, 80, tp=12)
        r = chord(c, 2)[0]
        s.notes(b0, 2, [r, r + 7, r + 12], 100, GTR); s.notes(b0 + 2, 2, [r, r + 7, r + 12], 96, GTR)
        for k in range(8):
            s.note(b0 + k * .5, .45, r - 12 + 12 * (k % 2), 104, BASS)
        for k in range(4):
            s.hit(b0 + k, DR['kick'], 112)
            if k % 2:
                s.hit(b0 + k, DR['snare'], 110)
            s.hit(b0 + k + .5, DR['oh'], 70)
        if i == 0:
            s.hit(0, DR['crash'], 116)
    x = s.render(dur, 1)
    return finish(x, .16, 1.8, .88, fout=.8, dur=dur)

def m_cliff():
    s = Song(60, seed=13)
    s.inst(0, P['orchhit'], 120); s.inst(1, P['timp'], 120); s.inst(2, P['brass'], 110); s.inst(3, P['bells'], 110)
    s.inst(4, P['contra'], 110); s.inst(5, P['strings'], 100); s.inst(9, 0, 120, drums=True, kit=KIT['orch'])
    for m in chord('Ab', 3) + chord('A', 4):
        s.note_t(0, 1.6, m, 124, 0)
    for m in [n2m('A1'), n2m('E2'), n2m('A2')]:
        s.note_t(0, 2.2, m, 120, 2); s.note_t(0, 3.0, m + 12, 110, 4)
    s.note_t(0, 2.5, n2m('A2'), 127, 1)
    for k in range(10):
        s.note_t(.6 + k * .06, .1, n2m('A2'), 70 - k * 4, 1)
    s.note_t(0, 1, DR['crash'], 127, 9)
    s.note_t(0, 2.2, n2m('A#4'), 70, 5); s.note_t(0, 2.2, n2m('A4'), 70, 5)  # dissonant cluster
    for i, m in enumerate(('E5', 'D#5', 'A4')):
        s.note_t(2.3 + i * .38, 1.5, n2m(m), 110, 3)
    x = s.render(4.5, 0)
    return finish(x, .35, 3.0, .92, fout=.6, dur=4.5)

def m_shout_sting():
    s = Song(60, seed=14)
    s.inst(0, P['orchhit'], 120); s.inst(1, P['timp'], 120); s.inst(2, P['brass'], 115); s.inst(9, 0, 120, drums=True, kit=KIT['orch'])
    for m in chord('Cm', 4):
        s.note_t(0, .9, m, 124, 0)
    for m in chord('Cm', 3) + [n2m('C2'), n2m('F#4')]:
        s.note_t(0, 1.2, m, 118, 2)
    s.note_t(0, 1.5, n2m('C2'), 127, 1); s.note_t(0, 1, DR['crash'], 120, 9)
    x = s.render(2.0, 0)
    return finish(x, .3, 2.2, .9, fout=.4, dur=2.0)

# ======================================================================= SFX
def _sf_one(prog, notes, dur, vel=110, drums=False, kit=0, bends=None, tail=.5):
    """notes: list of (t, dur, key[, vel])."""
    s = Song(120)
    s.inst(0 if not drums else 9, prog, 120, drums=drums, kit=kit)
    ch = 9 if drums else 0
    for nt in notes:
        t, d, k = nt[:3]
        v = nt[3] if len(nt) > 3 else vel
        s.note_t(t, d, k, v, ch, human=False)
    for t, val in (bends or []):
        s.bend_t(t, ch, val)
    return mono(s.render(dur, tail))

def _thump(n, f0=120, f1=40, tau=.12, k=25):
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * k)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / tau)

def _click(n, f=2500, tau=.004, seed=0, q=.3):
    t = np.arange(n) / SR
    x = bandpass(noise(n, seed), f * (1 - q), f * (1 + q)) * np.exp(-t / tau) * 4
    x += np.sin(2 * np.pi * f * t) * np.exp(-t / (tau * 3)) * .5
    return x

def _sweep_noise(n, f0, f1, seed=0, bands=10):
    """Noise whose band centre glides from f0 to f1 (crossfaded filter bank, no block clicks)."""
    x = noise(n, seed)
    pos = np.linspace(0, bands - 1, n)
    out = np.zeros(n)
    for b in range(bands):
        fc = f0 * (f1 / f0) ** (b / (bands - 1))
        w = np.clip(1 - np.abs(pos - b), 0, 1)
        out += bandpass(x, fc * .6, fc * 1.6) * w
    return out

def _rev(x, mix=.3, length=1.6):
    y = mono(reverb(np.stack([x, x], 1), mix, length))
    return y

def _fit(x, peak=.8):
    return norm(x, peak)

def sfx(name, seed=0):
    n_ = lambda s: int(s * SR)
    if name == 'step':
        n = n_(.18)
        x = _thump(n, 110, 50, .05) * .8 + bandpass(noise(n, seed), 300, 2500) * env_exp(n, .02) * .5
        return _fit(x, .7)
    if name == 'tiptoe':
        n = n_(.12)
        x = _click(n, 1800, .006, seed) * .5 + _thump(n, 300, 150, .02) * .2
        return _fit(x, .35)
    if name == 'slam':
        n = n_(1.4)
        t = np.arange(n) / SR
        x = _thump(n, 90, 38, .35, 12) * 1.2
        x += bandpass(noise(n, 21), 150, 3000) * env_exp(n, .05) * 1.2
        x += bandpass(noise(n, 22), 2000, 6000) * env_exp(n, .015)
        rattle = bandpass(noise(n, 23), 800, 2500) * (np.sin(2 * np.pi * 34 * t) > .3) * np.exp(-t * 6) * .3
        x += rattle
        return _fit(_rev(x, .5, 2.2), .95)
    if name == 'creak':
        n = n_(1.1)
        t = np.arange(n) / SR
        f = 26 + 10 * np.sin(t * 5) + 6 * np.sin(t * 13)
        ph = np.cumsum(f) / SR
        pulses = (np.diff(np.floor(ph), prepend=0) > 0).astype(float)
        body = lfilter([1], [1, -1.6 * math.cos(2 * math.pi * 900 / SR), .81], pulses)
        body += lfilter([1], [1, -1.7 * math.cos(2 * math.pi * 1700 / SR), .86], pulses) * .6
        x = body * np.sin(np.pi * np.clip(t / 1.1, 0, 1)) ** .5
        return _fit(_rev(x, .3), .45)
    if name == 'surprise':  # anime 'ジャン!' reaction stab
        a = _sf_one(P['orchhit'], [(0, .3, n2m('E5')), (0, .3, n2m('B5'))], .6, 120)
        b = _sf_one(0, [(0, .3, DR['splash'])], .6, 110, drums=True)
        c = _sf_one(P['glock'], [(0, .3, n2m('B6')), (.06, .4, n2m('E7'))], .6, 110)
        m = min(len(a), len(b), len(c))
        return _fit(a[:m] + b[:m] * .6 + c[:m] * .5, .75)
    if name in ('question', 'boing'):
        n = n_(.6)
        t = np.arange(n) / SR
        base = 180 if name == 'boing' else 260
        f = base * (1 + .5 * np.exp(-t * 6) * np.sin(2 * np.pi * 14 * t)) * (1 + (.6 if name == 'question' else 0) * t)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4)
        x += np.sin(4 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8) * .25
        return _fit(x, .5)
    if name == 'puff':
        n = n_(.9)
        t = np.arange(n) / SR
        return _fit(bandpass(noise(n, 7), 200, 1600) * np.sin(np.pi * t / .9) ** 1.5, .4)
    if name == 'smoke':
        n = n_(1.6)
        t = np.arange(n) / SR
        x = bandpass(noise(n, 31), 600, 5000) * np.sin(np.pi * t / 1.6) ** 2
        return _fit(x, .3)
    if name == 'cards':
        out = np.zeros(n_(.8))
        rnd = random.Random(seed)
        for i in range(18):
            i0 = int((i * .035 + rnd.uniform(0, .01)) * SR)
            c = _click(900, rnd.uniform(2500, 4500), .003, seed + i) * rnd.uniform(.4, .8)
            out[i0:i0 + 900] += c[:len(out) - i0]
        return _fit(out, .5)
    if name == 'sparkle':
        notes = [(i * .05, .6, n2m(m), 100) for i, m in enumerate(('E6', 'G#6', 'B6', 'E7', 'G#7'))]
        a = _sf_one(P['celesta'], notes, 1.0, 100)
        b = _sf_one(0, [(0, 1, DR['chimes'])], 1.0, 100, drums=True)
        m = min(len(a), len(b))
        return _fit(_rev(a[:m] + b[:m] * .6, .4), .55)
    if name == 'glint':
        n = n_(.7)
        t = np.arange(n) / SR
        f = 2500 + 5500 * np.clip(t / .12, 0, 1)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) * .5
        tri = _sf_one(0, [(0, .6, DR['mtri'])], .7, 120, drums=True)
        m = min(len(x), len(tri))
        return _fit(_rev(x[:m] * .5 + tri[:m], .35), .5)
    if name == 'don':
        a = _sf_one(P['taiko'], [(0, 1, n2m('C2'), 127)], 1.6)
        b = _sf_one(P['timp'], [(0, 1, n2m('C2'), 127)], 1.6)
        n = min(len(a), len(b))
        x = a[:n] + b[:n] + _thump(n, 80, 35, .4, 10) * .5
        return _fit(_rev(x, .35, 2.0), .9)
    if name == 'impact':
        n = n_(2.4)
        t = np.arange(n) / SR
        x = _thump(n, 140, 30, .6, 9) * 1.3
        x += lowpass(noise(n, 41), 900) * np.exp(-t * 5) * .8
        x += bandpass(noise(n, 42), 2000, 8000) * np.exp(-t * 20) * .5
        return _fit(_rev(x, .6, 2.8), .95)
    if name == 'whoosh':
        n = n_(.55)
        t = np.arange(n) / SR
        x = _sweep_noise(n, 300, 5000, 13) * np.sin(np.pi * t / .55) ** 2
        return _fit(x, .5)
    if name == 'bleep':
        n = n_(.5)
        x = np.sin(2 * np.pi * 1000 * np.arange(n) / SR)
        e = np.ones(n); e[:200] = np.linspace(0, 1, 200); e[-200:] = np.linspace(1, 0, 200)
        return x * e * .32
    if name == 'rumble':
        n = n_(3.0)
        t = np.arange(n) / SR
        return _fit(lowpass(noise(n, 14), 110) * np.clip(t, 0, 1) * np.clip(3 - t, 0, 1), .7)
    if name == 'gogo':
        n = n_(2.6)
        t = np.arange(n) / SR
        a = _sf_one(P['contra'], [(0, 2.4, n2m('C1'), 110), (0, 2.4, n2m('C#1'), 100)], 2.6, tail=0)
        rum = lowpass(noise(n, 18), 90) * 2
        m = min(len(a), n)
        x = a[:m] * 1.2 + rum[:m]
        x *= np.clip(t[:m] * 2, 0, 1) * np.clip((2.6 - t[:m]) * 2, 0, 1)
        return _fit(x, .75)
    if name == 'tap':
        n = n_(1.6)
        t = np.arange(n) / SR
        click = _click(n, 1800, .006, 51) + _click(n, 3600, .003, 52) * .6
        clunk = _thump(n, 160, 60, .05, 40) * .7
        sub = _thump(n, 70, 32, .5, 6) * 1.1
        shimmer = _sf_one(P['choir'], [(.05, 1.2, n2m('F#6'), 70), (.05, 1.2, n2m('C7'), 60)], 1.6, tail=0)
        rc = _sf_one(0, [(0, 1, DR['china'], 60)], 1.6, drums=True, tail=0)
        m = min(n, len(shimmer), len(rc))
        x = click[:m] * .8 + clunk[:m] + sub[:m] + shimmer[:m] * .5 * np.exp(-t[:m] * 2) + rc[:m] * .15
        return _fit(_rev(x, .3, 2.0), .95)
    if name == 'untap':
        n = n_(.7)
        t = np.arange(n) / SR
        click = _click(n, 3200, .003, 61) * .8 + _thump(n, 400, 200, .02, 60) * .4
        rw = _sweep_noise(n, 5000, 600, 62) * (t / .7) ** 2 * np.exp(-((t - .5) / .12) ** 2) * .6
        return _fit(click + rw, .7)
    if name == 'spawn':
        n = n_(1.4)
        t = np.arange(n) / SR
        swirl = _sweep_noise(n, 200, 3000, 71) * np.sin(np.pi * np.clip(t / .7, 0, 1)) * (1 + .5 * np.sin(2 * np.pi * 9 * t)) * .7
        pop = np.sin(2 * np.pi * np.cumsum(500 * np.exp(-np.clip(t - .55, 0, None) * 18) + 90) / SR) * np.exp(-np.clip(t - .55, 0, None) * 12) * (t > .55)
        growl_f = 55 + 15 * np.sin(t * 31) + 8 * np.sin(t * 7)
        growl = lowpass(np.sign(np.sin(2 * np.pi * np.cumsum(growl_f) / SR)) * .5 + noise(n, 72) * .5, 450) * np.clip((t - .6) * 6, 0, 1) * np.exp(-np.clip(t - .6, 0, None) * 2.5)
        x = swirl + pop * .9 + growl * 1.2
        return _fit(_rev(x, .3), .9)
    if name == 'alarm':
        n = n_(1.6)
        t = np.arange(n) / SR
        f = 750 + 450 * (.5 + .5 * np.sin(2 * np.pi * 1.25 * t - np.pi / 2))
        ph = np.cumsum(f) / SR
        x = np.sin(2 * np.pi * ph) + .3 * np.sin(4 * np.pi * ph) + .15 * np.sin(6 * np.pi * ph)
        return _fit(_rev(soft(x, 1.5), .25), .45)
    if name == 'scratch':
        n = n_(.5)
        t = np.arange(n) / SR
        speed = np.sin(2 * np.pi * 3.2 * t) * np.exp(-t * 2)
        src = bandpass(noise(n, 17), 200, 4000)
        idx = np.clip((np.cumsum(np.abs(speed)) * 1.8).astype(int), 0, n - 1)
        x = src[idx] * np.abs(speed)
        return _fit(x, .55)
    if name == 'drop':  # sweat drop 'pochan'
        n = n_(.5)
        t = np.arange(n) / SR
        f = 900 + 1400 * np.clip(t / .05, 0, 1)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18)
        return _fit(_rev(x, .3, 1.2), .45)
    if name == 'heartbeat':
        n = n_(.65)
        x = _thump(n, 80, 38, .09, 30)
        i = int(.22 * SR)
        x[i:] += _thump(n - i, 70, 36, .08, 30) * .7
        return _fit(lowpass(x, 300), .8)
    if name == 'snore':
        n = n_(1.4)
        t = np.arange(n) / SR
        rattle = 1 + .8 * np.sin(2 * np.pi * 32 * t)
        x = bandpass(noise(n, 19), 120, 700) * np.sin(np.pi * t / 1.4) ** 2 * rattle
        return _fit(x, .35)
    if name == 'thud':
        n = n_(.5)
        x = _thump(n, 100, 45, .1, 25) + lowpass(noise(n, 5), 500) * env_exp(n, .03) * .5
        return _fit(x, .7)
    if name == 'zap':
        n = n_(.45)
        t = np.arange(n) / SR
        crack = highpass(noise(n, 81), 1500) * (np.random.default_rng(82).random(n) > .85) * np.exp(-t * 6)
        buzz = bandpass(noise(n, 83), 2000, 6000) * (np.sin(2 * np.pi * 60 * t) > 0) * np.exp(-t * 7)
        return _fit(crack + buzz * .6, .5)
    if name == 'flashback':
        notes = [(i * .035, .8, k, 90) for i, k in enumerate(range(n2m('C5'), n2m('C7'), 2))]
        a = _sf_one(P['harp'], notes, 1.8, 95)
        b = _sf_one(0, [(0, 1.5, DR['chimes'])], 1.8, 100, drums=True)
        m = min(len(a), len(b))
        return _fit(_rev(a[:m] + b[:m] * .7, .5, 2.4), .6)
    if name == 'tick':
        a = _sf_one(0, [(0, .1, DR['wood_hi'], 100), (.5, .1, DR['wood_lo'], 90)], 1.0, drums=True, tail=0)
        return _fit(a, .5)
    if name == 'crowd_panic':
        n = n_(2.6)
        t = np.arange(n) / SR
        out = np.zeros(n)
        rnd = random.Random(seed + 5)
        forms = [(700, 1200), (400, 2000), (300, 2500), (600, 1000), (500, 1700)]
        for v in range(14):
            f0 = rnd.uniform(140, 320)
            con = f0 * (1 + .25 * np.sin(2 * np.pi * rnd.uniform(2, 5) * t + v) + .15 * np.sin(2 * np.pi * rnd.uniform(.5, 1.5) * t))
            ph = np.cumsum(con) / SR
            glott = (ph % 1.0) ** 3 - .25
            f1, f2 = forms[v % len(forms)]
            voice = bandpass(glott, f1 * .7, f1 * 1.3) + bandpass(glott, f2 * .8, f2 * 1.2) * .6
            gate = np.clip(np.sin(2 * np.pi * rnd.uniform(1.5, 4) * t + rnd.uniform(0, 6)) * 2, 0, 1)
            out += voice * gate * rnd.uniform(.5, 1)
        out *= np.clip(t * 3, 0, 1) * np.clip((2.6 - t) * 3, 0, 1)
        return _fit(_rev(out, .35), .6)
    if name == 'monster_run':
        n = n_(1.6)
        out = np.zeros(n)
        rnd = random.Random(seed + 9)
        tt = 0.0
        while tt < 1.45:
            i0 = int(tt * SR)
            s_ = _thump(n_(.08), rnd.uniform(120, 220), 60, .03, 40) * rnd.uniform(.4, .9) + _click(n_(.08), rnd.uniform(900, 1600), .004, rnd.randint(0, 999)) * .3
            out[i0:i0 + len(s_)] += s_[:n - i0]
            tt += rnd.uniform(.05, .11)
        for k in range(3):
            i0 = int(rnd.uniform(.1, 1.2) * SR)
            m = n_(.15); tq = np.arange(m) / SR
            sq = np.sin(2 * np.pi * np.cumsum(1800 + 900 * np.sin(tq * 40)) / SR) * np.exp(-tq * 20) * .25
            out[i0:i0 + m] += sq[:n - i0]
        return _fit(out, .6)
    if name == 'crash':
        n = n_(1.2)
        t = np.arange(n) / SR
        rnd = random.Random(seed + 4)
        x = highpass(noise(n, 91), 2500) * np.exp(-t * 9) * .8
        for k in range(26):
            i0 = int(rnd.uniform(0, .45) * SR)
            m = n_(.25); tq = np.arange(m) / SR
            ping = np.sin(2 * np.pi * rnd.uniform(3000, 9000) * tq) * np.exp(-tq * rnd.uniform(15, 40)) * rnd.uniform(.1, .35)
            x[i0:i0 + m] += ping[:n - i0]
        x += _thump(n, 200, 90, .04, 40) * .4
        return _fit(_rev(x, .25), .7)
    raise KeyError(name)

SFX_NAMES = ['step', 'tiptoe', 'slam', 'creak', 'surprise', 'question', 'puff', 'cards', 'sparkle', 'glint', 'don',
             'impact', 'whoosh', 'bleep', 'rumble', 'gogo', 'tap', 'untap', 'spawn', 'alarm', 'scratch', 'drop',
             'heartbeat', 'boing', 'snore', 'thud', 'zap', 'flashback', 'tick', 'crowd_panic', 'monster_run',
             'crash', 'smoke']


# ======================================================================= EPISODE 2 additions
# (appended; Ep01 cues/sfx above are untouched)
P2 = dict(organ=19, reedorgan=20, marimba=12, kalimba=108, panflute=75, slapbass=36, synbass=38, cleangtr=27,
          mutegtr=28, tubular=14, tremstr=44, halo=94, sweep=95, ooh=53, synvoice=54, tinkle=112, trombone=57,
          altosax=65, timp=47, frhorn=60, eguitar_jazz=26)

def _bars(dur, bpm, beats=4):
    return int(math.ceil(dur / (beats * 60.0 / bpm))) + 1

def _ramp_cc(s, ch, t0, t1, v0, v1, steps=24, cc=11):
    for i in range(steps + 1):
        k = i / steps
        s.cc_t(t0 + (t1 - t0) * k, ch, cc, v0 + (v1 - v0) * k)

def _bitcrush(x, hold=8, bits=4):
    """Sample-and-hold rate reduction + amplitude quantisation (digital 'BTC' glitch)."""
    y = x.copy()
    n = len(y)
    idx = (np.arange(n) // hold) * hold
    y = y[np.minimum(idx, n - 1)]
    q = 2 ** (bits - 1)
    return np.round(y * q) / q

def _glitch_gate(n, seed=0, rate=3.0, duty=.35):
    rnd = np.random.default_rng(seed)
    g = np.zeros(n)
    pos = 0
    while pos < n:
        seg = int(rnd.uniform(.03, .25) * SR)
        if rnd.random() < duty:
            g[pos:pos + seg] = 1.0
        pos += seg + int(rnd.uniform(0, 1 / rate) * SR)
    return lowpass(g, 400)

def _section_render(s, sections, rev=.15, rlen=1.6):
    total = sum(d for d, _ in sections)
    x = s.render(total, 0)
    n = int(round(total * SR))
    x = x[:n]
    if len(x) < n:
        x = np.concatenate([x, np.zeros((n - len(x), 2))])
    y = reverb(x, rev, rlen)[:n]
    return y, n

# ----------------------------------------------------------------------- recap
def m_recap(dur, bpm=140):
    s = Song(bpm, seed=21)
    PNO, STR, VLN, BASS, HIT, TIMP = 0, 1, 2, 3, 4, 5
    s.inst(PNO, P['piano'], 108, 50); s.inst(STR, P['strings'], 92, 76); s.inst(VLN, P['violin'], 96, 90)
    s.inst(BASS, P['fbass'], 104); s.inst(HIT, P['orchhit'], 118); s.inst(TIMP, P['timp'], 116)
    s.inst(9, 0, 104, drums=True, kit=KIT['standard'])
    # opening sting
    for m in chord('Dm', 4) + [n2m('D3')]:
        s.note_t(0, .6, m, 124, HIT)
    s.note_t(0, 1.2, n2m('D2'), 124, TIMP); s.note_t(0, .5, DR['crash'], 118, 9)
    prog = ['Dm', 'Bb', 'C', 'A']
    start = 4  # beats after the sting
    bars = _bars(dur, bpm)
    mel = ['A5:3 G5:1 F5:2 E5:2', 'D5:4 F5:2 A5:2', 'G5:3 F5:1 E5:2 G5:2', 'E5:6 C#5:2']
    for b in range(bars):
        b0 = start + b * 4
        c = prog[b % 4]
        cn = chord(c, 4)
        arp = [cn[0] - 12, cn[1] - 12, cn[2] - 12, cn[0], cn[2] - 12, cn[1] - 12, cn[0], cn[2]]
        for k in range(8):
            s.note(b0 + k * .5, .45, arp[k], 92 if k % 2 else 104, PNO)
        s.notes(b0, 3.9, chord(c, 3), 78, STR)
        r = chord(c, 2)[0]
        for k in range(4):
            s.note(b0 + k, .9, r, 100, BASS)
        s.hit(b0, DR['kick'], 96); s.hit(b0 + 2, DR['kick'], 90)
        s.hit(b0 + 1, DR['snare'], 70); s.hit(b0 + 3, DR['snare'], 74)
        for k in range(8):
            s.hit(b0 + k * .5, DR['hh'], 52 if k % 2 else 64)
        if b >= 2:
            s.mel(b0, mel[b % 4], VLN, 96)
        if b % 4 == 0 and b:
            s.hit(b0, DR['crash'], 90)
    x = s.render(dur, 0)
    return finish(x, .2, 2.0, .9, fout=min(1.5, dur * .2), dur=dur)

# ----------------------------------------------------------------------- the demon reveal
def m_demon(sections):
    """sections: list of (dur, mode) with modes stuck|orbit|flames|rise|reveal|hold; sample-accurate boundaries."""
    s = Song(60, seed=31)
    ORG, CH, BRS, TIMP, TREM, HARP, STR, HIT, CB, TRB = 0, 1, 2, 3, 4, 5, 6, 7, 8, 10
    s.inst(ORG, P2['organ'], 110); s.inst(CH, P['choir'], 104); s.inst(BRS, P['brass'], 108, 74)
    s.inst(TIMP, P['timp'], 120); s.inst(TREM, P2['tremstr'], 104, 84); s.inst(HARP, P['harp'], 108, 40)
    s.inst(STR, P['strings'], 96, 64); s.inst(HIT, P['orchhit'], 124); s.inst(CB, P['contra'], 110)
    s.inst(TRB, P2['trombone'], 110, 56)
    s.inst(9, 0, 110, drums=True, kit=KIT['orch'])
    chans = (ORG, CH, BRS, TIMP, TREM, HARP, STR, HIT, CB, TRB)
    t0 = 0.0
    for dur, mode in sections:
        s.alloff_t(t0)
        for ch in chans:
            s.cc_t(t0, ch, 11, 127)
        if mode == 'stuck':
            _ramp_cc(s, TREM, t0, t0 + dur, 50, 120)
            for m in (n2m('A5'), n2m('Bb5'), n2m('E6')):
                s.note_t(t0 + .02, dur - .05, m, 96, TREM)
            k = 0
            while k * .25 < dur - .05:
                s.note_t(t0 + k * .25, .05, DR['wood_hi'] if k % 2 else DR['wood_lo'], 100, 9)
                k += 1
            s.note_t(t0 + .02, dur - .05, n2m('D2'), 70, CB)
        elif mode == 'orbit':
            arp = [n2m(x) for x in ('D4', 'F4', 'A4', 'C#5', 'D5', 'C#5', 'A4', 'F4')]
            k = 0
            while k * .11 < dur - .05:
                s.note_t(t0 + k * .11, .3, arp[k % 8] + (12 if (k // 8) % 2 else 0), 96, HARP)
                k += 1
            k = 0
            while k * .5 < dur - .05:
                s.note_t(t0 + k * .5, .45, [n2m('D3'), n2m('Eb3'), n2m('D3'), n2m('C#3')][k % 4], 92, STR)
                k += 1
            s.note_t(t0 + .02, dur - .05, n2m('D1') + 12, 104, CB)
        elif mode == 'flames':
            for m in (n2m('D3'), n2m('A3'), n2m('F4'), n2m('Eb4')):
                s.note_t(t0 + .02, dur - .05, m, 100, CH)
            s.note_t(t0 + .02, dur - .05, n2m('D2'), 110, CB)
            k = 0
            while k * .07 < dur - .05:
                s.note_t(t0 + k * .07, .1, n2m('D2'), int(50 + 70 * (k * .07) / dur), TIMP)
                k += 1
        elif mode == 'rise':
            # the same rise replayed: every repetition restarts the crescendo soft -> huge
            for ch in (ORG, CH, BRS, TRB, STR):
                _ramp_cc(s, ch, t0, t0 + dur, 22, 127)
            for m in chord('Dm', 3) + [n2m('D2'), n2m('A4'), n2m('D5')]:
                s.note_t(t0 + .02, dur - .04, m, 112, ORG)
            for m in (n2m('D4'), n2m('F4'), n2m('A4')):
                s.note_t(t0 + .02, dur - .04, m, 110, CH)
            s.note_t(t0 + .02, dur - .04, n2m('D2'), 118, TRB); s.note_t(t0 + .02, dur - .04, n2m('A2'), 112, BRS)
            s.note_t(t0 + .02, dur - .04, n2m('D3'), 104, STR)
            k = 0
            while k * .06 < dur - .05:
                s.note_t(t0 + k * .06, .08, n2m('D2'), int(40 + 85 * (k * .06) / dur), TIMP)
                k += 1
        elif mode == 'reveal':
            for m in chord('Dm', 4) + [n2m('Eb4')]:
                s.note_t(t0, .7, m, 127, HIT)
            for m in chord('Dm', 3) + [n2m('D2'), n2m('Eb3'), n2m('A4'), n2m('D5')]:
                s.note_t(t0, dur - .05, m, 124, ORG)
            for m in (n2m('D3'), n2m('A3'), n2m('D4'), n2m('F4')):
                s.note_t(t0, dur - .05, m, 120, CH)
            s.note_t(t0, dur * .8, n2m('D2'), 127, TRB); s.note_t(t0, dur * .8, n2m('D3'), 124, BRS)
            s.note_t(t0, 1.5, n2m('D2'), 127, TIMP)
            s.note_t(t0, .5, DR['crash'], 127, 9); s.note_t(t0 + .01, .5, DR['crash2'], 120, 9)
        elif mode == 'hold':
            _ramp_cc(s, ORG, t0, t0 + dur, 110, 70)
            for m in (n2m('D2'), n2m('Ab2'), n2m('D3'), n2m('F3')):
                s.note_t(t0 + .02, dur - .04, m, 96, ORG)
            s.note_t(t0 + .02, dur - .04, n2m('D3'), 80, CH)
        t0 += dur
    y, n = _section_render(s, sections, .2, 2.4)
    # each 'rise' replay restarts audibly soft -> huge (also swallows the previous section's tail)
    t0 = 0.0
    for dur, mode in sections:
        i, j = int(round(t0 * SR)), int(round((t0 + dur) * SR))
        if mode == 'rise':
            k = np.linspace(0, 1, j - i)
            y[i:j] *= (.12 + .88 * k ** 1.6)[:, None]
        t0 += dur
    return norm(soft(norm(y, 1.0), 1.4), .92)

def m_demon_theme(dur, bpm=56):
    s = Song(bpm, seed=33)
    ORG, CH, CB, TIMP = 0, 1, 2, 3
    s.inst(ORG, P2['organ'], 104); s.inst(CH, P['choir'], 92); s.inst(CB, P['contra'], 108); s.inst(TIMP, P['timp'], 112)
    s.inst(9, 0, 118, drums=True, kit=KIT['power'])
    prog = [('Dm', 'D2'), ('Eb', 'Eb2'), ('Dm', 'D2'), ('C#dim', 'C#2')]
    bars = _bars(dur, bpm)
    for b in range(bars):
        c, r = prog[b % 4]
        b0 = b * 4
        s.notes(b0, 3.95, chord(c, 3) + [chord(c, 4)[0]], 98, ORG)
        s.notes(b0, 3.95, chord(c, 4), 84, CH)
        s.note(b0, 3.9, n2m(r), 108, CB)
        s.hit(b0, DR['kick'], 122); s.hit(b0, DR['tom6'], 110)
        s.hit(b0 + 2, DR['snare'], 112); s.hit(b0 + 2, DR['clap'], 90)
        s.hit(b0 + 3.5, DR['kick'], 100)
        if b % 2 == 0:
            s.note(b0, 1.5, n2m(r) + 12, 112, TIMP)
    x = s.render(dur, 0)
    # glitch layer: bitcrushed organ arpeggio, gated in random bursts
    g = Song(bpm * 2, seed=34)
    g.inst(0, P['celesta'], 110)
    nb = int(dur / g.beat) + 4
    arp = [n2m(v) for v in ('D5', 'A5', 'F5', 'Eb6', 'D6', 'A5', 'C#6', 'F5')]
    for k in range(nb * 2):
        g.note(k * .5, .4, arp[(k * 3) % 8], 100, 0)
    gl = mono(g.render(dur, 0))
    gl = _bitcrush(gl, hold=9, bits=3) * _glitch_gate(len(gl), 35, rate=2.5, duty=.4)
    x[:len(gl)] += np.stack([gl, gl * .7], 1) * .25
    return finish(x, .3, 3.0, .9, fin=.4, fout=min(1.5, dur * .2), dur=dur, bright=3500)

# ----------------------------------------------------------------------- chops' warning
def m_warning(dur, bpm=70):
    s = Song(bpm, seed=41)
    STR, CEL, HRN, TIMP, CB, TRP = 0, 1, 2, 3, 4, 5
    s.inst(STR, P['strings'], 100, 70); s.inst(CEL, P['cello'], 100, 50); s.inst(HRN, P['horns'], 106, 64)
    s.inst(TIMP, P['timp'], 116); s.inst(CB, P['contra'], 104); s.inst(TRP, P['trumpet'], 92, 80)
    s.inst(9, 0, 110, drums=True, kit=KIT['orch'])
    prog = ['Cm', 'Ab', 'Eb', 'G']
    mel = ['G4:4 Ab4:2 G4:2', 'F4:4 Eb4:4', 'Bb4:4 C5:2 Bb4:2', 'G4:6 -:2']
    bars = _bars(dur, bpm)
    s.hit(0, DR['crash'], 100)
    for b in range(bars):
        c = prog[b % 4]
        b0 = b * 4
        s.notes(b0, 3.95, chord(c, 4), 92, STR)
        r = chord(c, 2)[0]
        for k in range(8):
            s.note(b0 + k * .5, .45, r + (12 if k % 2 else 0), 96, CEL)
        s.note(b0, 3.9, r, 100, CB)
        s.note(b0, .8, r + 12, 112, TIMP); s.note(b0 + 2, .8, r + 12, 100, TIMP)
        if b >= 1:
            s.mel(b0, mel[b % 4], HRN, 104, tp=0)
        if b >= 4:
            s.mel(b0, mel[b % 4], TRP, 86, tp=12)
    x = s.render(dur, 0)
    return finish(x, .3, 2.6, .9, fin=.3, fout=min(1.5, dur * .2), dur=dur)

# ----------------------------------------------------------------------- the timeline shuffle
def m_shuffle():
    dur = 4.5
    s = Song(120, seed=51)
    HARP, CEL, CH, HIT, BRS, TIMP, REV, GLK = 0, 1, 2, 3, 4, 5, 6, 7
    s.inst(HARP, P['harp'], 110, 40); s.inst(CEL, P['celesta'], 104, 90); s.inst(CH, P['choir'], 108)
    s.inst(HIT, P['orchhit'], 127); s.inst(BRS, P['brass'], 116); s.inst(TIMP, P['timp'], 124)
    s.inst(REV, P['revcym'], 120); s.inst(GLK, P['glock'], 110)
    s.inst(9, 0, 124, drums=True, kit=KIT['orch'])
    lyd = [n2m(v) for v in ('C4', 'E4', 'F#4', 'G4', 'B4', 'C5', 'E5', 'F#5', 'G5', 'B5', 'C6', 'E6', 'F#6', 'G6')]
    t, k, step = 0.0, 0, .16
    while t < 2.55:
        s.note_t(t, .3, lyd[k % len(lyd)], 90 + min(30, k), HARP)
        s.note_t(t + .03, .25, lyd[(k + 4) % len(lyd)] + 12, 80 + min(30, k), CEL)
        t += step; k += 1; step = max(.045, step * .92)
    _ramp_cc(s, CH, 0, 2.7, 20, 127)
    for m in (n2m('C4'), n2m('G4'), n2m('B4'), n2m('E5')):
        s.note_t(0, 2.7, m, 110, CH)
    s.note_t(.6, 2.2, n2m('C5'), 120, REV)
    hit = 2.7
    for m in chord('C', 4) + [n2m('C3'), n2m('G5')]:
        s.note_t(hit, .8, m, 127, HIT)
        s.note_t(hit, 1.4, m - 12, 120, BRS)
    s.note_t(hit, 1.6, n2m('C2'), 127, TIMP)
    s.note_t(hit, .5, DR['crash'], 127, 9); s.note_t(hit, .5, DR['crash2'], 124, 9)
    k = 0
    while hit + .05 + k * .06 < dur - .2:
        s.note_t(hit + .05 + k * .06, .15, [n2m('C7'), n2m('G6'), n2m('E7'), n2m('B6')][k % 4], max(30, 110 - k * 3), GLK)
        k += 1
    x = s.render(dur, 0)
    n = len(x)
    i = int(hit * SR)
    boom = _thump(n - i, 90, 30, .9, 8) * .8 + lowpass(noise(n - i, 52), 600) * env_exp(n - i, .5) * .6
    x[i:] += boom[:, None]
    return finish(x, .35, 3.0, .92, fout=.6, dur=dur, bright=7000)

# ----------------------------------------------------------------------- timelines
def m_prehistoric(dur, bpm=118):
    s = Song(bpm, seed=61)
    MAR, FLT, TUBA, TAIKO, KAL = 0, 1, 2, 3, 4
    s.inst(MAR, P2['marimba'], 110, 50); s.inst(FLT, P2['panflute'], 100, 80); s.inst(TUBA, P['tuba'], 112)
    s.inst(TAIKO, P['taiko'], 120); s.inst(KAL, P2['kalimba'], 96, 30)
    s.inst(9, 0, 112, drums=True, kit=KIT['standard'])
    riff = ['F4', 'A4', 'C5', 'A4', 'G4', 'Bb4', 'C5', 'D5']
    mel = ['C6:2 A5:1 C6:1 D6:2 C6:2', 'A5:2 G5:2 F5:4', 'G5:2 A5:1 G5:1 F5:2 D5:2', 'C5:6 -:2']
    roots = ['F2', 'F2', 'Bb1', 'C2']
    bars = _bars(dur, bpm)
    for b in range(bars):
        b0 = b * 4
        for k in range(8):
            s.note(b0 + k * .5, .4, n2m(riff[k]) + (5 if b % 4 == 2 else 0), 100, MAR)
            if k % 2 == 1:
                s.note(b0 + k * .5, .3, n2m(riff[(k + 3) % 8]) + 12, 70, KAL)
        r = n2m(roots[b % 4])
        s.note(b0, .6, r, 120, TUBA); s.note(b0 + 2, .6, r + 7, 112, TUBA); s.note(b0 + 3.5, .4, r + 12, 100, TUBA)
        s.note(b0, .5, n2m('C3'), 124, TAIKO); s.note(b0 + 2, .5, n2m('C3'), 116, TAIKO); s.note(b0 + 2.75, .3, n2m('G3'), 90, TAIKO)
        for k in range(4):
            s.hit(b0 + k, [DR['tom5'], DR['tom3'], DR['tom4'], DR['tom1']][k], 100)
            s.hit(b0 + k + .5, DR['shaker'], 70)
        if b >= 2:
            s.mel(b0, mel[b % 4], FLT, 98)
    x = s.render(dur, 0)
    return finish(x, .18, 1.8, .9, fout=min(1.2, dur * .2), dur=dur)

def m_rich(dur, bpm=90):
    s = Song(bpm, seed=71)
    PNO, BASS, BRS, STR = 0, 1, 2, 3
    s.inst(PNO, P['ep'], 100, 50); s.inst(BASS, P2['synbass'], 116); s.inst(BRS, P['brass'], 108, 80); s.inst(STR, P['strings'], 70, 70)
    s.inst(9, 0, 112, drums=True, kit=KIT['standard'])
    prog = ['Ebmaj9', 'Cm9', 'Fm9', 'Bb13']
    bars = _bars(dur, bpm)
    for b in range(bars):
        c = prog[b % 4]
        b0 = b * 4
        oc = 3 if c in ('Bb13',) else 4
        s.notes(b0, 1.4, chord(c, oc)[:4], 88, PNO, strum=.012)
        s.notes(b0 + 2.5, 1.2, chord(c, oc)[:4], 80, PNO, strum=.012)
        s.notes(b0, 3.9, chord(c, 4)[:3], 60, STR)
        r = chord(c, 1)[0]
        s.note(b0, 1.6, r + 12, 120, BASS); s.note(b0 + 1.75, .5, r + 12, 104, BASS); s.note(b0 + 2.5, 1.4, r + 24, 110, BASS)
        s.hit(b0, DR['kick'], 120); s.hit(b0 + 1.75, DR['kick'], 104); s.hit(b0 + 2.5, DR['kick'], 110)
        s.hit(b0 + 2, DR['clap'], 110); s.hit(b0 + 2, DR['snare'], 80)
        for k in range(16):
            if b % 2 == 1 and k >= 12:
                for j in range(3):
                    s.hit(b0 + k * .25 + j * .25 / 3, DR['hh'], 70)
            else:
                s.hit(b0 + k * .25, DR['hh'], 76 if k % 2 == 0 else 54)
        if b % 2 == 1:
            for m in chord(c, 4)[:3]:
                s.note(b0 + 3.5, .4, m, 110, BRS)
        if b % 4 == 0:
            s.hit(b0, DR['crash'], 80)
    x = s.render(dur, 0)
    return finish(x, .15, 1.6, .9, fout=min(1.2, dur * .2), dur=dur)

def m_limbo(dur):
    s = Song(60, seed=81)
    PAD, HALO, REV = 0, 1, 2
    s.inst(PAD, P['warmpad'], 96); s.inst(HALO, P2['halo'], 90); s.inst(REV, P['revcym'], 90)
    s.inst(9, 0, 90, drums=True, kit=KIT['standard'])
    chords_ = [('C#m', 3), ('Am', 3), ('Fmaj7', 3), ('G#m', 3)]
    t, i = 0.0, 0
    while t < dur:
        c, o = chords_[i % 4]
        for m in chord(c, o):
            s.note_t(t, 4.2, m, 80, PAD)
        s.note_t(t + .5, 3.5, chord(c, o + 1)[1], 70, HALO)
        s.note_t(t + 1.8, 2.2, n2m('C5'), 80, REV)
        t += 4; i += 1
    k = 0
    while k * .5 < dur:
        s.note_t(k * .5 + (.03 if k % 2 else 0), .05, DR['wood_hi'] if k % 2 else DR['wood_lo'], 64, 9)
        k += 1
    x = s.render(dur, 0)
    g = Song(100, seed=82); g.inst(0, P['celesta'], 104)
    rnd = random.Random(83)
    tt = .3
    while tt < dur:
        g.note_t(tt, .3, rnd.choice([n2m(v) for v in ('C#6', 'E6', 'G#6', 'B6', 'D7')]), 100, 0)
        tt += rnd.uniform(.08, .5)
    gl = mono(g.render(dur, 0))
    gl = _bitcrush(gl, hold=12, bits=3) * _glitch_gate(len(gl), 84, rate=2, duty=.3)
    x[:len(gl)] += np.stack([gl * .7, gl], 1) * .3
    return finish(x, .45, 3.5, .85, fin=.8, fout=min(1.5, dur * .25), dur=dur, bright=3000)

def m_mars_ruins(dur, bpm=64):
    s = Song(bpm, seed=91)
    PNO, STR, OOH, CEL = 0, 1, 2, 3
    s.inst(PNO, P['piano'], 100, 56); s.inst(STR, P['slowstr'], 88, 72); s.inst(OOH, P2['ooh'], 76); s.inst(CEL, P['cello'], 84, 40)
    prog = ['Am', 'Fmaj7', 'C', 'Em']
    mel = ['E5:3 D5:1 C5:2 B4:2', 'A4:6 -:2', 'G4:2 C5:2 E5:3 D5:1', 'B4:6 -:2']
    bars = _bars(dur, bpm)
    for b in range(bars):
        c = prog[b % 4]
        b0 = b * 4
        cn = chord(c, 3)
        arp = [cn[0], cn[1] + 12, cn[2] + 12, cn[1] + 12]
        for k in range(8):
            s.note(b0 + k * .5, 1.0, arp[k % 4] if k < 4 else arp[k % 4] + (12 if k % 2 else 0), 70, PNO)
        s.notes(b0, 3.95, chord(c, 4)[:3], 70, STR)
        s.note(b0, 3.9, chord(c, 2)[0], 76, CEL)
        if b >= 1:
            s.mel(b0, mel[b % 4], PNO, 92)
        if b >= 2:
            s.notes(b0, 3.9, chord(c, 4)[:2], 60, OOH)
    x = s.render(dur, 0)
    return finish(x, .38, 3.2, .85, fin=.6, fout=min(2.0, dur * .25), dur=dur)

def m_cooking(dur, bpm=124):
    s = Song(bpm, seed=101)
    BASS, GTR, BRS, SAX = 0, 1, 2, 3
    s.inst(BASS, P2['slapbass'], 118); s.inst(GTR, P2['mutegtr'], 100, 40); s.inst(BRS, P['brass'], 110, 84); s.inst(SAX, P2['altosax'], 100, 70)
    s.inst(9, 0, 112, drums=True, kit=KIT['standard'])
    bassline = [(0, 'E2', .3), (.75, 'E2', .2), (1, 'E3', .2), (1.5, 'D3', .2), (2, 'E2', .3), (2.75, 'G2', .2), (3, 'A2', .3), (3.5, 'B2', .2)]
    lick = ['E5:1 G5:1 A5:1 B5:1 D6:2 B5:2', '-:4 E5:1 D5:1 B4:2', 'G5:1 A5:1 G5:1 E5:1 D5:2 E5:2', '-:8']
    bars = _bars(dur, bpm)
    for b in range(bars):
        b0 = b * 4
        tp = 5 if b % 4 == 3 else 0
        for off, nm, ln in bassline:
            s.note(b0 + off, ln, n2m(nm) + tp, 116, BASS)
        for k in range(16):
            if k % 4 in (1, 3) or k in (6, 14):
                s.notes(b0 + k * .25, .12, [n2m('E4') + tp, n2m('G#4') + tp, n2m('D5') + tp, n2m('F#5') + tp], 84 if k % 2 else 96, GTR)
        s.hit(b0, DR['kick'], 118); s.hit(b0 + 1.75, DR['kick'], 100); s.hit(b0 + 2.5, DR['kick'], 108)
        s.hit(b0 + 1, DR['snare'], 116); s.hit(b0 + 3, DR['snare'], 116); s.hit(b0 + 3.75, DR['snare'], 70)
        for k in range(16):
            s.hit(b0 + k * .25, DR['hh'], 80 if k % 2 == 0 else 58)
        if b % 2 == 0:
            for m in (n2m('B4'), n2m('E5'), n2m('G#5')):
                s.note(b0 + 3.5, .3, m + tp, 118, BRS)
                s.note(b0 + 4, .25, m + tp, 112, BRS)
        if b >= 2:
            s.mel(b0, lick[b % 4], SAX, 100, unit=.5)
        if b % 4 == 0:
            s.hit(b0, DR['crash'], 96)
    x = s.render(dur, 0)
    return finish(x, .14, 1.4, .9, fout=min(1.0, dur * .2), dur=dur)

def m_wakeup():
    dur = 3.2
    s = Song(100, seed=111)
    BEL, BRS, CH, TIMP = 0, 1, 2, 3
    s.inst(BEL, P2['tubular'], 112); s.inst(BRS, P['brass'], 112); s.inst(CH, P['choir'], 108); s.inst(TIMP, P['timp'], 116)
    s.inst(9, 0, 110, drums=True, kit=KIT['orch'])
    for i, m in enumerate(('C5', 'E5', 'G5', 'C6')):
        s.note_t(i * .12, 1.6, n2m(m), 110, BEL)
    _ramp_cc(s, BRS, .3, 1.0, 40, 127); _ramp_cc(s, CH, .2, .9, 40, 127)
    for m in chord('C', 4) + [n2m('C3')]:
        s.note_t(.45, 2.2, m, 116, BRS)
        s.note_t(.4, 2.4, m, 110, CH)
    s.note_t(.45, 1.2, n2m('C2'), 120, TIMP); s.note_t(.45, .5, DR['crash'], 110, 9)
    x = s.render(dur, 0)
    return finish(x, .32, 2.6, .9, fout=.8, dur=dur)

def m_mystery(dur, bpm=70):
    s = Song(bpm, seed=121)
    PNO, STR, CB = 0, 1, 2
    s.inst(PNO, P['piano'], 96, 56); s.inst(STR, P['strings'], 84, 72); s.inst(CB, P['contra'], 92)
    prog = ['Am', 'F', 'Dm', 'E']
    beat = 60.0 / bpm
    hold = min(3.0, dur * .3)                      # final unresolved chord
    body = max(0.0, dur - hold)
    nb = int(body / (4 * beat))
    for b in range(nb):
        c = prog[b % 4]
        b0 = b * 4
        cn = chord(c, 4)
        for k in range(4):
            s.note(b0 + k, .9, cn[k % 3] - (12 if k == 0 else 0), 72, PNO)
        s.notes(b0, 3.95, chord(c, 3), 70, STR)
        s.note(b0, 3.9, chord(c, 2)[0], 80, CB)
    t_end = nb * 4 * beat
    # unresolved: Bb/E (tritone over the bass) — the question hangs
    for m in (n2m('E2'), n2m('Bb3'), n2m('D4'), n2m('F4'), n2m('A#4')):
        s.note_t(t_end, dur - t_end, m, 86, STR)
    for m in (n2m('E3'), n2m('Bb3'), n2m('D4'), n2m('F4')):
        s.note_t(t_end, dur - t_end, m, 78, PNO)
    s.note_t(t_end, dur - t_end, n2m('E1') + 12, 90, CB)
    x = s.render(dur, 0)
    return finish(x, .35, 3.0, .85, fin=.4, fout=.25, dur=dur)

# ----------------------------------------------------------------------- Ep02 SFX (falls through to Ep01 sfx)
_sfx_ep01 = sfx

def sfx(name, seed=0):
    n_ = lambda s: int(s * SR)
    if name == 'roar':
        n = n_(1.8)
        t = np.arange(n) / SR
        f = (190 - 90 * np.clip(t / 1.4, 0, 1)) * (1 + .04 * np.sin(2 * np.pi * 7 * t))
        ph = np.cumsum(f) / SR
        saw = 2 * (ph % 1.0) - 1
        rough = saw * (1 + .5 * bandpass(noise(n, 131), 20, 90))
        x = bandpass(rough, 300, 900) + bandpass(rough, 1100, 1800) * .6 + lowpass(rough, 250) * .8
        x += bandpass(noise(n, 132), 400, 3000) * .35
        env = np.clip(t / .12, 0, 1) * np.clip((1.8 - t) / .6, 0, 1)
        return _fit(_rev(np.tanh(x * env * 2.5), .4, 2.0), .9)
    if name == 'stuck_click':
        n = n_(1.1)
        out = np.zeros(n)
        rnd = random.Random(seed + 133)
        tt = .02
        while tt < .95:
            i0 = int(tt * SR)
            c = _click(n_(.06), rnd.uniform(2600, 3400), .004, rnd.randint(0, 99)) * .6 + _thump(n_(.06), 500, 250, .01) * .3
            out[i0:i0 + len(c)] += c[:n - i0]
            tt += rnd.uniform(.07, .14)
        return _fit(out, .55)
    if name == 'magic':
        n = n_(1.6)
        t = np.arange(n) / SR
        sw = _sweep_noise(n, 300, 9000, 141) * np.clip(t / 1.4, 0, 1) ** 2 * np.clip((1.6 - t) / .2, 0, 1)
        notes = [(i * .07, .4, n2m(v) + 12 * (i // 6)) for i, v in enumerate(['C5', 'E5', 'G5', 'B5', 'D6', 'F#6'] * 3)]
        cel = _sf_one(P['celesta'], notes, 1.6, 100, tail=.2)
        m = min(n, len(cel))
        return _fit(_rev(sw[:m] * .5 + cel[:m], .4), .75)
    if name == 'explosion_light':
        n = n_(3.2)
        t = np.arange(n) / SR
        x = _thump(n, 110, 28, 1.0, 6) * 1.2 + lowpass(noise(n, 151), 900) * env_exp(n, .6) * .9
        x += highpass(noise(n, 152), 3000) * env_exp(n, .9) * .25
        sh = _sf_one(P['glock'], [(.05 + k * .05, .3, [n2m('C7'), n2m('G6'), n2m('E7'), n2m('B6')][k % 4], max(20, 110 - 3 * k)) for k in range(50)], 3.2, tail=0)
        m = min(n, len(sh)); x[:m] += sh[:m] * .6
        return _fit(_rev(x, .45, 2.6), .95)
    if name == 'cash':
        n = n_(1.3)
        t = np.arange(n) / SR
        rnd = random.Random(seed + 161)
        x = bandpass(noise(n, 162), 800, 3000) * np.exp(-t * 18) * .5          # drawer slide
        bell = _sf_one(P2['tinkle'], [(.08, .6, n2m('E6'), 120), (.08, .6, n2m('B6'), 110)], 1.3, tail=0)
        m = min(n, len(bell)); x[:m] += bell[:m]
        for k in range(14):
            i0 = int(rnd.uniform(.25, 1.0) * SR); mm = n_(.2); tq = np.arange(mm) / SR
            ping = (np.sin(2 * np.pi * rnd.uniform(3500, 7000) * tq) + .5 * np.sin(2 * np.pi * rnd.uniform(7000, 11000) * tq)) * np.exp(-tq * 30) * .2
            x[i0:i0 + mm] += ping[:n - i0]
        return _fit(x, .75)
    if name == 'crowd_cheer':
        n = n_(2.6)
        t = np.arange(n) / SR
        out = np.zeros(n)
        rnd = random.Random(seed + 171)
        forms = [(800, 1250), (750, 1150), (650, 1100), (900, 1400)]
        for v in range(16):
            f0 = rnd.uniform(160, 380)
            con = f0 * (1 + .12 * np.sin(2 * np.pi * rnd.uniform(3, 6) * t + v)) * (1 + .2 * np.clip(t, 0, 1))
            glott = ((np.cumsum(con) / SR) % 1.0) ** 3 - .25
            f1, f2 = forms[v % 4]
            out += (bandpass(glott, f1 * .7, f1 * 1.3) + bandpass(glott, f2 * .8, f2 * 1.2) * .6) * rnd.uniform(.5, 1)
        for k in range(60):
            i0 = int(rnd.uniform(0, 2.4) * SR); mm = n_(.03)
            out[i0:i0 + mm] += bandpass(noise(mm, k), 1000, 4000)[:n - i0] * rnd.uniform(.3, .8)
        out *= np.clip(t * 4, 0, 1) * np.clip((2.6 - t) * 2, 0, 1)
        return _fit(_rev(out, .35), .7)
    if name == 'pour':
        n = n_(1.3)
        t = np.arange(n) / SR
        fc = 500 + 900 * np.clip(t / 1.2, 0, 1)
        nz = noise(n, 181)
        x = np.zeros(n)
        for b, f in enumerate((500, 800, 1200, 1600)):
            w = np.clip(1 - np.abs(fc - f) / 450, 0, 1)
            x += bandpass(nz, f * .8, f * 1.25) * w
        x *= 1 + .6 * np.sin(2 * np.pi * 23 * t) * np.sin(2 * np.pi * 3.1 * t)
        x *= np.clip(t / .08, 0, 1) * np.clip((1.3 - t) / .15, 0, 1)
        return _fit(x, .55)
    if name == 'muddle':
        n = n_(.9)
        out = np.zeros(n)
        for k, tt in enumerate((.05, .35, .62)):
            i0 = int(tt * SR); mm = n_(.22); tq = np.arange(mm) / SR
            sq = lowpass(noise(mm, 190 + k), 700) * np.sin(np.pi * np.clip(tq / .22, 0, 1)) * 1.4
            sq += _click(mm, 1400, .01, k) * .25 + _thump(mm, 160, 80, .05) * .5
            out[i0:i0 + mm] += sq[:n - i0]
        return _fit(out, .55)
    if name == 'ice':
        n = n_(1.1)
        out = np.zeros(n)
        rnd = random.Random(seed + 201)
        for k in range(70):
            i0 = int(rnd.uniform(0, .95) * SR)
            c = _click(n_(.03), rnd.uniform(1800, 6000), rnd.uniform(.002, .006), rnd.randint(0, 999)) * rnd.uniform(.2, .7)
            out[i0:i0 + len(c)] += c[:n - i0]
        t = np.arange(n) / SR
        out += bandpass(noise(n, 202), 2000, 7000) * np.exp(-t * 4) * .15
        return _fit(out, .6)
    if name == 'stir':
        n = n_(1.3)
        t = np.arange(n) / SR
        out = bandpass(noise(n, 211), 1500, 5000) * (.5 + .5 * np.sin(2 * np.pi * 5 * t)) * .1
        rnd = random.Random(seed + 212)
        for k in range(7):
            i0 = int((.05 + k * .17 + rnd.uniform(-.02, .02)) * SR); mm = n_(.35); tq = np.arange(mm) / SR
            ping = sum(np.sin(2 * np.pi * f * tq) * a for f, a in ((2480, 1), (5130, .5), (7910, .25))) * np.exp(-tq * 14) * rnd.uniform(.3, .6)
            out[i0:i0 + mm] += ping[:n - i0]
        return _fit(out, .6)
    if name == 'frost':
        n = n_(1.3)
        t = np.arange(n) / SR
        rnd = np.random.default_rng(seed + 221)
        crk = np.zeros(n); idx = rnd.integers(0, n, 400); crk[idx] = rnd.uniform(-1, 1, 400)
        crk = highpass(crk, 3000) * np.clip(t / .3, 0, 1)
        shim = np.sin(2 * np.pi * np.cumsum(3000 + 2500 * t / 1.3) / SR) * .15 * np.exp(-t * 1.5)
        return _fit(_rev(crk + shim, .4), .5)
    if name == 'slap':
        n = n_(.25)
        t = np.arange(n) / SR
        x = bandpass(noise(n, 231), 600, 5000) * np.exp(-t / .015) * 1.5 + _thump(n, 300, 140, .02) * .4
        return _fit(x, .6)
    if name == 'slurp':
        n = n_(1.1)
        t = np.arange(n) / SR
        fc = 900 + 700 * np.sin(2 * np.pi * 1.3 * t)
        nz = noise(n, 241)
        x = bandpass(nz, 500, 1300) * (fc < 1100) + bandpass(nz, 1100, 2400) * (fc >= 1100)
        x *= (np.sin(2 * np.pi * 14 * t) > -.2) * np.clip(t / .05, 0, 1) * np.clip((1.1 - t) / .15, 0, 1)
        x += _thump(n, 240, 120, .03) * (t > .95) * .0
        return _fit(lowpass(x, 3500), .5)
    if name == 'quake':
        n = n_(2.0)
        t = np.arange(n) / SR
        x = _thump(n, 75, 24, .8, 7) * 1.3 + lowpass(noise(n, 251), 140) * np.exp(-t * 1.6) * 2.0
        rnd = random.Random(seed + 252)
        for k in range(30):
            i0 = int(rnd.uniform(.05, 1.4) * SR)
            c = _click(n_(.04), rnd.uniform(800, 2500), .006, k) * rnd.uniform(.05, .2)
            x[i0:i0 + len(c)] += c[:n - i0]
        return _fit(_rev(x, .3, 1.8), .95)
    if name == 'stone_crack':
        n = n_(1.4)
        t = np.arange(n) / SR
        x = bandpass(noise(n, 261), 900, 6000) * np.exp(-t / .03) * 1.6 + _thump(n, 150, 50, .15, 20) * .7
        rnd = random.Random(seed + 262)
        for k in range(40):
            i0 = int(rnd.uniform(.08, 1.2) * SR)
            c = _click(n_(.03), rnd.uniform(500, 2200), .008, k) * rnd.uniform(.05, .25) * (1 - i0 / n)
            x[i0:i0 + len(c)] += c[:n - i0]
        return _fit(_rev(x, .25), .8)
    if name == 'swoosh':
        n = n_(1.0)
        t = np.arange(n) / SR
        up = _sweep_noise(n, 200, 6000, 271)
        x = up * np.sin(np.pi * np.clip(t / 1.0, 0, 1)) ** 1.5
        return _fit(_rev(x, .3), .7)
    if name == 'flame':
        n = n_(2.0)
        t = np.arange(n) / SR
        base = lowpass(noise(n, 281), 500) * (1 + .5 * np.sin(2 * np.pi * 1.7 * t) + .3 * np.sin(2 * np.pi * 3.3 * t))
        whoosh = _sweep_noise(n, 300, 2500, 282) * np.exp(-t * 2.5) * .6
        rnd = np.random.default_rng(seed + 283)
        pops = np.zeros(n); idx = rnd.integers(0, n, 70); pops[idx] = rnd.uniform(-1, 1, 70)
        pops = bandpass(pops, 1500, 7000) * 3
        x = base * 1.5 + whoosh + pops
        x *= np.clip(t / .1, 0, 1) * np.clip((2.0 - t) / .2, 0, 1)
        return _fit(x, .6)
    return _sfx_ep01(name, seed)

SFX_NAMES = SFX_NAMES + ['roar', 'stuck_click', 'magic', 'explosion_light', 'cash', 'crowd_cheer', 'pour', 'muddle', 'ice',
                         'stir', 'frost', 'slap', 'slurp', 'quake', 'stone_crack', 'swoosh', 'flame']


# ======================================================================= EPISODE 3 additions
# (appended; Ep01/Ep02 cues/sfx above are untouched)
P3 = dict(koto=107, shamisen=106, shakuhachi=77, sawlead=81, squarelead=80, polysynth=90, chiffs=83, scifi=103, goblin=101,
          echoes=102, atmos=99, crystal=98, brightness=100, synstr=50, epiano2=5)

def m_neoedo(dur, bpm=86):
    """Neo-Edo: rainy retro city pop / vaporwave — tired neon, koto over an old drum machine."""
    s = Song(bpm, seed=301)
    EP, BAS, KOTO, PAD, LEAD = 0, 1, 2, 3, 4
    s.inst(EP, P3['epiano2'], 88, 52); s.inst(BAS, P2['synbass'], 96); s.inst(KOTO, P3['koto'], 92, 80)
    s.inst(PAD, P3['polysynth'], 70); s.inst(LEAD, P3['chiffs'], 76, 70)
    s.inst(9, 0, 82, drums=True, kit=KIT['power'])
    prog = ['Fmaj7', 'Em7', 'Dm7', 'C', 'Fmaj7', 'Em7', 'Am', 'G']
    bars = _bars(dur, bpm)
    for b in range(bars):
        c = prog[b % 8]
        name = c.replace('maj7', '').replace('m7', 'm').replace('7', '')
        b0 = b * 4
        s.notes(b0, 3.9, chord(c, 4), 62, PAD)
        for k in (0, 1.5, 2.5):
            s.notes(b0 + k, .8, chord(c, 4)[:3], 66, EP, strum=.02)
        root = chord(name, 2)[0]
        for k, d_ in ((0, 1.2), (1.5, .4), (2, .9), (3.5, .4)):
            s.note(b0 + k, d_, root + (12 if k == 3.5 else 0), 92, BAS)
        if b >= 2:
            ct = chord(name, 5)
            for k in range(0, 8, 2 if b % 2 else 3):
                s.note(b0 + k * .5, .6, ct[k % len(ct)], 70 + (k % 3) * 8, KOTO)
        if b >= 4 and b % 4 == 3:
            s.mel(b0, 'A5:2 G5:1 E5:3 D5:2', LEAD, 80)
        for k in range(4):
            s.note(b0 + k, .2, DR['kick'] if k in (0, 2) else DR['snare'], 70 if k in (0, 2) else 62, 9)
            s.note(b0 + k + .5, .1, DR['hh'], 44, 9)
    x = s.render(dur, 0)
    # tape wobble + a little crush: the city is old
    n = len(x); tt = np.arange(n) / SR
    idx = np.clip(np.arange(n) + (np.sin(2 * np.pi * .35 * tt) * 22).astype(int), 0, n - 1)
    x = x[idx]
    return finish(x, .34, 3.0, .8, fin=.8, fout=min(1.5, dur * .25), dur=dur, bright=3600)

def m_otherness(dur, bpm=60):
    """Nick Land / the OTHERNESS tower: cold, slow, hypnotic — halo pad, low bells, a clock that ticks off-grid."""
    s = Song(bpm, seed=311)
    HALO, BELL, VOX, BAS, CRY = 0, 1, 2, 3, 4
    s.inst(HALO, P2['halo'], 92); s.inst(BELL, P2['tubular'], 70); s.inst(VOX, P2['synvoice'], 70)
    s.inst(BAS, P2['synbass'], 86); s.inst(CRY, P3['crystal'], 70, 90)
    s.inst(9, 0, 70, drums=True, kit=KIT['standard'])
    prog = ['Dm', 'Bb', 'Gm', 'A']
    bars = _bars(dur, bpm)
    for b in range(bars):
        c = prog[b % 4]
        b0 = b * 4
        s.notes(b0, 3.95, chord(c, 3), 74, HALO)
        s.note(b0, 3.9, chord(c, 1)[0] + 12, 90, BAS)
        if b % 2 == 0:
            s.note(b0, 2.5, chord(c, 4)[0], 78, BELL)
        if b >= 1:
            s.notes(b0 + 1, 2.8, chord(c, 4)[1:], 58, VOX)
        if b >= 2:
            for k in range(3):
                s.note(b0 + k * 1.33, .4, chord(c, 6)[k % 3], 60, CRY)
    k = 0
    while k * .73 < dur:                      # an off-grid clock tick
        s.note_t(k * .73, .05, DR['wood_hi'] if k % 2 else DR['rim'], 46, 9)
        k += 1
    x = s.render(dur, 0)
    return finish(x, .5, 4.0, .8, fin=1.0, fout=min(2.0, dur * .25), dur=dur, bright=2600)

def m_centuries(dur, bpm=92):
    """Time-lapse of centuries: a clock that accelerates while one chord loops and rises."""
    s = Song(bpm, seed=321)
    s.inst(0, P['musicbox'], 90); s.inst(1, P['slowstr'], 80); s.inst(9, 0, 80, drums=True, kit=KIT['standard'])
    t, step, i = 0.0, .5, 0
    while t < dur:
        s.note_t(t, .05, DR['wood_hi'] if i % 2 else DR['wood_lo'], 70, 9)
        t += step; step = max(.04, step * .965); i += 1
    for k, c in enumerate(['Am', 'F', 'C', 'G', 'Am', 'F', 'C', 'E']):
        tt = k * dur / 8
        s.notes(tt * bpm / 60, dur / 8 * bpm / 60, chord(c, 4 + (k >= 4)), 66, 1)
        for j in range(4):
            s.note_t(tt + j * dur / 32, .3, chord(c, 5 + (k >= 4))[j % 3], 80, 0)
    x = s.render(dur, 0)
    return finish(x, .3, 2.4, .85, fin=.2, fout=.15, dur=dur)


# ======================================================================= EPISODE 4 additions
def m_alterity(dur, bpm=54):
    """The Otherness: a space with no time — reversed swells, a music box running backwards, no downbeat you can trust."""
    s = Song(bpm, seed=401)
    s.inst(0, P2['halo'], 92); s.inst(1, P['musicbox'], 86); s.inst(2, P3['atmos'], 80); s.inst(3, P2['synvoice'], 70)
    prog = ['Ebmaj7', 'Am', 'Dbmaj7', 'Gm']
    bars = _bars(dur, bpm)
    for b in range(bars):
        c = prog[b % 4]; b0 = b * 4
        s.notes(b0, 3.95, chord(c, 3), 70, 0)
        s.notes(b0 + 1.5, 2.4, chord(c, 4)[1:], 56, 3)
        for k in range(6):
            s.note(b0 + k * .66, .5, chord(c, 5)[(k * 2) % 3] + (12 if k == 5 else 0), 66, 1)
        s.note(b0 + 2.2, 1.6, chord(c, 2)[0], 64, 2)
    x = s.render(dur, 0)
    n = int(SR * 4)                                       # every 4 s a block of the track plays backwards
    y = x.copy()
    for i in range(0, len(y) - n, n * 2):
        y[i:i + n] = y[i:i + n][::-1]
    return finish(y, .55, 4.5, .8, fin=1.2, fout=min(2.0, dur * .25), dur=dur, bright=2400)

def m_council(dur, bpm=72):
    """The council of Nick Lands: starts as a ticking argument, accelerates, ends on a huge choir chord (the realisation)."""
    s = Song(bpm, seed=411)
    s.inst(0, P['slowstr'], 92); s.inst(1, P2['ooh'], 88); s.inst(2, P['timp'], 100); s.inst(3, P2['tubular'], 80)
    s.inst(4, P['brass'], 92); s.inst(9, 0, 90, drums=True, kit=KIT['orch'])
    prog = ['Dm', 'Bb', 'C', 'A', 'Dm', 'F', 'G', 'A']
    bars = _bars(dur, bpm)
    for b in range(bars):
        c = prog[b % 8]; b0 = b * 4
        q = b / max(1, bars - 1)                          # 0 → 1: everything grows
        s.notes(b0, 3.95, chord(c, 3), int(60 + 40 * q), 0)
        if q > .3:
            s.notes(b0, 3.9, chord(c, 4), int(50 + 50 * q), 1)
        step = 1.0 if q < .4 else (.5 if q < .75 else .25)   # the clock accelerates
        k = 0.0
        while k < 4:
            s.hit(b0 + k, DR['wood_hi'] if int(k / step) % 2 else DR['wood_lo'], int(50 + 50 * q))
            k += step
        if q > .6:
            s.note(b0, 1, chord(c, 2)[0], int(80 + 40 * q), 2)
        if q > .85:
            s.notes(b0, 3.9, chord(c, 4), 110, 4)
            s.hit(b0, DR['crash'], 110)
    x = s.render(dur, 0)
    return finish(x, .4, 3.5, .88, fin=.6, fout=min(1.5, dur * .2), dur=dur)


# ======================================================================= EPISODE 5 additions
def m_inspire(dur, bpm=76):
    """The 'power inside you' speech: swelling major-key strings + choir, deliberately over the top (cut by a record scratch)."""
    s = Song(bpm, seed=501)
    s.inst(0, P['strings'], 96); s.inst(1, P2['ooh'], 90); s.inst(2, P['harp'], 88); s.inst(3, P['horns'], 90)
    prog = ['C', 'G', 'Am', 'F', 'C', 'G', 'F', 'G']
    bars = _bars(dur, bpm)
    for b in range(bars):
        c = prog[b % 8]; b0 = b * 4; q = b / max(1, bars - 1)
        s.notes(b0, 3.95, chord(c, 3), int(70 + 40 * q), 0)
        s.notes(b0, 3.9, chord(c, 4), int(50 + 50 * q), 1)
        for k in range(8):
            s.note(b0 + k * .5, .5, chord(c, 5)[k % 3] + (12 if k > 4 else 0), 70, 2)
        if q > .4:
            s.mel(b0, ['E5:4 G5:4', 'D5:4 B4:4', 'C5:4 E5:4', 'F5:6 A5:2'][b % 4], 3, int(80 + 30 * q))
    x = s.render(dur, 0)
    return finish(x, .35, 3.0, .9, fin=1.0, fout=.05, dur=dur)

def m_ceremony(dur, bpm=96):
    """The validation ceremony: a heroic march; every validation lands on a downbeat."""
    s = Song(bpm, seed=511)
    s.inst(0, P['brass'], 100); s.inst(1, P['strings'], 92); s.inst(2, P['timp'], 104); s.inst(3, P2['ooh'], 86)
    s.inst(9, 0, 100, drums=True, kit=KIT['orch'])
    prog = ['D', 'A', 'Bm', 'G', 'D', 'A', 'G', 'A']
    bars = _bars(dur, bpm)
    for b in range(bars):
        c = prog[b % 8]; b0 = b * 4; q = b / max(1, bars - 1)
        s.notes(b0, 3.9, chord(c, 3), 80, 1)
        s.notes(b0, 1.0, chord(c, 4), int(90 + 30 * q), 0); s.notes(b0 + 2, 1.0, chord(c, 4), int(80 + 30 * q), 0)
        s.note(b0, 1, chord(c, 2)[0], 110, 2); s.note(b0 + 2, 1, chord(c, 2)[0], 96, 2)
        if q > .3:
            s.notes(b0, 3.9, chord(c, 4), 70, 3)
        for k in range(4):
            s.hit(b0 + k, DR['snare'] if k % 2 else DR['kick'], 90)
        if b % 4 == 3:
            s.hit(b0, DR['crash'], 110)
    x = s.render(dur, 0)
    return finish(x, .3, 2.4, .9, fin=.3, fout=min(2.0, dur * .2), dur=dur)

def m_auction(dur, bpm=148):
    """The auction as a battle: driving minor ostinato, brass stabs on every bid, timpani, snare rolls that keep rising."""
    s = Song(bpm, seed=521)
    STR, BRS, BAS, PNO = 0, 1, 2, 3
    s.inst(STR, P['strings'], 96); s.inst(BRS, P['brass'], 104); s.inst(BAS, P2['synbass'], 104); s.inst(PNO, P['piano'], 86)
    s.inst(7, P['timp'], 104); s.inst(9, 0, 104, drums=True, kit=KIT['power'])
    prog = ['Am', 'Am', 'F', 'G', 'Am', 'Am', 'Dm', 'E']
    bars = _bars(dur, bpm)
    for b in range(bars):
        c = prog[b % 8]; b0 = b * 4; q = min(1, b / max(1, bars - 1) * 1.4)
        r = chord(c, 2)[0]
        for k in range(8):                                          # the galloping ostinato
            s.note(b0 + k * .5, .4, chord(c, 4)[k % 3] + (12 if k % 4 == 3 else 0), 74 + int(20 * q), STR)
            s.note(b0 + k * .5, .4, r + (12 if k % 2 else 0), 100, BAS)
        if b % 2 == 0:
            s.notes(b0, 1.0, chord(c, 4), 110, BRS); s.notes(b0 + 1.5, .5, chord(c, 4), 104, BRS)
        if b % 2 == 1:
            s.notes(b0 + 2, 2.0, chord(c, 5), 70 + int(30 * q), PNO)
        s.note(b0, 1, chord(c, 1)[0] + 12, 110, 7)
        for k in range(4):
            s.hit(b0 + k, DR['kick'] if k % 2 == 0 else DR['snare'], 104)
            s.hit(b0 + k + .5, DR['hh'], 70)
        if b % 4 == 3:
            for k in range(8):
                s.hit(b0 + 2 + k * .25, DR['snare'], 70 + k * 6)
            s.hit(b0 + 4, DR['crash'], 112)
    x = s.render(dur, 0)
    return finish(x, .22, 1.8, .9, fin=.3, fout=min(1.5, dur * .2), dur=dur)
