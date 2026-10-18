"""Listen to the sung lyrics like a viewer would: sing each line alone (voice only), transcribe it with Whisper
and compare with the written lyrics. Use it before rendering a song Short.

usage: python3 engine/check_lyrics.py shorts/<id>/short.json
Prints, per line: score (0-100), what we wrote, what Whisper heard. Rewrite any line that is misheard
(especially into a different or rude word), then check again.
"""
import json, os, re, sys, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import singer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIAC = re.compile(r'[ً-ْٰـ]')


def norm(s, lang):
    s = DIAC.sub('', s.lower())
    if lang == 'ar': s = s.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه').replace('ى', 'ي')
    return re.sub(r'[^\w]+', '', s)


def main():
    import sherpa_onnx
    sj = json.load(open(sys.argv[1])); song = sj['song']; lang = song.get('lang', 'en')
    m = os.path.join(ROOT, '.tts', 'sherpa-onnx-whisper-small')
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=os.path.join(m, 'small-encoder.int8.onnx'), decoder=os.path.join(m, 'small-decoder.int8.onnx'),
        tokens=os.path.join(m, 'small-tokens.txt'), language=lang, task='transcribe')
    worst = 100
    for b in sj['beats']:
        if b['type'] != 'sing': continue
        a, _, _ = singer.sing([(0.3, b['line'])], float(song.get('bpm', 108)), lang, sj.get('voice', 'af_heart'))
        st = rec.create_stream(); st.accept_waveform(singer.SR, a.astype(np.float32)); rec.decode_stream(st)
        heard = st.result.text.strip()
        want = ' '.join(w for w, _ in singer.parse_line(b['line']) if w)
        sc = int(100 * difflib.SequenceMatcher(None, norm(want, lang), norm(heard, lang)).ratio())
        worst = min(worst, sc)
        print(f'{sc:3d}  wrote: {want}\n     heard: {heard}')
    goal = 60 if lang == 'ar' else 80
    print(f'worst line {worst} (aim >= {goal})')


if __name__ == '__main__':
    main()
