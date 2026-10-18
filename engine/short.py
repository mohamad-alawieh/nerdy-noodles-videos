"""Render a vertical Nerdy Noodles Short (funny gag, 1080x1920) from shorts/<id>/short.json.

usage:
  python3 engine/short.py shorts/<id>/short.json                 # -> short.mp4 (+ prints timeline)
  python3 engine/short.py shorts/<id>/short.json --stills 1 4 9  # preview frames
  python3 engine/short.py shorts/<id>/short.json --plan          # print beat timings only
"""
import json, math, os, random, subprocess, sys, wave
import numpy as np
import cairo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import draw as D
from draw import (INK, WHITE, YEL, RED, NUMCOL, hexc, clamp, seg, eo, eio, back, lerp, text, text_w, fit_size,
                  rrect, circle, ellipse, fill, stroke, with_alpha, draw_noodle, draw_object, scene_bg)
from hosts import draw_host, host_spec, HOST_HEAD_Y
from sfx import get_sound

VW, VH, FPS, SR = 1080, 1920, 30, 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLOOR = 1476                      # floor line after scaling the landscape scene
NX, NY, NS = 540, 1192, 1.45      # Noodle position / scale (bottom sits on the floor)
HEAD_TOP = 966
NAMED = {'center': (540, 780), 'head': (540, 905), 'left': (230, 930), 'right': (850, 930), 'top': (540, 700),
         'floor_left': (200, 1400), 'floor_right': (880, 1400), 'top_left': (250, 560), 'top_right': (830, 560),
         'nose': (540, 1130), 'hand_left': (235, 1060), 'hand_right': (845, 1060)}
OFF = {'left': (-220, 900), 'right': (1300, 900), 'top': (540, -260), 'bottom': (540, 2150),
       'top_left': (-200, 300), 'top_right': (1280, 300)}
FACES = {  # name -> (eyes, mouth, brows)
    'happy': ('happy', 'smile', False), 'normal': ('normal', 'smile', False), 'laugh': ('happy', 'laugh', False),
    'shock': ('shock', 'big_o', True), 'o': ('normal', 'o', False), 'squint': ('squint', 'achoo', False),
    'sleep': ('closed', 'smile', False), 'worried': ('shock', 'o', True), 'proud': ('closed', 'laugh', False)}


def pos_of(p, default=(540, 640)):
    if isinstance(p, (list, tuple)) and len(p) == 2: return (float(p[0]), float(p[1]))
    return NAMED.get(p, default)


