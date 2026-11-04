"""Japanese voice-over via a local VOICEVOX engine, cached, with lip-sync envelopes."""
import os, json, hashlib, subprocess, time, wave, io
import numpy as np
import requests
from scipy.signal import resample_poly

HERE = os.path.dirname(os.path.abspath(__file__))
import paths
CACHE = paths.VOICE_CACHE
ENGINE_DIR = paths.VOICEVOX_DIR
URL = 'http://127.0.0.1:50021'
SR = 44100
PACE = 1.1   # global anime pacing

# character -> {emotion: (style_id, speed, pitch, intonation, volume)}
# VOICEVOX speakers (credit required in the ED): see CREDITS below
def _v(n, s=1.0, p=0.0, i=1.0, v=1.0):
    return (n, s, p, i, v)

CAST = {
    'giulio':      dict(normal=_v(12, 1.05), shout=_v(34, 1.12, .02, 1.45, 1.25), panic=_v(33, 1.18, .03, 1.4, 1.2), whisper=_v(12, .92, -.02, .8, .55), serious=_v(12, .95, -.04, 1.1), sad=_v(35, 1.0)),
    'chops':       dict(normal=_v(13, .98), mono=_v(84, .93, -.02, 1.15), shout=_v(81, 1.08, 0, 1.4, 1.2), whisper=_v(86, .95), happy=_v(83, 1.08)),
    'colin':       dict(normal=_v(11, 1.02), shout=_v(40, 1.14, .02, 1.65, 1.35), serious=_v(11, .95, -.04, 1.0), happy=_v(39, 1.1, .02, 1.5),
                        dark=_v(40, 1.08, -.04, 1.8, 1.4), darkwhisper=_v(11, .85, -.07, 1.3, .9), sad=_v(41, .98)),
    'slaughter':   dict(normal=_v(21, .97, -.02), shout=_v(21, 1.15, .04, 1.6, 1.3), serious=_v(21, .92, -.05, 1.0)),
    'elegy':       dict(normal=_v(14, .9, -.02, .8), worried=_v(14, 1.0, .02, 1.2),
                        unhinged=_v(14, .8, -.03, 1.45, .85), rage=_v(14, 1.12, .04, 1.9, 1.4)),          # Ep03+: the cracked deadpan (slow, breathy, giggles)
    'taras':       dict(normal=_v(52, 1.05, 0, 1.25), shout=_v(52, 1.15, .03, 1.5, 1.2)),
    'jeff':        dict(normal=_v(42, .92, 0, .8)),
    'uh':          dict(normal=_v(3, 1.08), shout=_v(7, 1.15, .02, 1.5, 1.2), happy=_v(1, 1.1, .02, 1.4)),
    'pedrox':      dict(normal=_v(51, 1.05), shout=_v(51, 1.15, .03, 1.5, 1.25)),
    'bb':          dict(normal=_v(8, 1.1), shout=_v(8, 1.18, .04, 1.5, 1.2)),
    'quin':        dict(normal=_v(53, .85, -.05, .7), shout=_v(53, .92, -.03, 1.35, 1.25), sad=_v(53, .82, -.06, 1.1)),
    'luke':        dict(normal=_v(100, 1.05), shout=_v(100, 1.15, .03, 1.5, 1.2)),
    'noside':      dict(normal=_v(16, 1.05), shout=_v(18, 1.15, .03, 1.5, 1.2)),
    'errorgarden': dict(normal=_v(99, 1.05), shout=_v(101, 1.15, .03, 1.5, 1.2)),
    'pondering':   dict(normal=_v(29, 1.0), shout=_v(29, 1.12, .03, 1.5, 1.2)),
    'cheesus':     dict(normal=_v(61, 1.1), shout=_v(62, 1.18, .03, 1.5, 1.2)),
    'deepcode':    dict(normal=_v(88, 1.0), shout=_v(88, 1.12, .02, 1.4, 1.2)),
    # --- non-ghoul roles (Ep02+)
    'narrator':    dict(normal=_v(109, 1.0, 0, 1.1)),
    'demon':       dict(normal=_v(53, .9, -.12, 1.3, 1.3), shout=_v(53, 1.0, -.1, 1.7, 1.45), whisper=_v(53, .85, -.13, 1.0, 1.0)),
    'pa':          dict(normal=_v(47, 1.0, 0, .8, .9)),      # public-address robot (skull-ban timeline)
    'monster_a':   dict(normal=_v(112, .95, -.12, 1.6, 1.2)),   # monster #1 — growly gibberish (+ monster_fx)
    'monster_b':   dict(normal=_v(113, .85, -.15, 1.8, 1.3)),   # monster #14 — big, deep gibberish (+ monster_fx)
    # --- Ep03+
    'nick':        dict(normal=_v(67, .84, -.07, .9, 1.05), slow=_v(67, .76, -.08, .8, 1.0), shout=_v(67, .98, -.03, 1.55, 1.3),
                        whisper=_v(67, .8, -.08, .7, .65), shaken=_v(67, .9, -.04, 1.25, .95)),   # Nick Land cyborg (+ nick_fx)
    'hammallama':  dict(normal=_v(122, 1.04), shout=_v(123, 1.12, .02, 1.45, 1.2), sad=_v(124, .95), whisper=_v(125, .95, 0, .9, .6)),
    # --- Ep04: the other Nick Lands (same 栗田まろん, different age/medium) and the council speaking as one
    'nick95':      dict(normal=_v(67, 1.0, .0, 1.15, 1.0)),            # 1995, young, fast (+ VHS warble)
    'nick09':      dict(normal=_v(67, .9, -.05, .8, .95)),             # 2009, tired, guilty (+ CRT box)
    'nick77':      dict(normal=_v(67, 1.02, -.02, 1.25, 1.0)),         # #7777, poor but sharp
    'nickhead':    dict(normal=_v(67, .96, .02, .9, .95)),             # the head in the jar (+ pa_fx)
    'nickold':     dict(normal=_v(67, .6, -.12, .6, 1.0)),             # the ancient one (+ stone echo)
    'nicks':       dict(normal=_v(67, .85, -.06, 1.0, 1.1), shout=_v(67, .9, -.04, 1.4, 1.3)),   # all the Nicks in unison (+ chorus)
    # --- Ep05
    'auctioneer':  dict(normal=_v(46, 1.08, .02, 1.3, 1.0), shout=_v(46, 1.15, .04, 1.6, 1.2)),   # #7777 auction house (小夜/SAYO)
    'crowd':       dict(normal=_v(78, 1.1, .02, 1.6, 1.2)),                                     # a voice from the auction crowd (もち子さん 怒り)
    'gang':        dict(normal=_v(7, 1.15, .02, 1.6, 1.3)),                                     # all the ghouls at once (+ chorus)
    'bodacious':   dict(normal=_v(55, 1.04, 0, 1.2), shout=_v(110, 1.1, .02, 1.5, 1.2), happy=_v(57, 1.08, .02, 1.4), sad=_v(56, .95)),
    'ai':          dict(normal=_v(89, 1.0, 0, .6, .9)),       # OTHERNESS reception AI (+ pa_fx)
    'ghost':       dict(normal=_v(104, .95, 0, 1.1, .9)),     # ghost uploaded into a paper lantern (Neo-Edo)
    'monk':        dict(normal=_v(50, .9, -.03, 1.2, .9)),    # machine monk (+ pa_fx)
    'interviewer': dict(normal=_v(2, 1.05, .02, 1.15), happy=_v(0, 1.08, .03, 1.3), awkward=_v(36, .95, 0, .9, .8)),   # press-junket interviewer (bonus)
}

