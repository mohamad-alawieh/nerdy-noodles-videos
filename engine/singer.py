"""Singing voice for Nerdy Noodles song Shorts.

Each lyric word is spoken by a TTS voice (Kokoro for English, Piper "kareem" for Arabic), then the WORLD vocoder
re-pitches it onto the melody note(s), stretches the vowel to the note length and shifts the formants up so it
sounds like a bright, child-friendly singer. Consonants before the vowel are placed just before the beat so the
vowel lands exactly on it.

Song lines are written as tokens:  word:NOTE[/beats][,NOTE[/beats]...]
  "Wash:G4 your:E4 hands:C4/2"        one note per word (default 1 beat)
  "ta-ble:E4,D4"                      a 2-syllable word sung on two notes
  "_/1"                               a rest of 1 beat
"""
import os, re
import numpy as np

SR = 44100
KEEP_CONS = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTE_RE = re.compile(r'^([A-Ga-g])([#b]?)(-?\d)$')
SEMI = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def note_midi(n):
    m = NOTE_RE.match(n.strip())
    if not m: raise ValueError(f'bad note {n!r} (use like C4, F#4, Bb3)')
    v = SEMI[m.group(1).upper()] + {'#': 1, 'b': -1, '': 0}[m.group(2)]
    return 12 * (int(m.group(3)) + 1) + v


def parse_line(line):
    """'Wash:G4 your:E4 hands:C4/2' -> [(word, [(midi, beats), ...]), ...]; rests have word None."""
    out = []
    for tok in line.split():
        if tok.startswith('_'):
            out.append((None, [(None, float(tok.split('/')[1]) if '/' in tok else 1.0)])); continue
        if ':' not in tok: raise ValueError(f'token {tok!r} needs :NOTE')
        w, ns = tok.rsplit(':', 1)
        notes = []
        for part in ns.split(','):
            n, b = (part.split('/') + ['1'])[:2]
            notes.append((note_midi(n), float(b)))
        out.append((w.replace('-', '').replace('_', ' '), notes))
    return out


class Voices:
    def __init__(self, lang):
        self.lang = lang
        if lang == 'ar':
            import sherpa_onnx
            m = os.environ.get('NN_AR_TTS', os.path.join(ROOT, '.tts', 'vits-piper-ar_JO-kareem-medium'))
            cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=os.path.join(m, 'ar_JO-kareem-medium.onnx'),
                                                           tokens=os.path.join(m, 'tokens.txt'),
                                                           data_dir=os.path.join(m, 'espeak-ng-data'))))
            self.tts = sherpa_onnx.OfflineTts(cfg)
        else:
            from kokoro_onnx import Kokoro
            d = os.environ.get('NN_TTS_DIR', os.path.join(ROOT, '.tts'))
            self.tts = Kokoro(os.path.join(d, 'kokoro-v1.0.int8.onnx'), os.path.join(d, 'voices-v1.0.bin'))

    def say(self, word, voice='af_heart', trim=True):
        if self.lang == 'ar':
            a = self.tts.generate(word, sid=0, speed=0.9); s, sr = np.array(a.samples, float), a.sample_rate
        else:
            s, sr = self.tts.create(word, voice=voice, speed=0.9, lang='en-us'); s = np.asarray(s, float)
        s = np.interp(np.linspace(0, len(s) - 1, int(len(s) * SR / sr)), np.arange(len(s)), s)
        nz = np.where(np.abs(s) > 0.02 * np.abs(s).max())[0]
        return s[max(0, nz[0] - 100): nz[-1] + 200] if len(nz) else s


    def words(self, words, voice='af_heart'):
        """Speak the whole line naturally, then cut it into words by DTW-aligning it with the words spoken one by one.
        Natural flow sounds far clearer than gluing isolated words together (important for Arabic)."""
        import librosa
        line = self.say(' '.join(words) + '.', voice)
        if len(words) == 1: return [line]
        iso = [self.say(w, voice) for w in words]
        hop = 441
        f = lambda x: librosa.feature.mfcc(y=x.astype(np.float32), sr=SR, n_mfcc=20, hop_length=hop, n_fft=1024)
        F1, F2 = f(np.concatenate(iso)), f(line)
        _, wp = librosa.sequence.dtw(F1, F2, metric='cosine'); wp = wp[::-1]
        first = {}
        for i, j in wp: first.setdefault(int(i), int(j))
        b = np.cumsum([0] + [len(x) for x in iso]) // hop
        cuts = [first[min(int(x), F1.shape[1] - 1)] * hop for x in b[:-1]] + [len(line)]
        cuts = np.maximum.accumulate(cuts)
        segs = [line[cuts[k]:cuts[k + 1]] for k in range(len(words))]
        return [sg if len(sg) > 0.08 * SR else iso[k] for k, sg in enumerate(segs)]