class Short:
    def __init__(self, sj):
        self.sj = sj
        self.host = host_spec(sj.get('host'))
        if self.host['kind'] == 'car' and sj.get('scene') == 'road': self.host.setdefault('driving', True)
        global HEAD_TOP  # objects sit on top of whichever host stars in this Short
        if self.host['kind'] != 'noodle':
            HEAD_TOP = NY + (HOST_HEAD_Y[self.host['kind']] - 450) * NS
            NAMED['head'] = (540, HEAD_TOP - 61)
        self.compile()

    # -------------------------------------------------------------- beat compiler
    def compile(self):
        sj = self.sj
        self.objs = {}        # id -> dict(item, segs=[...], born, dies, clone_of)
        self.face_track = []  # (t, face)
        self.arms_track = []  # (t, arms)
        self.actions = []     # (t0, t1, action)
        self.bursts = []      # (t, word, color)
        self.caps = []        # (t0, t1, text)
        self.voice = []       # (t, text, maxdur)
        self.sfx = []         # (t, name)
        self.confetti = []    # t
        self.looks = []       # (t, obj id)
        self.zzz = []         # (t0, t1)
        self.song = sj.get('song')
        self.lyrics = []      # (t0, t1, [display words], [(w_t0, w_t1)], rtl)
        self.sung_lines = []  # (t0, token line) for the singer
        self.beat_len = 60.0 / float(self.song.get('bpm', 108)) if self.song else 0.5
        T = 0.0; prev_start = 0.0
        if self.song: T = prev_start = float(self.song.get('intro_beats', 2)) * self.beat_len
        self.line_start = T
        self.face_track.append((0.0, sj.get('start_face', 'normal')))
        self.arms_track.append((0.0, 'rest'))
        self.plan = []
        for b in sj['beats']:
            typ = b['type']
            start = prev_start if b.get('with_prev') else T
            if 'at_beat' in b and self.song:  # place an action on a beat of the current sung line
                start = self.line_start + float(b['at_beat']) * self.beat_len
            dur = float(b.get('dur', {'say': 0, 'enter': 1.0, 'move': 0.9, 'grow': 0.8, 'shrink': 0.8, 'pop': 0.6,
                                       'multiply': 1.2, 'burst': 0.9, 'noodle': 1.0, 'wait': 0.8, 'face': 0.4,
                                       'end': 2.2}.get(typ, 1.0)))
            if typ == 'sing':
                self.line_start = start
                from singer import parse_line
                toks = parse_line(b['line'])
                wt, tt = [], start
                for w, notes in toks:
                    d = sum(x for _, x in notes) * self.beat_len
                    if w is not None: wt.append((tt, tt + d))
                    tt += d
                dur = tt - start
                shown = b.get('show', ' '.join(w for w, _ in toks if w is not None)).split()
                if len(shown) != len(wt): shown = [w for w, _ in toks if w is not None]
                self.lyrics.append((start, start + dur, shown, wt))
                self.sung_lines.append((start, b['line']))
                if b.get('face'): self.face_track.append((start, b['face']))
                if b.get('arms'): self.arms_track.append((start, b['arms']))
            elif typ == 'say':
                est = 0.55 + len(b.get('text', '')) / 13.5
                dur = max(dur, est)
                self.voice.append((start, b['text'], dur - 0.15))
                self.caps.append((start, start + dur, b.get('caption', b['text'])))
                if b.get('face'): self.face_track.append((start, b['face']))
                if b.get('arms'): self.arms_track.append((start, b['arms']))
            elif typ == 'face':
                self.face_track.append((start, b.get('face', 'normal')))
                if b.get('arms'): self.arms_track.append((start, b['arms']))
            elif typ == 'enter':
                oid = b.get('id', 'a')
                to = pos_of(b.get('to', 'right'))
                style = b.get('style', 'bounce')
                src = b.get('from', 'right')
                p0 = to if style == 'zoom' else OFF.get(src, pos_of(src))
                sc = float(b.get('scale', 1.6))
                o = self.objs.setdefault(oid, {'item': b['obj'], 'segs': [], 'born': start, 'dies': 1e9})
                o['item'] = b['obj']; o['born'] = start
                o['segs'].append((start, start + dur, p0, to, 0.02 if style == 'zoom' else sc, sc, 0, 0, style))
                self.looks.append((start, oid))
                self.sfx.append((start, b.get('sfx', {'bounce': 'whoosh', 'slide': 'whoosh', 'fall': 'slide_down',
                                                      'zoom': 'pop'}.get(style, 'whoosh'))))
                if style in ('bounce', 'fall'): self.sfx.append((start + dur * 0.85, 'boing' if style == 'bounce' else 'thud'))
            elif typ in ('move', 'grow', 'shrink', 'spin'):
                oid = b.get('id', 'a'); o = self.objs[oid]
                last = o['segs'][-1]
                p0, s0, r0 = last[3], last[5], last[7]
                p1 = pos_of(b['to'], p0) if 'to' in b else p0
                s1 = s0
                if typ == 'grow': s1 = s0 * float(b.get('scale', 2.5))
                if typ == 'shrink': s1 = s0 * float(b.get('scale', 0.35))
                if 'scale_to' in b: s1 = float(b['scale_to'])
                style = b.get('style', 'hop' if typ == 'move' else ('wobble' if typ == 'grow' else 'slide'))
                r1 = r0 + (2 * math.pi * float(b.get('turns', 1)) if (typ == 'spin' or style == 'spin') else 0)
                if b.get('to') == 'head' or (typ in ('grow', 'shrink') and o.get('on_head') and 'to' not in b):
                    p1 = (540, HEAD_TOP - 54 * s1); o['on_head'] = True
                elif 'to' in b:
                    o['on_head'] = False
                o['segs'].append((start, start + dur, p0, p1, s0, s1, r0, r1, style))
                self.looks.append((start, oid))
                self.sfx.append((start, b.get('sfx', {'grow': 'slide_up', 'shrink': 'slide_down', 'spin': 'whoosh'}.get(typ, 'hop'))))
            elif typ == 'pop':
                oid = b.get('id', 'a'); o = self.objs[oid]
                o['dies'] = start + dur * 0.4
                p = o['segs'][-1][3]
                self.bursts.append((start + dur * 0.4, b.get('word', 'POP!'), b.get('color', '#FFD23F'), p))
                self.confetti.append(start + dur * 0.4)
                self.sfx.append((start + dur * 0.4, b.get('sfx', 'pop')))
            elif typ == 'multiply':
                oid = b.get('id', 'a'); o = self.objs[oid]
                last = o['segs'][-1]; c = last[3]; n = int(b.get('count', 5))
                rad = float(b.get('radius', 300))
                for k in range(n):
                    a = -math.pi / 2 + (k + 0.5) * 2 * math.pi / n
                    p = (clamp(c[0] + rad * math.cos(a), 110, 970), clamp(c[1] + rad * 0.8 * math.sin(a), 680, 1450))
                    t0 = start + k * dur / n * 0.8
                    cid = f'{oid}#{k}'
                    self.objs[cid] = {'item': o['item'], 'segs': [(t0, t0 + 0.35, c, p, 0.05, last[5] * 0.8, 0, 0, 'zoom')],
                                      'born': t0, 'dies': o['dies'], 'clone_of': oid}
                    self.sfx.append((t0, 'blip'))
            elif typ == 'burst':
                self.bursts.append((start, b['word'], b.get('color', '#FFD23F'), pos_of(b.get('at', 'top'))))
                self.sfx.append((start, b.get('sfx', 'boing')))
            elif typ == 'noodle':
                act = b.get('action', 'jump')
                self.actions.append((start, start + dur, act))
                self.sfx.append((start, b.get('sfx', {'jump': 'hop', 'spin': 'whoosh', 'sneeze': 'sneeze', 'shake': 'rattle',
                                                       'hairpop': 'pop', 'sleep': 'snore', 'dance': 'drum', 'grow': 'slide_up',
                                                       'tiny': 'slide_down', 'squash': 'boing', 'faint': 'slide_down'}.get(act, 'boing'))))
                if act == 'sleep': self.zzz.append((start, start + dur))
                if act == 'sneeze': self.bursts.append((start + 0.35, b.get('word', 'ACHOO!'), '#FFD23F', (540, 520)))
            elif typ == 'end':
                self.face_track.append((start, 'laugh')); self.arms_track.append((start, 'wave'))
                self.end_t = start
                dflt = 'تابِعونا لِأغانٍ أكثر!' if self.lang() == 'ar' else 'Follow for more giggles!'
                self.caps.append((start, start + dur, b.get('text', dflt)))
                if b.get('say', True): self.voice.append((start, b.get('voice', b.get('text', dflt)), dur - 0.2))
                self.sfx.append((start, 'ding'))
            if 'face' in b and typ not in ('say', 'face', 'sing'): self.face_track.append((start, b['face']))
            if 'arms' in b and typ not in ('say', 'face', 'sing'): self.arms_track.append((start, b['arms']))
            if 'sfx' in b and typ in ('wait', 'say', 'face', 'end'): self.sfx.append((start, b['sfx']))
            if b.get('confetti'): self.confetti.append(start)
            self.plan.append((round(start, 2), round(start + dur, 2), typ, b.get('show', b.get('line', b.get('text', b.get('word', b.get('action', b.get('id', ''))))))))
            prev_start = start
            if 'at_beat' not in b: T = max(T, start + dur)
        self.dur = min(58.0, T + 0.3)
        if not hasattr(self, 'end_t'): self.end_t = self.dur
        self.face_track.sort(key=lambda x: x[0]); self.arms_track.sort(key=lambda x: x[0])
        rnd = random.Random(sj.get('music_seed', 7))
        self.conf = [(rnd.uniform(0, VW), rnd.uniform(-400, -20), rnd.uniform(250, 500), rnd.uniform(-60, 60),
                      rnd.uniform(0, 6), rnd.choice(NUMCOL)) for _ in range(160)]

    def lang(self):
        return (self.song or {}).get('lang', self.sj.get('lang', 'en'))

    # -------------------------------------------------------------- state
    def obj_pose(self, o, t):
        if t < o['born'] or t >= o['dies']: return None
        segs = o['segs']
        cur = segs[0]
        for s in segs:
            if t >= s[0]: cur = s
        t0, t1, p0, p1, s0, s1, r0, r1, style = cur
        k = seg(t, t0, t1)
        x, y, sc, rot = p0[0], p0[1], s0, r0
        if style == 'bounce':
            e = eo(k); x = lerp(p0[0], p1[0], e); y = lerp(p0[1], p1[1], e) - 260 * math.sin(math.pi * min(1, k * 1.25)) * (1 - k)
            y -= 60 * abs(math.sin(k * 3 * math.pi)) * (1 - k)
            sc = lerp(s0, s1, e)
        elif style == 'fall':
            e = k * k; x = lerp(p0[0], p1[0], e); y = lerp(p0[1], p1[1], e); sc = lerp(s0, s1, k)
        elif style == 'zoom':
            x, y = lerp(p0[0], p1[0], eo(k)), lerp(p0[1], p1[1], eo(k)); sc = lerp(s0, s1, back(k) if k < 1 else 1)
        elif style == 'hop':
            e = eio(k); x = lerp(p0[0], p1[0], e); y = lerp(p0[1], p1[1], e) - 240 * math.sin(math.pi * k); sc = lerp(s0, s1, e)
        elif style == 'zip':
            e = eo(min(1, k * 1.6)); x = lerp(p0[0], p1[0], e); y = lerp(p0[1], p1[1], e); sc = lerp(s0, s1, e)
        elif style == 'wobble':
            e = back(k) if k < 1 else 1; sc = lerp(s0, s1, e) * (1 + 0.06 * math.sin(k * 30) * (1 - k))
            x, y = lerp(p0[0], p1[0], eio(k)), lerp(p0[1], p1[1], eio(k))
        else:  # slide / spin
            e = eio(k); x = lerp(p0[0], p1[0], e); y = lerp(p0[1], p1[1], e); sc = lerp(s0, s1, e)
            if style == 'spin': y -= 120 * math.sin(math.pi * k)
        rot = lerp(r0, r1, eio(k))
        # idle life
        if t >= t1:
            y += 8 * math.sin(t * 3 + hash(o['item'].get('kind', '')) % 7)
            rot += 0.08 * math.sin(t * 2.3)
        # squash on landing
        if style in ('bounce', 'fall') and t1 <= t < t1 + 0.25:
            sc *= 1 + 0.15 * math.sin(math.pi * (t - t1) / 0.25)
        return (x, y, rot, sc)

    def track_at(self, track, t):
        cur = track[0][1]
        for (tt, v) in track:
            if t >= tt: cur = v
        return cur

    # -------------------------------------------------------------- frame
    def frame(self, ctx, t):
        sj = self.sj
        ctx.save()
        shake = 0.0
        for (t0, t1, a) in self.actions:
            if a == 'shake' and t0 <= t < t1: shake = 14
        for (tb, *_r) in self.bursts:
            if 0 <= t - tb < 0.3: shake = max(shake, 10 * (1 - (t - tb) / 0.3))
        if shake: ctx.translate(shake * math.sin(t * 90), shake * math.cos(t * 77))
        # background: landscape scene scaled to cover the vertical frame
        ctx.save(); k = VH / 1080.0; ctx.translate(-(1920 * k - VW) / 2, 0); ctx.scale(k, k)
        scene_bg(ctx, t, sj.get('scene', 'kitchen')); ctx.restore()
        # brand tag
        rrect(ctx, 40, 150, 330, 74, 37); fill(ctx, WHITE, True); stroke(ctx, INK, 6)
        text(ctx, 'Nerdy Noodles', 205, 187, 40, RED)

        face = self.track_at(self.face_track, t); arms = self.track_at(self.arms_track, t)
        eyes, mouth, brows = FACES.get(face, FACES['normal'])
        cx, cy, s, sq, rot, frac = NX, NY, NS, 0.0, 0.0, 1.0
        for (t0, t1, a) in self.actions:
            if not (t0 <= t < t1 + 0.4): continue
            k = seg(t, t0, t1)
            active = t < t1
            if a == 'jump' and active:
                cy -= 340 * math.sin(math.pi * k); sq = -0.08 * math.sin(math.pi * k)
            elif a == 'spin' and active:
                rot = 2 * math.pi * eio(k); cy -= 80 * math.sin(math.pi * k)
            elif a == 'sneeze':
                if k < 0.35: eyes, mouth, sq = 'closed', 'big_o', -0.1 * (k / 0.35)
                elif active: eyes, mouth, sq = 'squint', 'achoo', 0.16 * math.cos((k - 0.35) * 20) * (1 - k)
            elif a == 'shake' and active:
                cx += 18 * math.sin(t * 60); eyes, brows = 'shock', True
            elif a == 'hairpop':
                frac = 0.0 if active else clamp((t - t1) / 0.4)
                if active: eyes, mouth, brows = 'shock', 'big_o', True
            elif a == 'sleep' and active:
                eyes, mouth = 'closed', 'smile'; sq = 0.02 * math.sin(t * 3)
            elif a == 'dance' and active:
                sq = 0.07 * abs(math.sin(math.pi * 2 * t)); arms = 'dance'; cx += 30 * math.sin(math.pi * 2 * t * 0.5)
            elif a == 'grow':
                s = NS * (lerp(1, 1.35, back(k)) if active else 1.35 - 0.35 * eo(clamp((t - t1) / 0.4)))
            elif a == 'tiny':
                s = NS * (lerp(1, 0.55, eio(k)) if active else 0.55 + 0.45 * eo(clamp((t - t1) / 0.4)))
            elif a == 'squash' and active:
                sq = 0.25 * math.sin(math.pi * k * 3) * (1 - k)
            elif a == 'faint' and active:
                eyes, mouth = 'closed', 'o'; rot = -0.35 * eio(min(1, k * 2)); cx -= 40 * eio(min(1, k * 2))
        if self.song and t < self.end_t:  # bop to the music
            ph = (t / self.beat_len) % 1
            sq += 0.045 * math.exp(-ph * 6); cx += 14 * math.sin(math.pi * t / self.beat_len)
            for (l0, l1, words, wt) in self.lyrics:
                if l0 <= t < l1:
                    for (w0, w1) in wt:
                        if w0 - 0.04 <= t < w1 - 0.05:
                            mouth = 'laugh' if (t - w0) < 0.6 * (w1 - w0) or (w1 - w0) > 0.6 else 'smile'
                            if (w1 - w0) > 0.6 and ((t - w0) // 0.3) % 2: mouth = 'o'
        # look at the most recently active object
        look = (0, 0)
        cur = None
        for (tt, oid) in self.looks:
            if t >= tt: cur = oid
        if cur and cur in self.objs:
            p = self.obj_pose(self.objs[cur], t)
            if p:
                dx, dy = p[0] - cx, p[1] - (cy - 70); d = math.hypot(dx, dy) or 1; look = (dx / d, dy / d)
        if eyes == 'normal' and (t % 3.3) < 0.12: eyes = 'closed'

        # objects behind Noodle? draw objects at y < Noodle top in front anyway (simple: all in front)
        ctx.save()
        if rot:
            ctx.translate(cx, cy + 100); ctx.rotate(rot); ctx.translate(-cx, -cy - 100)
        draw_host(ctx, self.host, t, cx, cy, s, frac, eyes, mouth, look, sq, arms, brows)
        ctx.restore()
        for oid, o in self.objs.items():
            p = self.obj_pose(o, t)
            if p: draw_object(ctx, t, o['item'], p[0], p[1], p[2], p[3], mood=o['item'].get('mood', 'happy'),
                              sun=o['item'].get('sunglasses', False))
        # Zzz
        for (t0, t1) in self.zzz:
            if t0 <= t < t1:
                for k in range(3):
                    ph = ((t - t0) * 0.8 + k / 3) % 1
                    with_alpha(ctx, 1 - ph, lambda ph=ph, k=k: text(ctx, 'Z', 700 + ph * 120, 760 - ph * 260, 60 + k * 18, WHITE, sw=8))
        # bursts
        for (tb, word, col, p) in self.bursts:
            age = t - tb
            if 0 <= age < 1.3:
                sc = back(clamp(age / 0.25)) if age < 0.25 else 1 + 0.02 * math.sin(age * 20)
                a = 1 - seg(age, 0.9, 1.3)
                y = 690

                def bw(word=word, col=col, sc=sc, y=y, age=age):
                    ctx.save(); ctx.translate(540, y); ctx.scale(sc, sc); ctx.rotate(-0.07 + 0.03 * math.sin(age * 9))
                    sz = fit_size(ctx, word, 190, 900)
                    text(ctx, word, 0, 0, sz, hexc(col), sw=sz * 0.13); ctx.restore()
                with_alpha(ctx, a, bw)
                if age < 0.35 and word:  # ring
                    circle(ctx, p[0], p[1], 40 + age * 600); ctx.set_source_rgba(1, 1, 1, 0.7 * (1 - age / 0.35))
                    ctx.set_line_width(12); ctx.stroke()
        # confetti
        for tb in self.confetti:
            dt = t - tb
            if 0 <= dt < 3.0:
                a = 1 - seg(dt, 2.2, 3.0)
                for (x, y, v, vx, r, col) in self.conf:
                    yy = y + v * dt + 160 * dt * dt
                    if yy > VH: continue
                    ctx.save(); ctx.translate(x + vx * dt + 30 * math.sin(dt * 4 + r), yy); ctx.rotate(r + dt * 5)
                    ctx.rectangle(-11, -6, 22, 12); ctx.set_source_rgba(*col, a); ctx.fill(); ctx.restore()
        # caption (top area, clear of Shorts UI)
        cap = None
        for (t0, t1, c) in self.caps:
            if t0 <= t < t1: cap = c
        lyr = None
        for L in self.lyrics:
            if L[0] - 0.25 <= t < L[1] + 0.1: lyr = L
        if lyr: self.karaoke(ctx, t, lyr)
        elif cap: self.caption(ctx, cap)
        # hook title in first 2.5 s
        hook = sj.get('hook_text')
        if hook and t < 2.5:
            a = seg(t, 0, 0.2) * (1 - seg(t, 2.1, 2.5))

            def hk():
                ctx.save(); ctx.translate(540, 330); ctx.rotate(-0.04)
                sz = fit_size(ctx, hook, 92, 940)
                rrect(ctx, -500, -80, 1000, 160, 40); fill(ctx, YEL, True); stroke(ctx, INK, 9)
                text(ctx, hook, 0, 0, sz, INK); ctx.restore()
            with_alpha(ctx, a, hk)
        ctx.restore()

    def karaoke(self, ctx, t, L):
        """Sung line in a big bubble; words light up (and bounce) exactly when they are sung."""
        l0, l1, words, wt = L
        rtl = self.lang() == 'ar'
        size = 84; gap = 0.38
        ws = [text_w(ctx, w, size) for w in words]
        tot = sum(ws) + gap * size * (len(words) - 1)
        if tot > 940: k = 940 / tot; size *= k; ws = [w * k for w in ws]; tot = 940
        bw, bh = tot + 90, size * 1.5 + 40
        x, y = VW / 2 - bw / 2, 430
        a = seg(t, l0 - 0.25, l0 - 0.05)
        ctx.save(); ctx.translate(VW / 2, y + bh / 2); ctx.scale(0.9 + 0.1 * a, 0.9 + 0.1 * a); ctx.translate(-VW / 2, -y - bh / 2)
        rrect(ctx, x, y, bw, bh, 40); ctx.set_source_rgba(1, 1, 1, 0.97); ctx.fill_preserve(); stroke(ctx, INK, 8)
        ctx.rectangle(x + 30, y + bh - 16, (bw - 60) * clamp((t - l0) / (l1 - l0)), 8); fill(ctx, hexc('#FF6B35'))
        order = list(range(len(words)))
        cxp = VW / 2 + tot / 2 if rtl else VW / 2 - tot / 2
        for i in order:
            wc = cxp - ws[i] / 2 if rtl else cxp + ws[i] / 2
            w0, w1 = wt[i] if i < len(wt) else (1e9, 1e9)
            on = t >= w0 - 0.03
            pop = 1 + 0.1 * math.sin(math.pi * clamp((t - w0) / 0.25)) if on else 1
            ctx.save(); ctx.translate(wc, y + bh / 2 - 4); ctx.scale(pop, pop)
            text(ctx, words[i], 0, 0, size, hexc('#FF6B35') if on else INK, sw=(size * 0.12 if on else 0), scol=INK)
            ctx.restore()
            step = ws[i] + gap * size
            cxp = cxp - step if rtl else cxp + step
        ctx.restore()

    def caption(self, ctx, s):
        lines = s.split('\n'); size = 62
        mw = max(text_w(ctx, l, size) for l in lines)
        if mw > 900: size = size * 900 / mw; mw = 900
        bw, bh = mw + 90, len(lines) * size * 1.28 + 40
        x, y = VW / 2 - bw / 2, 440
        rrect(ctx, x, y, bw, bh, 34); ctx.set_source_rgba(1, 1, 1, 0.97); ctx.fill_preserve(); stroke(ctx, INK, 7)
        ctx.move_to(VW / 2 - 30, y + bh - 3); ctx.line_to(VW / 2, y + bh + 40); ctx.line_to(VW / 2 + 30, y + bh - 3)
        ctx.close_path(); fill(ctx, WHITE, True); stroke(ctx, INK, 7)
        ctx.rectangle(VW / 2 - 26, y + bh - 12, 52, 10); fill(ctx, WHITE)
        for k, l in enumerate(lines):
            text(ctx, l, VW / 2, y + 20 + size * 0.64 + k * size * 1.28, size, INK)

    # -------------------------------------------------------------- audio
    def audio(self, path):
        n = int(self.dur * SR)
        rng = np.random.default_rng(self.sj.get('music_seed', 7))
        prnd = random.Random(self.sj.get('music_seed', 7))

        def et(d): return np.arange(int(d * SR)) / SR
        def mf(m): return 440 * 2 ** ((m - 69) / 12)
        def tone(m, d, dec=6, harm=((1, 1),)):
            tt = et(d); f = mf(m)
            return sum(a * np.sin(2 * np.pi * f * h * tt) for h, a in harm) * np.exp(-tt * dec) * np.minimum(1, tt * 500)
        def sweep(f0, f1, d, vib=0.0):
            tt = et(d); f = np.linspace(f0, f1, len(tt)) * (1 + vib * np.sin(2 * np.pi * 7 * tt))
            return np.sin(2 * np.pi * np.cumsum(f) / SR)
        def bp(x, lo, hi):
            X = np.fft.rfft(x); fr = np.fft.rfftfreq(len(x), 1 / SR); X[(fr < lo) | (fr > hi)] = 0; return np.fft.irfft(X, len(x))
        def noise(d): return rng.standard_normal(int(d * SR))

        music = np.zeros(n); fx = np.zeros(n)

        def add(buf, sig, at, g):
            i = int(at * SR)
            if i >= n or at < 0: return
            m = min(len(sig), n - i); buf[i:i + m] += sig[:m] * g

        sung = None
        if self.song:
            import singer
            sung, _, mel = singer.sing(self.sung_lines, float(self.song.get('bpm', 108)), self.lang(),
                                       self.sj.get('voice', 'af_heart'))
            self.song_backing(music, mel, add, tone, bp, noise, et, prnd)
        # bouncy music: 128 bpm, staccato bass + xylophone riff
        beat = 60 / 128; key = prnd.choice([0, 2, 5, -3])
        prog = prnd.choice([[60, 65, 67, 60], [60, 57, 65, 67], [60, 67, 69, 65]])
        riff = [prnd.choice([0, 4, 7, 12, 7, 4]) for _ in range(8)]
        b = 0
        while not self.song and b * beat < self.end_t:
            t = b * beat; root = prog[(b // 4) % 4] + key
            add(music, tone(root - 24, 0.25, 9, ((1, 1), (2, .3))), t, 0.35)
            if b % 2: add(music, bp(noise(0.06), 4000, 12000) * np.exp(-et(0.06) * 60), t, 0.12)
            m = root + 12 + riff[b % 8]
            if b % 4 != 3: add(music, tone(m, 0.35, 8, ((1, 1), (3.98, .3))), t, 0.15)
            b += 1
        for k, m in enumerate([72, 76, 79, 84]): add(music, tone(m + key, 1.0, 4), self.end_t + k * 0.1, 0.2)

        def place(buf, d, i):
            m = min(len(d), len(buf) - i)
            if m > 0: buf[i:i + m] += d[:m]

        def sfx(name):
            if name == 'boing':
                tt = et(0.5); return np.sin(2 * np.pi * np.cumsum(240 * (1 + 0.35 * np.sin(2 * np.pi * 14 * tt)) + 280 * tt) / SR) * np.exp(-tt * 6)
            if name == 'pop': return sweep(900, 250, 0.12) * np.exp(-et(0.12) * 20) + bp(noise(0.12), 1000, 6000) * np.exp(-et(0.12) * 40) * 0.6
            if name == 'whoosh': return bp(noise(0.5), 300, 2500) * np.sin(np.pi * et(0.5) / 0.5)
            if name == 'hop': return sweep(300, 900, 0.18) * np.exp(-et(0.18) * 8)
            if name == 'slide_up': return sweep(350, 1400, 0.7, 0.04) * np.minimum(1, et(0.7) * 20)
            if name == 'slide_down': return sweep(1400, 300, 0.7, 0.04) * np.minimum(1, et(0.7) * 20)
            if name == 'thud': return tone(40, 0.3, 14, ((1, 1), (2, .5))) + bp(noise(0.3), 50, 400) * np.exp(-et(0.3) * 30)
            if name == 'blip': return tone(prnd.choice([84, 86, 88, 91]), 0.18, 18)
            if name == 'ding': return tone(88, 1.2, 3.5, ((1, 1), (2.76, .4)))
            if name == 'sneeze': return bp(noise(0.45), 700, 5000) * np.exp(-et(0.45) * 9) * np.minimum(1, et(0.45) * 200)
            if name == 'rattle': return bp(noise(0.8), 2000, 8000) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 18 * et(0.8)))) * 0.6
            if name == 'snore':
                tt = et(1.2); return bp(noise(1.2), 80, 600) * np.sin(np.pi * tt / 1.2) * 1.5
            if name == 'drum':
                s = np.zeros(int(1.0 * SR))
                for k in range(8):
                    i = int(k * 0.11 * SR); d = bp(noise(0.08), 100, 3000) * np.exp(-et(0.08) * 40)
                    place(s, d, i)
                return s
            if name == 'honk': return np.sign(np.sin(2 * np.pi * 330 * et(0.35))) * 0.3 * np.exp(-et(0.35) * 3)
            if name == 'giggle':
                s = np.zeros(int(0.9 * SR))
                for k in range(5):
                    d = tone(84 + (k % 2) * 3, 0.12, 20); i = int(k * 0.15 * SR); place(s, d, i)
                return s
            if name == 'splat': return bp(noise(0.3), 100, 1500) * np.exp(-et(0.3) * 12) * 1.4
            if name == 'tada':
                s = np.zeros(int(1.2 * SR))
                for k, m in enumerate([72, 76, 79, 84]):
                    d = tone(m, 1.0, 3); i = int(k * 0.09 * SR); place(s, d, i)
                return s
            real = get_sound(name, SR)  # real animal recordings + vehicle sounds (cow, dog, duck, beep, vroom...)
            if real is not None: return real * 2.4
            print('WARNING: unknown sfx', name)
            return np.zeros(10)

        for (t, name) in self.sfx: add(fx, sfx(name), t, 0.32)
        voice = self.voice_track(n)
        win = int(0.25 * SR)
        env = np.convolve((np.abs(voice) > 0.02).astype(float), np.ones(win) / win, 'same')
        mix = music * (1 - 0.6 * np.clip(env * 3, 0, 1)) * 0.8 + fx * 0.9 + voice * 0.85
        if sung is not None:
            m = min(n, len(sung)); mix[:m] += sung[:m] * 0.8
        mix = mix / (np.abs(mix).max() + 1e-9) * 0.92
        fl = int(0.3 * SR); mix[-fl:] *= np.linspace(1, 0, fl)
        with wave.open(path, 'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
            wf.writeframes((mix * 32767).astype(np.int16).tobytes())

    def song_backing(self, music, mel, add, tone, bp, noise, et, prnd):
        """Nursery-song band in time with the singer: kick/clap/shaker, bass, ukulele-style chords on the
        off-beats and a quiet glockenspiel doubling the melody. Chords are picked per bar to fit the melody (C major)."""
        bl = self.beat_len; t0 = float(self.song.get('intro_beats', 2)) * bl
        chords = {'C': (0, 4, 7), 'F': (5, 9, 0), 'G': (7, 11, 2), 'Am': (9, 0, 4), 'Dm': (2, 5, 9), 'Em': (4, 7, 11)}
        bar = 4 * bl

        def chord_at(k):
            a, b = t0 + k * bar, t0 + (k + 1) * bar
            w = np.zeros(12)
            for (tn, m, d) in mel:
                ov = max(0, min(b, tn + d) - max(a, tn))
                if ov > 0: w[m % 12] += ov * (1.5 if a <= tn < a + bl else 1)
            if not w.any(): return 'C'
            best = max(['C', 'F', 'G', 'Am'], key=lambda c: sum(w[p] for p in chords[c]) + (0.01 if c == 'C' else 0))
            return best

        def pluck(f, d):  # Karplus-Strong string
            N = max(2, int(SR / f)); buf = np.random.default_rng(int(f)).uniform(-1, 1, N)
            out = np.zeros(int(d * SR))
            for i in range(len(out)):
                out[i] = buf[i % N]; buf[i % N] = 0.497 * (buf[i % N] + buf[(i + 1) % N])
            return out * np.minimum(1, et(d) * 300)
        mf = lambda m: 440 * 2 ** ((m - 69) / 12)
        cache = {}
        b = 0
        while b * bl < self.end_t + 0.01:
            t = b * bl; k = int((t - t0) // bar) if t >= t0 else -1
            ch = chord_at(k) if k >= 0 else 'C'; root = chords[ch][0]
            beat_in_bar = b % 4
            kick = np.sin(2 * np.pi * np.cumsum(np.linspace(140, 45, int(0.18 * SR))) / SR) * np.exp(-et(0.18) * 18)
            if beat_in_bar in (0, 2): add(music, kick, t, 0.55)
            if beat_in_bar in (1, 3): add(music, bp(noise(0.12), 900, 7000) * np.exp(-et(0.12) * 30), t, 0.22)
            add(music, bp(noise(0.04), 6000, 14000) * np.exp(-et(0.04) * 80), t + bl / 2, 0.09)
            if t >= t0 - 0.01:
                add(music, tone(36 + root, bl * 0.8, 7, ((1, 1), (2, .4), (3, .15))), t, 0.32)
                for j, pc in enumerate(chords[ch]):
                    key = (pc, round(bl * 0.9, 2))
                    if key not in cache: cache[key] = pluck(mf(60 + pc), bl * 0.9)
                    add(music, cache[key], t + bl / 2 + j * 0.012, 0.16)
            b += 1
        for (tn, m, d) in mel:  # glockenspiel melody
            add(music, tone(m + 12, min(0.8, d + 0.2), 6, ((1, 1), (2.76, .25))), tn, 0.07)
        for kk, m in enumerate([72, 76, 79, 84]): add(music, tone(m, 1.0, 4), self.end_t + kk * 0.1, 0.2)

    def voice_track(self, n):
        out = np.zeros(n)
        vdir = os.environ.get('NN_TTS_DIR', os.path.join(ROOT, '.tts'))
        if not self.voice: return out
        try:
            if self.lang() == 'ar':
                from singer import Voices
                k = Voices('ar').tts
            else:
                from kokoro_onnx import Kokoro
                k = Kokoro(os.path.join(vdir, 'kokoro-v1.0.int8.onnx'), os.path.join(vdir, 'voices-v1.0.bin'))
        except Exception as e:
            print('WARNING: voice engine unavailable:', e); return out
        vname = self.sj.get('voice', 'af_heart')

        def synth(txt, spd):
            if self.lang() == 'ar':
                a = k.generate(txt, sid=0, speed=spd); s, sr = a.samples, a.sample_rate
            else:
                s, sr = k.create(txt, voice=vname, speed=spd, lang='en-us')
            s = np.asarray(s, float); s = np.interp(np.linspace(0, len(s) - 1, int(len(s) * SR / sr)), np.arange(len(s)), s)
            nz = np.where(np.abs(s) > 0.01)[0]
            return s[max(0, nz[0] - 200): nz[-1] + 1500] if len(nz) else s
        for (t, txt, maxd) in self.voice:
            txt = txt.replace('\n', ' ').strip()
            if not txt: continue
            s = synth(txt, 1.1)
            if len(s) / SR > maxd > 0.3: s = synth(txt, min(1.6, 1.1 * len(s) / SR / maxd))
            s = s / (np.abs(s).max() + 1e-9)
            i = int(t * SR); m = min(len(s), n - i)
            if m > 0: out[i:i + m] += s[:m]
        return out

    def render(self, out):
        wav = out + '.wav'; self.audio(wav)
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, VW, VH); ctx = cairo.Context(surf)
        p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{VW}x{VH}',
                              '-r', str(FPS), '-i', '-', '-i', wav, '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
                              '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', '-shortest', out],
                             stdin=subprocess.PIPE)
        for f in range(int(FPS * self.dur)):
            self.frame(ctx, f / FPS); surf.flush(); p.stdin.write(bytes(surf.get_data()))
        p.stdin.close(); p.wait(); os.remove(wav)
        if p.returncode: raise SystemExit('ffmpeg failed')


def main():
    path = sys.argv[1]
    S = Short(json.load(open(path)))
    d = os.path.dirname(os.path.abspath(path))
    for row in S.plan: print(row)
    print('duration', round(S.dur, 2))
    if '--plan' in sys.argv: return
    if '--stills' in sys.argv:
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, VW, VH); ctx = cairo.Context(surf)
        for t in [float(x) for x in sys.argv[sys.argv.index('--stills') + 1:]]:
            S.frame(ctx, t); surf.write_to_png(os.path.join(d, f'still_{t:05.1f}.png'))
        return
    S.render(os.path.join(d, 'short.mp4'))
    print('rendered', os.path.join(d, 'short.mp4'))


if __name__ == '__main__':
    main()