CREDITS = [
    ('ジュリオ', '白上虎太郎'), ('チョップス', '青山龍星'), ('コリン', '玄野武宏'), ('スローターメロン軍曹', '剣崎雌雄'),
    ('エレジー', '冥鳴ひまり'), ('タラス', '雀松朱司'), ('ジェフ', 'ちび式じい'), ('アー', 'ずんだもん'),
    ('ペドロックス', '†聖騎士 紅桜†'), ('ビービー', '春日部つむぎ'), ('クイン', '麒ヶ島宗麟'), ('ルーク', '黒沢冴白'),
    ('ノーサイド', '九州そら'), ('エラーガーデン', '離途'), ('ポンダリング', 'No.7'), ('チーザス', '中国うさぎ'),
    ('ディープコード', '後鬼'),
    ('ナレーション', '東北イタコ'), ('BTCデーモン', '麒ヶ島宗麟'), ('アナウンス', 'ナースロボ＿タイプＴ'), ('インタビュアー', '四国めたん'), ('モンスター1号', '猫使ビィ'), ('モンスター14号', 'あんこもん'),
    ('ニック・ランド', '栗田まろん'), ('ハマラマ', '暁記ミタマ'), ('ボディシャス・パイレーツ', '猫使アル'), ('受付AI', 'Voidoll'), ('競売人', '小夜/SAYO'), ('観衆', 'もち子さん'), ('提灯の幽霊', 'ユーレイちゃん'), ('機械僧', 'ナースロボ＿タイプＴ'),
]

