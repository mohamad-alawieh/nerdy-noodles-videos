"""Sound effects for Nerdy Noodles: real CC0 animal recordings (assets/sounds) + synthesized vehicle sounds.

    get_sound(key, sr=44100) -> numpy float array in [-1, 1], or None for an unknown key

A `.wav` in assets/sounds/<key>.wav always wins; otherwise the key is synthesized if we know how.
"""
import os, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUND_DIR = os.path.join(ROOT, 'assets', 'sounds')

# which sound each drawable kind makes (used in docs and as a default when an item says "sound": true)
KIND_SOUND = {'cow': 'cow', 'dog': 'dog', 'cat': 'cat', 'duck': 'duck', 'frog': 'frog', 'horse': 'horse',
              'owl': 'owl', 'pig': 'pig', 'rooster': 'rooster', 'sheep': 'sheep', 'bird': 'bird',
              'car': 'beep', 'bus': 'bus', 'dino': 'roar'}


def _read_wav(path, sr):
    with wave.open(path) as w:
        ch, sw, fr = w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(w.getnframes())
    x = np.frombuffer(raw, {1: np.int8, 2: np.int16, 4: np.int32}[sw]).astype(float)
    x /= float(2 ** (8 * sw - 1))
    if ch > 1: x = x.reshape(-1, ch).mean(axis=1)
    if fr != sr: x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * sr / fr)), np.arange(len(x)), x)
    return x


def _t(d, sr): return np.arange(int(d * sr)) / sr


def _lowpass(x, cutoff, sr):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / sr); X *= 1 / (1 + (f / cutoff) ** 4); return np.fft.irfft(X, len(x))


def _bandpass(x, lo, hi, sr):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / sr); X[(f < lo) | (f > hi)] = 0; return np.fft.irfft(X, len(x))


def _env(n, sr, a=0.01, r=0.05):
    e = np.ones(n); na, nr = int(a * sr), int(r * sr)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e


def _horn(sr, d, f1, f2):
    tt = _t(d, sr)
    s = np.zeros_like(tt)
    for f in (f1, f2):
        ph = 2 * np.pi * f * tt + 0.02 * np.sin(2 * np.pi * 6 * tt)
        for h in range(1, 12):  # buzzy, reed-like horn
            s += np.sin(h * ph) / h ** 0.9 * (1.0 if h % 2 else 0.6)
    s = _bandpass(s, 250, 3500, sr)
    return s * _env(len(s), sr, 0.012, 0.04)


def _beep(sr):
    a = _horn(sr, 0.22, 415, 520); gap = np.zeros(int(0.09 * sr))
    return np.concatenate([a, gap, _horn(sr, 0.34, 415, 520)])


def _honk(sr): return _horn(sr, 0.55, 415, 520)


def _bus(sr): return _horn(sr, 0.75, 262, 330)


def _vroom(sr, d=1.5):
    tt = _t(d, sr)
    rpm = 32 + 95 * np.sin(np.pi * np.clip(tt / (d * 0.7), 0, 1)) ** 1.5  # rev up then settle
    ph = np.cumsum(rpm) / sr
    pulses = (np.mod(ph, 1.0) < 0.18).astype(float)  # cylinder firing pulses
    rng = np.random.default_rng(7)
    s = _lowpass(pulses + 0.25 * rng.standard_normal(len(tt)), 900, sr)
    s += 0.4 * np.sin(2 * np.pi * ph)  # low rumble
    return s * _env(len(s), sr, 0.05, 0.25)


def _bird(sr):
    rng = np.random.default_rng(3)
    out = []
    for k in range(6):
        d = rng.uniform(0.06, 0.1); tt = _t(d, sr)
        f0, f1 = (2600, 4300) if k % 2 == 0 else (4200, 3100)
        f = np.linspace(f0, f1, len(tt)) * (1 + 0.04 * np.sin(2 * np.pi * 60 * tt))
        c = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.sin(np.pi * tt / d) ** 2
        out += [c, np.zeros(int(rng.uniform(0.04, 0.09) * sr))]
    tt = _t(0.3, sr)  # little trill at the end
    f = 3600 + 500 * np.sin(2 * np.pi * 28 * tt)
    out.append(np.sin(2 * np.pi * np.cumsum(f) / sr) * np.sin(np.pi * tt / 0.3) * 0.8)
    return np.concatenate(out)


def _roar(sr, d=1.2):
    """A friendly cartoon dino roar (not scary): low growl that rises and falls."""
    tt = _t(d, sr)
    f = 95 + 45 * np.sin(np.pi * tt / d)
    ph = np.cumsum(f) / sr
    s = sum(np.sin(2 * np.pi * h * ph) / h for h in range(1, 14))
    rng = np.random.default_rng(5)
    s = s * (1 + 0.5 * _lowpass(rng.standard_normal(len(tt)), 40, sr))
    s = _bandpass(s, 70, 2200, sr)
    return s * np.sin(np.pi * np.clip(tt / d, 0, 1)) ** 0.7


SYNTH = {'beep': _beep, 'honk': _honk, 'bus': _bus, 'vroom': _vroom, 'bird': _bird, 'tweet': _bird, 'roar': _roar}
ALIASES = {'moo': 'cow', 'woof': 'dog', 'bark': 'dog', 'meow': 'cat', 'quack': 'duck', 'ribbit': 'frog',
           'neigh': 'horse', 'hoot': 'owl', 'oink': 'pig', 'cockadoodledoo': 'rooster', 'baa': 'sheep',
           'chicken': 'rooster', 'car': 'beep', 'engine': 'vroom', 'dino': 'roar'}
_cache = {}


def sound_keys():
    files = [f[:-4] for f in os.listdir(SOUND_DIR) if f.endswith('.wav')] if os.path.isdir(SOUND_DIR) else []
    return sorted(set(files) | set(SYNTH))


def get_sound(key, sr=44100):
    if not key: return None
    key = ALIASES.get(str(key).lower(), str(key).lower())
    if (key, sr) in _cache: return _cache[(key, sr)]
    path = os.path.join(SOUND_DIR, key + '.wav')
    if os.path.exists(path): s = _read_wav(path, sr)
    elif key in SYNTH: s = SYNTH[key](sr)
    else: return None
    s = np.asarray(s, float); s = s / (np.abs(s).max() + 1e-9)
    _cache[(key, sr)] = s
    return s