def _resample_frames(a, n):
    if n <= 0: return a[:0]
    idx = np.linspace(0, len(a) - 1, n)
    lo = np.floor(idx).astype(int); hi = np.minimum(lo + 1, len(a) - 1); fr = (idx - lo)[:, None]
    return a[lo] * (1 - fr) + a[hi] * fr


def sing_word(x, notes, beat, formant=1.15, fp=5.0):
    """x: spoken word; notes: [(midi, beats)] -> (audio, lead_seconds) where lead is consonant time before the beat."""
    import pyworld as pw
    x = np.ascontiguousarray(x, dtype=np.float64)
    f0, t = pw.harvest(x, SR, f0_floor=70, f0_ceil=600, frame_period=fp)
    sp = pw.cheaptrick(x, f0, t, SR); ap = pw.d4c(x, f0, t, SR)
    voiced = np.where(f0 > 0)[0]
    if len(voiced) < 3: voiced = np.arange(len(f0))
    v0, v1 = voiced[0], voiced[-1] + 1
    head = min(v0, int(150 / fp)); tail = min(len(f0) - v1, int(90 / fp))
    hs, ts = slice(v0 - head, v0), slice(v1, v1 + tail)
    total = sum(b for _, b in notes) * beat
    sung_frames = max(4, int((total * 1000 - tail * fp) / fp))
    # split the voiced part evenly between the notes, each stretched to its own length
    seg_sp, seg_ap, seg_f0 = [], [], []
    bounds = np.linspace(v0, v1, len(notes) + 1).astype(int)
    if len(notes) > 1:  # cut syllables at the energy dips (consonants between vowels), near the even split
        en = np.log(np.sum(sp, axis=1) + 1e-12)
        span = (v1 - v0) / len(notes)
        for k in range(1, len(notes)):
            lo = int(max(bounds[k - 1] + 2, bounds[k] - 0.35 * span)); hi = int(min(v1 - 2, bounds[k] + 0.35 * span))
            if hi > lo: bounds[k] = lo + int(np.argmin(en[lo:hi]))
    used = 0
    for k, (m, b) in enumerate(notes):
        nf = int(round(b * beat * 1000 / fp)) if k < len(notes) - 1 else sung_frames - used
        nf = max(2, nf - (tail if k == len(notes) - 1 else 0) * 0)
        a0, a1 = bounds[k], max(bounds[k] + 1, bounds[k + 1])
        # keep the attack of the syllable natural, stretch the steady middle
        att = min(int(60 / fp), (a1 - a0) // 2)
        mid = _resample_frames(sp[a0 + att:a1], max(1, nf - att)); seg_sp += [sp[a0:a0 + att], mid]
        seg_ap += [ap[a0:a0 + att], _resample_frames(ap[a0 + att:a1], max(1, nf - att))]
        hz = 440 * 2 ** ((m - 69) / 12)
        tt = np.arange(nf) * fp / 1000
        vib = 1 + 0.012 * np.sin(2 * np.pi * 5.5 * tt) * np.clip((tt - 0.25) * 4, 0, 1)
        if seg_f0:  # little glide from the previous note
            prev = seg_f0[-1][-1]; g = np.minimum(1, tt / 0.05); cur = prev * (1 - g) + hz * g
        else:
            cur = np.full(nf, hz)
        seg_f0.append(cur * vib)
        used += nf
    sp2 = np.vstack([sp[hs]] + seg_sp + [sp[ts]]); ap2 = np.vstack([ap[hs]] + seg_ap + [ap[ts]])
    f2 = np.concatenate([np.zeros(head), np.concatenate(seg_f0), np.zeros(tail)])
    n = min(len(sp2), len(ap2), len(f2)); sp2, ap2, f2 = sp2[:n], ap2[:n], f2[:n]
    # keep unvoiced (s, sh, f...) frames unvoiced inside the sung part
    ap2 = np.clip(ap2, 0, 1)
    # formant shift up: brighter, younger voice
    fb = sp2.shape[1]; src = np.clip(np.arange(fb) / formant, 0, fb - 1)
    lo = np.floor(src).astype(int); hi = np.minimum(lo + 1, fb - 1); fr = src - lo
    sp2 = sp2[:, lo] * (1 - fr) + sp2[:, hi] * fr
    y = pw.synthesize(np.ascontiguousarray(f2), np.ascontiguousarray(sp2), np.ascontiguousarray(ap2), SR, fp)
    # use the ORIGINAL recording for the consonants before/after the vowel (crisper words), vocoder for the sung part
    spf = int(fp / 1000 * SR); xf = int(0.012 * SR)
    hn = head * spf
    if hn > xf and KEEP_CONS:
        orig = x[(v0 - head) * spf: v0 * spf]
        orig = orig / (np.abs(x).max() + 1e-9) * (np.abs(y).max() + 1e-9)
        m = min(len(orig), len(y)); ramp = np.linspace(1, 0, xf)
        mix = y.copy(); mix[:m - xf] = orig[:m - xf]
        mix[m - xf:m] = orig[m - xf:m] * ramp + y[m - xf:m] * (1 - ramp)
        y = mix
    tn = tail * spf
    if tn > xf and v1 * spf < len(x) and KEEP_CONS:
        orig = x[v1 * spf: v1 * spf + tn] / (np.abs(x).max() + 1e-9) * (np.abs(y).max() + 1e-9)
        st = len(y) - len(orig)
        if st > xf and len(orig) > xf:
            ramp = np.linspace(0, 1, xf)
            y[st:st + xf] = y[st:st + xf] * (1 - ramp) + orig[:xf] * ramp; y[st + xf:] = orig[xf:len(y) - st]
    env = np.ones(len(y)); r = int(0.03 * SR); env[-r:] = np.linspace(1, 0, r)
    y = y * env
    return y / (np.abs(y).max() + 1e-9), head * fp / 1000


def sing(lines, bpm, lang='en', voice='af_heart', start=0.0):
    """lines: [(t0, token_string)] -> (audio array, word timings [(t_start, t_end, line_idx, word_idx)], melody notes)."""
    beat = 60 / bpm
    V = Voices(lang)
    # Arabic voice is a man: sing an octave lower with natural formants; English voice: as written, a bit brighter
    formant, trans = (1.0, -12) if lang == 'ar' else (1.1, 0)
    events, notes_out, cache = [], [], {}
    parts = []
    for li, (t0, line) in enumerate(lines):
        t = t0; wi = 0
        toks = parse_line(line)
        ws = [w for w, _ in toks if w is not None]
        spoken = V.words(ws, voice) if lang == 'ar' else [V.say(w, voice) for w in ws]
        k = 0
        for w, notes in toks:
            dur = sum(b for _, b in notes) * beat
            if w is not None:
                y, lead = sing_word(spoken[k], [(m + trans, b) for m, b in notes], beat, formant); k += 1
                parts.append((t - lead, y))
                events.append((t, t + dur, li, wi)); wi += 1
                tn = t
                for m, b in notes: notes_out.append((tn, m, b * beat)); tn += b * beat
            t += dur
    end = max([a + len(y) / SR for a, y in parts] + [0]) + 0.5
    out = np.zeros(int(end * SR))
    for a, y in parts:
        i = max(0, int(a * SR)); m = min(len(y), len(out) - i); out[i:i + m] += y[:m]
    # gentle double-track + room so it sounds like a song, not a robot
    d = int(0.018 * SR); dbl = np.zeros_like(out); dbl[d:] = out[:-d]
    rv = np.zeros_like(out)
    for k, g in [(0.045, .25), (0.09, .15), (0.14, .08)]:
        i = int(k * SR); rv[i:] += out[:-i] * g
    out = out + 0.35 * dbl + rv
    return out / (np.abs(out).max() + 1e-9), events, notes_out


def line_beats(line):
    return sum(sum(b for _, b in notes) for _, notes in parse_line(line))