def ensure_engine():
    try:
        requests.get(URL + '/version', timeout=2)
        return
    except Exception:
        pass
    subprocess.Popen([os.path.join(ENGINE_DIR, 'run'), '--host', '127.0.0.1', '--port', '50021', '--cpu_num_threads', '8'],
                     cwd=ENGINE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(60):
        time.sleep(2)
        try:
            requests.get(URL + '/version', timeout=2)
            return
        except Exception:
            pass
    raise RuntimeError('VOICEVOX engine did not start')

def _key(who, text, emo):
    return hashlib.sha1(json.dumps([who, text, emo, CAST[who].get(emo, CAST[who]['normal']), PACE], ensure_ascii=False).encode()).hexdigest()[:16]

def synth(who, text, emo='normal'):
    """Return mono float32 @44.1k. Cached on disk."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f'{who}_{_key(who, text, emo)}.wav')
    if not os.path.exists(path):
        ensure_engine()
        sid, speed, pitch, inton, vol = CAST[who].get(emo, CAST[who]['normal'])
        q = requests.post(URL + '/audio_query', params={'text': text, 'speaker': sid}, timeout=120).json()
        q.update(speedScale=speed * PACE, pitchScale=pitch, intonationScale=inton, volumeScale=vol,
                 prePhonemeLength=0.05, postPhonemeLength=0.12, outputSamplingRate=24000, outputStereo=False)
        r = requests.post(URL + '/synthesis', params={'speaker': sid}, data=json.dumps(q),
                          headers={'Content-Type': 'application/json'}, timeout=300)
        r.raise_for_status()
        open(path, 'wb').write(r.content)
    with wave.open(path) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
    if sr != SR:
        x = resample_poly(x, 147, 80) if sr == 24000 else resample_poly(x, SR, sr)
    if emo in ('dark', 'darkwhisper'):
        x = demonic(x)
    if who == 'demon':
        x = demon_fx(x)
    if who in ('pa', 'ai', 'monk'):
        x = pa_fx(x)
    if who.startswith('nick'):
        x = nick_fx(x)
    if who == 'nick95':
        x = vhs_fx(x)
    if who == 'nick09':
        y = pa_fx(x); y[:len(x)] = y[:len(x)] * .6 + x * .5; x = y          # CRT speaker box
    if who == 'nickhead':
        x = pa_fx(x)
    if who == 'nickold':
        x = cave_fx(x)
    if who in ('nicks', 'gang'):
        x = chorus_fx(x)
    if who.startswith('monster'):
        x = monster_fx(x, deep=(who == 'monster_b'))
    return x.astype(np.float32)

def demonic(x):
    """Villain power-up voice: grit + a lower ghost double + cavernous echo."""
    from scipy.signal import lfilter
    n = len(x)
    # lower double: resample down a fifth-ish, time-stretched copy trimmed to length
    low = resample_poly(x, 3, 2)[:n]
    low = np.pad(low, (0, max(0, n - len(low))))
    grit = np.tanh(x * 4) * .35
    a = np.exp(-2 * np.pi * 900 / SR)
    low = lfilter([1 - a], [1, -a], low)
    y = x + grit + low * .55
    out = np.zeros(n + int(.6 * SR))
    out[:n] += y
    for k, (dly, g) in enumerate(((.11, .35), (.23, .22), (.37, .14))):
        i = int(dly * SR)
        out[i:i + n] += y * g
    out = out / (np.abs(out).max() + 1e-9) * min(1.0, np.abs(x).max() * 1.4)
    return out

def envelope(x, fps=24):
    """Per-frame mouth openness 0..3 from audio loudness."""
    hop = SR // fps
    n = len(x) // hop + 1
    out = np.zeros(n)
    for i in range(n):
        seg = x[i * hop:(i + 1) * hop]
        if len(seg):
            out[i] = np.sqrt((seg ** 2).mean())
    ref = np.percentile(out[out > 0], 90) if (out > 0).any() else 1
    k = out / (ref + 1e-9)
    m = np.zeros(n, int)
    m[k > .18] = 1
    m[k > .45] = 2
    m[k > .85] = 3
    return m


def demon_fx(x):
    """The BTC Demon: sub-octave ring-mod body + demonic layer + cathedral echo."""
    from scipy.signal import lfilter
    n = len(x)
    t = np.arange(n) / SR
    a = np.exp(-2 * np.pi * 300 / SR)
    sub = lfilter([1 - a], [1, -a], x * np.sin(2 * np.pi * 55 * t)) * 2.2
    y = demonic(x)[:n] + sub
    out = np.zeros(n + int(1.2 * SR))
    out[:n] += y
    for dly, g in ((.17, .3), (.34, .2), (.55, .13), (.8, .08)):
        i = int(dly * SR)
        out[i:i + n] += y * g
    return out / (np.abs(out).max() + 1e-9) * .95

def nick_fx(x):
    """Nick Land cyborg: the human voice + a faint metallic ring-mod layer and a tight comb (chrome throat)."""
    n = len(x); t = np.arange(n) / SR
    ring = x * np.sin(2 * np.pi * 55 * t)
    d = int(.006 * SR)
    comb = np.zeros(n); comb[d:] = x[:-d]
    y = x * .85 + ring * .22 + comb * .25
    return y / (np.abs(y).max() + 1e-9) * .95

def vhs_fx(x):
    """Old tape: slow wow/flutter and a little hiss."""
    n = len(x); t = np.arange(n) / SR
    idx = np.clip(np.arange(n) + (np.sin(2 * np.pi * .7 * t) * 30).astype(int), 0, n - 1)
    y = x[idx] + np.random.default_rng(1).normal(0, .004, n)
    return y / (np.abs(y).max() + 1e-9) * .95

def cave_fx(x):
    """Stone: long dark echo."""
    out = np.zeros(len(x) + int(1.2 * SR)); out[:len(x)] += x
    for k, g in ((.18, .45), (.41, .3), (.7, .18)):
        i = int(k * SR); out[i:i + len(x)] += x * g
    return out / (np.abs(out).max() + 1e-9) * .95

def chorus_fx(x):
    """Several Nicks at once: detuned, slightly late copies of the same voice."""
    n = len(x)
    out = np.zeros(n + int(.08 * SR)); out[:n] += x
    for rate, delay, g in ((.985, .021, .7), (1.015, .037, .6), (.97, .055, .45)):
        src = np.interp(np.arange(0, n, rate), np.arange(n), x)[:n]
        i = int(delay * SR); out[i:i + len(src)] += src * g
    return out / (np.abs(out).max() + 1e-9) * .95

def pa_fx(x):
    """Tinny public-address speaker."""
    from scipy.signal import lfilter
    a = np.exp(-2 * np.pi * 3200 / SR)
    lp = lfilter([1 - a], [1, -a], x)
    b = np.exp(-2 * np.pi * 500 / SR)
    hp = lp - lfilter([1 - b], [1, -b], lp)
    y = np.tanh(hp * 3) * .6
    out = np.zeros(len(y) + int(.5 * SR)); out[:len(y)] += y
    i = int(.12 * SR); out[i:i + len(y)] += y * .35
    return out


def monster_fx(x, deep=False):
    """Creature voice: wobbling pitch (resample warble) + gurgle tremolo + low growl layer."""
    from scipy.signal import lfilter
    n = len(x)
    t = np.arange(n) / SR
    trem = 1 + .35 * np.sin(2 * np.pi * (23 if deep else 31) * t)
    y = x * trem
    low = resample_poly(x, 4 if deep else 5, 3 if deep else 4)[:n]
    low = np.pad(low, (0, max(0, n - len(low))))
    a = np.exp(-2 * np.pi * 700 / SR)
    low = lfilter([1 - a], [1, -a], low)
    y = y * .7 + low * (.8 if deep else .5) + np.tanh(x * 5) * .15
    return (y / (np.abs(y).max() + 1e-9) * .9).astype(np.float32)
