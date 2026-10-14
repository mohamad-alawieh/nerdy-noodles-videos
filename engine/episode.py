"""Render a Nerdy Noodles episode (video + thumbnail) from an episode.json.

usage:
  python3 engine/episode.py episodes/<id>/episode.json            # video.mp4 + thumbnail.jpg
  python3 engine/episode.py episodes/<id>/episode.json --stills 3 12 44   # preview frames only
  python3 engine/episode.py episodes/<id>/episode.json --thumb    # thumbnail only
"""
import json, math, os, random, subprocess, sys, wave
import numpy as np
import cairo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from draw import *  # noqa

FPS, DUR, SR = 30, 60.0, 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CX, CY, S = 960, 610, 1.1
BOWL_TOP = (960, 515)
BIGPOP = (390, 650)
POS = [(760, 250), (905, 160), (1075, 130), (1240, 175), (1390, 245), (1540, 160), (1690, 260),
       (1820, 160), (1500, 400), (1300, 380), (1720, 420)]


class Episode:
    def __init__(self, ep):
        self.ep = ep
        self.items = ep['items']
        self.N = N = len(self.items)
        assert 3 <= N <= 10, 'items must have 3..10 entries'
        self.twist = ep.get('twist', {})
        self.titem = self.twist.get('item', dict(self.items[-1]))
        gap = min(2.4, 15.0 / max(1, N - 1))
        tricks = [it.get('trick') for it in self.items]
        if not any(tricks):
            default = {2: 'cartwheel', 5: 'sunglasses', 7: 'bounce'} if N >= 8 else {1: 'cartwheel', N - 2: 'sunglasses'}
            tricks = [default.get(i) for i in range(N)]
        self.tricks = tricks
        self.START = [5.6 + i * gap for i in range(N)]
        self.FLYD = [1.3 if tricks[i] == 'bounce' else 0.9 for i in range(N)]
        self.LAND = [self.START[i] + self.FLYD[i] for i in range(N)]
        rg = 16.0 / N
        self.SECOND = [22.4 + i * rg for i in range(N)]
        self.POS = [POS[i % len(POS)] for i in range(N)]
        M = N + 1
        per = M if M <= 5 else math.ceil(M / 2)
        rows = 1 if M <= 5 else 2
        x0, x1 = 1360, 1840
        sp = (x1 - x0) / max(1, per - 1)
        self.slot_sc = min(0.72, sp / 140)
        ys = [720] if rows == 1 else [590, 762]
        self.SLOTS = []
        for k in range(M):
            r, c = divmod(k, per)
            self.SLOTS.append((x0 + c * sp, ys[r]))
        self.shelves = [(x0 - 60, y + 52, x1 - x0 + 110) for y in ys]
        self.noodle_kind = all(it.get('kind') == 'noodle' for it in self.items)
        self.GLASSES = (960 + 75 * S, 610 + 45 * S)
        self.lyrics = ep.get('song', [''] * 4)
        rnd = random.Random(ep.get('music_seed', 1))
        self.conf = [(rnd.uniform(0, W), rnd.uniform(-300, -20), rnd.uniform(180, 420), rnd.uniform(-60, 60),
                      rnd.uniform(0, 6), rnd.choice(NUMCOL)) for _ in range(140)]

    # -------------------------------------------------------------- timeline helpers
    def collected(self, t):
        if t < 1.05: return 0
        c = sum(1 for l in self.LAND if t >= l)
        return c + (1 if t >= 49.2 else 0)

    def item_state(self, i, t):
        """(x, y, rot, scale, where) for item i"""
        px, py = self.POS[i]; sx, sy = self.SLOTS[i]
        if t < 1.05: return None
        if t < 1.85:
            k = eo(seg(t, 1.05, 1.85)); ex, ey = BOWL_TOP
            return (lerp(ex, px, k), lerp(ey, py, k) - 120 * math.sin(math.pi * k), (i - 4.5) * 0.25 * (1 - k) + 6 * (1 - k), lerp(0.4, 1.0, k), 'air')
        if t < self.START[i]:
            return (px, py + 8 * math.sin(t * 3 + i), 0.15 * math.sin(t * 2 + i), 1.0, 'air')
        if t >= self.LAND[i]:
            bob = 0.0; sc = self.slot_sc; rot = 0.0
            if 22 <= t < 40:
                bob = -10 * abs(math.sin(math.pi * 2 * t + i)); rot = 0.12 * math.sin(math.pi * 2 * t + i)
                age = t - self.SECOND[i]
                if 0 <= age < 0.8: sc *= 1 + 0.45 * math.sin(math.pi * age / 0.8)
            if 49.2 <= t < 52: bob = -14 * abs(math.sin(t * 9 + i))
            land_age = t - self.LAND[i]
            if land_age < 0.3: sc *= 1 + 0.25 * math.sin(math.pi * land_age / 0.3)
            return (sx, sy + bob, rot, sc, 'slot')
        trick = self.tricks[i]
        if trick == 'bounce':
            g = self.GLASSES
            if t < self.START[i] + 0.55:
                k = eio(seg(t, self.START[i], self.START[i] + 0.55))
                return (lerp(px, g[0], k), lerp(py, g[1], k) - 80 * math.sin(math.pi * k), -1.2 * k, 1.0, 'air')
            k = seg(t, self.START[i] + 0.55, self.LAND[i])
            return (lerp(g[0], sx, k), lerp(g[1], sy, k) - 300 * math.sin(math.pi * k), -1.2 + 1.2 * k + 2 * math.pi * k, lerp(1, self.slot_sc, k), 'air')
        k = eio(seg(t, self.START[i], self.LAND[i]))
        spin = 4 * math.pi * k if trick == 'cartwheel' else 0.3 * math.sin(math.pi * k)
        return (lerp(px, sx, k), lerp(py, sy, k) - 220 * math.sin(math.pi * k), spin, lerp(1, self.slot_sc, k), 'air')

    def twist_state(self, t):
        if 42 <= t < 48:
            k = eo(seg(t, 42.0, 43.0))
            return (lerp(560, 735, k), 300 + 6 * math.sin(t * 6), 0.25 * math.sin(t * 9) if t > 43 else 0.0, 0.8, 'peek')
        if 48 <= t < 49.2:
            k = eio(seg(t, 48, 49.2)); sx, sy = self.SLOTS[self.N]
            return (lerp(735, sx, k), lerp(300, sy, k) - 340 * math.sin(math.pi * k), 4 * math.pi * k, lerp(0.8, self.slot_sc, k), 'air')
        if t >= 49.2:
            sx, sy = self.SLOTS[self.N]; age = t - 49.2
            sc = self.slot_sc * (1 + 0.3 * math.sin(math.pi * clamp(age / 0.3)))
            return (sx, sy - (14 * abs(math.sin(t * 9 + 3)) if t < 52 else 0), 0, sc, 'slot')
        return None

    def lyric(self, t):
        L = self.lyrics
        if 5.0 <= t < 22: return L[min(3, int((t - 5.0) / (17 / 4)))]
        if 22 <= t < 40: return L[min(3, int((t - 22) / 4.5))]
        return None

    # -------------------------------------------------------------- drawing
    def big_pop(self, ctx, t, item, age, x=BIGPOP[0], y=BIGPOP[1]):
        if age < 0 or age > 1.5: return
        sc = back(clamp(age / 0.35)) if age < 0.35 else 1.0
        a = 1 - seg(age, 1.1, 1.5)
        big = item.get('big', '')
        word = item.get('word', '')

        def draw():
            ctx.save(); ctx.translate(x, y); ctx.scale(sc, sc); ctx.rotate(0.08 * math.sin(age * 10) * (1 - clamp(age)))
            if big:
                sz = fit_size(ctx, big, 300 if len(big) <= 2 else 170, 470)
                text(ctx, big, 0, -30, sz, hexc(item.get('color', '#FF5A36')), sw=sz * 0.075)
            else:
                draw_object(ctx, t, item, 0, -40, 0, 2.3)
            if word:
                wsz = fit_size(ctx, word, 74, 480)
                text(ctx, word, 0, 130, wsz, WHITE, sw=14)
            ctx.restore()
        with_alpha(ctx, a, draw)

    def big_word(self, ctx, s, age, x, y, size, col, shake=0):
        if not s or age < 0 or age > 1.6: return
        size = fit_size(ctx, s, size, 900)
        sc = back(clamp(age / 0.3)) if age < 0.3 else 1 + 0.02 * math.sin(age * 20)
        a = 1 - seg(age, 1.2, 1.6)

        def draw():
            ctx.save()
            ctx.translate(x + shake * math.sin(age * 70), y + shake * math.cos(age * 63)); ctx.scale(sc, sc); ctx.rotate(-0.06)
            text(ctx, s, 0, 0, size, col, sw=size * 0.12); ctx.restore()
        with_alpha(ctx, a, draw)

    def confetti(self, ctx, t, tb):
        dt = t - tb
        if dt < 0 or dt > 3.2: return
        a = 1 - seg(dt, 2.4, 3.2)
        for (x, y, v, vx, r, col) in self.conf:
            yy = y + v * dt + 120 * dt * dt
            if yy > H: continue
            xx = x + vx * dt + 30 * math.sin(dt * 4 + r)
            ctx.save(); ctx.translate(xx, yy); ctx.rotate(r + dt * 5)
            ctx.rectangle(-9, -5, 18, 10); ctx.set_source_rgba(*col, a); ctx.fill(); ctx.restore()

    def frame(self, ctx, t):
        ep = self.ep; N = self.N
        cnt = self.collected(t)
        hook = ep.get('hook', {})
        ctx.save()
        if 1.0 <= t < 1.6:
            a = 16 * (1 - seg(t, 1.0, 1.6)); ctx.translate(a * math.sin(t * 90), a * math.cos(t * 77))
        scene_bg(ctx, t, ep.get('scene', 'kitchen'))
        tw = self.twist_state(t)
        if tw and tw[4] == 'peek':
            draw_object(ctx, t, self.titem, tw[0], tw[1], tw[2], tw[3])
        value = '?!' if 46 <= t < 49.2 else str(cnt)
        board(ctx, t, ep.get('board_title', 'Let\'s count!'), ep.get('board_label', 'Count:'), value)
        for (sx, sy, sw) in self.shelves:
            rrect(ctx, sx, sy, sw, 20, 8); fill(ctx, hexc('C68B59'), True); stroke(ctx, INK, 7)

        eyes, mouth, arms, brows, look, sq, dy = 'normal', 'smile', 'rest', False, (0, 0), 0.0, 0.0
        frac = (cnt / N if t < 49.2 else 1.0) if self.noodle_kind else 1.0
        beat = abs(math.sin(math.pi * 2 * t))

        def look_at(p):
            if not p: return (0, 0)
            dx, dy0 = p[0] - CX, p[1] - (CY - 60); d = math.hypot(dx, dy0) or 1
            return (dx / d, dy0 / d)

        if t < 1.0:
            eyes = 'closed' if t > 0.45 else 'normal'; mouth = 'o' if t < 0.6 else 'big_o'
            sq = -0.08 * eio(seg(t, 0.1, 1.0)); look = (0, -1)
        elif t < 1.5:
            eyes, mouth = 'squint', 'achoo'
            sq = 0.16 * math.cos((t - 1.0) * 14) * (1 - seg(t, 1.0, 1.5))
            if self.noodle_kind: frac = 0
        elif t < 5.0:
            eyes, mouth, arms, brows = 'shock', 'big_o' if t < 3.0 else 'o', 'shock', True
            if self.noodle_kind: frac = 0
            sq = 0.02 * math.sin(t * 16) * (1 - seg(t, 1.5, 2.2))
            look = (0.6 * math.sin(t * 1.5), -0.3) if t < 2.4 else (0, 0)
        elif t < 22:
            sq = 0.035 * beat
            active = [i for i in range(N) if self.START[i] - 0.4 <= t < self.LAND[i]]
            if active:
                look = look_at(self.item_state(active[0], t))
            elif t > self.LAND[-1]:
                eyes, mouth, arms = 'happy', 'laugh', 'cheer'
            for l in self.LAND:
                if 0 <= t - l < 0.25: sq += 0.09 * math.sin((t - l) / 0.25 * math.pi)
            for i in range(N):
                if self.tricks[i] == 'bounce' and self.START[i] + 0.5 <= t < self.START[i] + 0.85:
                    eyes, mouth = 'closed', 'o'
        elif t < 40:
            sq = 0.06 * beat; arms = 'dance'; mouth = 'laugh' if int(t * 2) % 2 else 'smile'
            eyes = 'happy' if int(t) % 4 == 0 else 'normal'; look = (0.7 * math.sin(t * math.pi), 0)
        elif t < 42:
            eyes, mouth, arms = 'happy', 'laugh', 'cheer'
            dy = -70 * math.sin(math.pi * seg(t, 40.1, 40.8)) - 40 * math.sin(math.pi * seg(t, 40.9, 41.4))
        elif t < 46:
            mouth = 'smile' if t < 44 else 'o'
            look = (0, 0) if t < 42.6 else (-1, -0.6)
        elif t < 48:
            eyes, mouth, arms, brows = 'shock', 'big_o', 'shock', True
            look = (-1, -0.6); sq = 0.03 * math.sin(t * 30) * (1 - seg(t, 46, 46.6))
        elif t < 49.2:
            eyes, mouth, brows = 'shock', 'o', True; look = look_at(tw)
        elif t < 52:
            eyes, mouth, arms = 'happy', 'laugh', 'cheer'
            sq = 0.05 * math.sin(t * 22) + (0.1 * math.sin(seg(t, 49.2, 49.45) * math.pi) if t < 49.45 else 0)
        else:
            eyes, mouth, arms = 'normal', 'smile', 'wave'; sq = 0.02 * math.sin(t * 4)
            if int(t * 1.3) % 3 == 2: eyes = 'happy'
        if eyes == 'normal' and (t % 3.7) < 0.12: eyes = 'closed'

        draw_noodle(ctx, t, CX, CY + dy, S, frac, eyes, mouth, look, sq, arms, brows)
        for i in range(N):
            st = self.item_state(i, t)
            if st is None: continue
            mood = 'worried' if (1.85 <= t < self.START[i] and t < 5.6) else 'happy'
            draw_object(ctx, t, self.items[i], st[0], st[1], st[2], st[3], mood=mood, sun=(self.tricks[i] == 'sunglasses'))
        if tw and tw[4] != 'peek':
            draw_object(ctx, t, self.titem, tw[0], tw[1], tw[2], tw[3])

        # overlays
        self.big_word(ctx, hook.get('burst', 'ACHOO!'), t - 1.0, 960, 150, 190, YEL, shake=10)
        if 0.15 <= t < 1.0 and hook.get('pre'):
            with_alpha(ctx, seg(t, 0.15, 0.3), lambda: text(ctx, hook['pre'], 1450, 300, fit_size(ctx, hook['pre'], 80, 760), WHITE, sw=12))
        for i in range(N):
            self.big_pop(ctx, t, self.items[i], t - self.LAND[i])
            self.big_pop(ctx, t, self.items[i], t - self.SECOND[i])
        self.big_pop(ctx, t, self.titem, t - 49.2)
        self.big_word(ctx, ep.get('celebrate_word', 'YAY!'), t - 40.05, 1450, 330, 200, YEL)
        self.big_word(ctx, self.twist.get('reveal_word', self.twist.get('reveal', 'WHAT?!')), t - 46.0, 1360, 250, 170, hexc('FF6FB5'), shake=8)
        if 22 <= t < 40:
            a = seg(t, 22, 22.4) * (1 - seg(t, 39.6, 40))

            def badge():
                ctx.save(); ctx.translate(1600, 140 if len(self.SLOTS) > 6 else 140); ctx.rotate(0.08 + 0.05 * math.sin(t * 6))
                rrect(ctx, -190, -55, 380, 110, 55); fill(ctx, YEL, True); stroke(ctx, INK, 8)
                text(ctx, "Sing along!", 0, 0, 58, INK); ctx.restore()
            with_alpha(ctx, a, badge)
        self.confetti(ctx, t, 40.0); self.confetti(ctx, t, 49.2)

        cap = None
        if 2.1 <= t < 5.0: cap = hook.get('line_caption', hook.get('line'))
        elif self.lyric(t): cap = self.lyric(t)
        elif 40.0 <= t < 42.4: cap = ep.get('celebrate')
        elif 42.6 <= t < 46.0: cap = self.twist.get('peek_line', "Wait... who's that?")
        elif 46.0 <= t < 48.0: cap = self.twist.get('reveal')
        elif 49.3 <= t < 52.0: cap = self.twist.get('laugh_caption', self.twist.get('laugh'))
        elif 52.2 <= t < 56.6: cap = ep.get('outro_caption', ep.get('outro'))
        caption(ctx, cap)
        ctx.restore()

        if t >= 56.5:
            k = eo(seg(t, 56.5, 57.2))
            circle(ctx, 960, 540, 1200 * k); fill(ctx, YEL)
            if t >= 56.9:
                k2 = seg(t, 56.9, 57.4)
                ctx.save(); ctx.translate(960, 430); sc = back(k2) if k2 < 1 else 1; ctx.scale(sc, sc)
                circle(ctx, 0, 0, 250); fill(ctx, BLUE, True); stroke(ctx, INK, 12)
                ctx.save(); circle(ctx, 0, 0, 244); ctx.clip()
                draw_noodle(ctx, t, 0, 30, 0.55, 1.0, 'happy' if int(t * 2) % 3 == 0 else 'normal', 'smile', (0, 0),
                            0.03 * math.sin(t * 8), 'wave', shadow=False)
                ctx.restore(); ctx.restore()
            k3 = seg(t, 57.3, 57.8)
            if k3 > 0:
                ctx.save(); ctx.translate(960, 790); sc = back(k3) if k3 < 1 else 1 + 0.015 * math.sin(t * 6); ctx.scale(sc, sc)
                text(ctx, "Nerdy Noodles", 0, 0, 150, RED, sw=20); ctx.restore()
            k4 = seg(t, 58.0, 58.4)
            with_alpha(ctx, k4, lambda: text(ctx, "Subscribe for more fun learning!", 960, 930, 56, INK))

    # -------------------------------------------------------------- thumbnail
    def thumbnail(self, path):
        ep = self.ep; th = ep.get('thumbnail', {})
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(surf)
        scene_bg(ctx, 0.3, ep.get('scene', 'kitchen'))
        cx, cy = 1350, 560
        for k in range(0, 24, 2):
            a0 = k * 2 * math.pi / 24
            ctx.move_to(cx, cy); ctx.line_to(cx + 2500 * math.cos(a0), cy + 2500 * math.sin(a0))
            ctx.line_to(cx + 2500 * math.cos(a0 + math.pi / 24), cy + 2500 * math.sin(a0 + math.pi / 24)); ctx.close_path()
        ctx.set_source_rgba(1, 1, 1, 0.12); ctx.fill()
        expr = th.get('expression', 'shock')
        if expr == 'happy':
            draw_noodle(ctx, 0.3, 1370, 640, 1.45, 1.0, 'happy', 'laugh', (0, 0), 0, 'cheer')
        else:
            draw_noodle(ctx, 0.3, 1370, 640, 1.45, 0.0 if self.noodle_kind else 1.0, 'shock', 'big_o', (0, -0.6), 0.0, 'shock', brows=True)
        spots = [(1050, 230, -0.4), (1220, 120, -0.2), (1420, 90, 0.2), (1610, 150, 0.4), (1780, 300, 0.6),
                 (1830, 520, 0.8), (980, 430, -0.6), (1790, 760, 1.0)]
        for k, (x, y, r) in enumerate(spots):
            it = self.items[k % self.N]
            draw_object(ctx, 1.0 + k, it, x, y, r, 1.25, sun=(k == 3))
        burst = th.get('burst', ep.get('hook', {}).get('burst', ''))
        if burst:
            ctx.save(); ctx.translate(1290, 330); ctx.rotate(-0.08)
            text(ctx, burst, 0, 0, fit_size(ctx, burst, 120, 520), YEL, sw=16); ctx.restore()
        lines = th.get('lines', ['COUNT', 'WITH', 'NOODLE!'])
        cols = [YEL, WHITE, hexc('FF6FB5')]
        ys = [250, 440, 620] if len(lines) == 3 else ([300, 540] if len(lines) == 2 else [400])
        for k, l in enumerate(lines[:3]):
            base = [200, 140, 180][k] if len(lines) == 3 else 200
            sz = fit_size(ctx, l, base, 880)
            ctx.save(); ctx.translate(500, ys[k]); ctx.rotate(-0.05)
            text(ctx, l, 0, 0, sz, INK, sw=sz * 0.34)
            text(ctx, l, 0, 0, sz, cols[k % 3], sw=sz * 0.16, scol=WHITE)
            ctx.restore()
        st = th.get('sticker', 'OOPS!')
        if st:
            ctx.save(); ctx.translate(400, 840); ctx.rotate(-0.12)
            ssz = fit_size(ctx, st, 120, 380)
            rrect(ctx, -230, -85, 460, 170, 85); fill(ctx, RED, True); stroke(ctx, INK, 12)
            text(ctx, st, 0, 0, ssz, WHITE, sw=14); ctx.restore()
        badges = [(820, 870), (950, 820), (1080, 870)] if any(it.get('big') for it in self.items) else []
        for k, (x, y) in enumerate(badges):
            it = self.items[k % self.N]
            circle(ctx, x, y, 62); fill(ctx, NUMCOL[k + 1], True); stroke(ctx, INK, 10)
            b = it.get('big') or str(k + 1)
            text(ctx, b, x, y, fit_size(ctx, b, 84, 90), WHITE, sw=10)
        surf.write_to_png(path + '.png')
        from PIL import Image
        Image.open(path + '.png').convert('RGB').resize((1280, 720), Image.LANCZOS).save(path, quality=92)
        os.remove(path + '.png')

    # -------------------------------------------------------------- audio
    def music_and_fx(self):
        ep = self.ep
        buf = np.zeros(int(SR * (DUR + 1)))
        rng = np.random.default_rng(ep.get('music_seed', 3))
        prnd = random.Random(ep.get('music_seed', 3))

        def add(sig, at, g=1.0):
            i = int(at * SR)
            if i >= len(buf) or at < 0: return
            n = min(len(sig), len(buf) - i); buf[i:i + n] += sig[:n] * g

        def mf(m): return 440 * 2 ** ((m - 69) / 12)

        def env_t(d): return np.arange(int(d * SR)) / SR

        def xylo(m, d=0.9):
            f = mf(m); tt = env_t(d)
            return (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * 3.98 * f * tt) * np.exp(-tt * 25)) * np.exp(-tt * 6.5) * np.minimum(1, tt * 400)

        def pluck(m, d=0.7):
            f = mf(m); tt = env_t(d)
            s = sum(np.sin(2 * np.pi * f * h * tt) * a * np.exp(-tt * (4 + h * 2)) for h, a in ((1, 1), (2, .5), (3, .3), (4, .15)))
            return s * np.minimum(1, tt * 600)

        def bass(m, d=0.45):
            f = mf(m); tt = env_t(d)
            return (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 5) * np.minimum(1, tt * 300)

        def bell(m, d=1.4):
            f = mf(m); tt = env_t(d)
            return (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * 2.76 * f * tt) * np.exp(-tt * 6) + 0.25 * np.sin(2 * np.pi * 5.4 * f * tt) * np.exp(-tt * 12)) * np.exp(-tt * 3.5) * np.minimum(1, tt * 800)

        def bp(x, lo, hi):
            X = np.fft.rfft(x); fr = np.fft.rfftfreq(len(x), 1 / SR); X[(fr < lo) | (fr > hi)] = 0; return np.fft.irfft(X, len(x))

        def sweep(f0, f1, d, vib=0):
            tt = env_t(d); f = np.linspace(f0, f1, len(tt)) * (1 + vib * np.sin(2 * np.pi * 7 * tt))
            return np.sin(2 * np.pi * np.cumsum(f) / SR)

        key = prnd.choice([0, 2, -3, 5, -1])
        CH = {'C': [60, 64, 67, 72], 'F': [60, 65, 69, 72], 'G': [59, 62, 67, 71], 'Am': [60, 64, 69, 72], 'Dm': [62, 65, 69, 74]}
        RT = {'C': 36, 'F': 41, 'G': 43, 'Am': 45, 'Dm': 38}
        prog = prnd.choice([['C', 'F', 'G', 'C'], ['C', 'Am', 'F', 'G'], ['C', 'G', 'Am', 'F'], ['F', 'G', 'C', 'C'], ['C', 'Dm', 'G', 'C']])
        # melody: 4 bars x 4 beats from chord tones, random walk
        mel = []
        prev = 76
        for b in range(4):
            tones = sorted(set(m + 12 for m in CH[prog[b]]) | set(m + 24 for m in CH[prog[b]][:2]))
            pattern = prnd.choice([[1, 1, 1, 1], [1, 1, 2], [2, 1, 1], [0.5, 0.5, 1, 2], [1, 0.5, 0.5, 2]])
            bt = 0
            for ln in pattern:
                cand = sorted(tones, key=lambda m: abs(m - prev) + prnd.random() * 4)
                n = cand[prnd.randint(0, 1)]
                mel.append((b * 4 + bt, n, ln)); prev = n; bt += ln

        def lvl(t):
            if t < 5 or 46 <= t < 49.2 or t >= 56.5: return 0
            if 40 <= t < 46: return 0.6
            return 1

        for b in range(120):
            t = 5.0 + b * 0.5
            lv = lvl(t)
            if lv == 0: continue
            bar = (b // 4) % 4; bi = b % 4
            for j, m in enumerate(CH[prog[bar]]):
                add(pluck(m + key), t + j * 0.012, 0.09 * lv * (1 if bi % 2 == 0 else 0.6))
            if bi in (0, 2): add(bass(RT[prog[bar]] + key), t, 0.32 * lv)
            n = rng.standard_normal(int(0.05 * SR)) * np.exp(-env_t(0.05) * 80)
            add(bp(n, 5000, 12000), t + 0.25, 0.08 * lv)
        for ph in range(8):
            base = 5.0 + ph * 8
            for (bt, m, ln) in mel:
                t = base + bt * 0.5
                if (5 <= t < 40) or (52 <= t < 56.5): add(xylo(m + key, 0.5 * ln + 0.5), t, 0.22 if t < 40 else 0.14)

        add(xylo(79, 0.6), 0.25, 0.18); add(xylo(81, 0.6), 0.65, 0.2)
        n = rng.standard_normal(int(0.45 * SR)); tt = env_t(0.45)
        add(bp(n, 700, 5000) * np.exp(-tt * 9) * np.minimum(1, tt * 200), 1.0, 0.9)
        add(sweep(900, 200, 0.6) * np.exp(-env_t(0.6) * 4), 1.05, 0.15)
        w = rng.standard_normal(int(0.8 * SR)); add(bp(w, 300, 2500) * np.sin(np.pi * env_t(0.8) / 0.8), 1.05, 0.35)
        for k, m in enumerate([84, 83, 82, 81]): add(xylo(m, 0.7), 2.1 + k * 0.28, 0.18)

        scale = [72, 74, 76, 77, 79, 81, 83, 84, 86, 88]
        for i in range(self.N):
            add(sweep(500, 1100, 0.18) * np.exp(-env_t(0.18) * 15), self.START[i], 0.08)
            add(bell(scale[i] + key), self.LAND[i], 0.26)
            add(bell(scale[i] + key, 1.0), self.SECOND[i], 0.12)
            if self.tricks[i] == 'bounce':
                tt = env_t(0.5)
                boing = np.sin(2 * np.pi * np.cumsum(220 * (1 + 0.35 * np.sin(2 * np.pi * 14 * tt)) + 300 * tt) / SR) * np.exp(-tt * 6)
                add(boing, self.START[i] + 0.55, 0.35)
            if self.tricks[i] == 'cartwheel':
                add(bp(rng.standard_normal(int(0.6 * SR)), 400, 3000) * np.sin(np.pi * env_t(0.6) / 0.6), self.START[i] + 0.1, 0.18)
        for k, m in enumerate([72, 76, 79, 84]): add(bell(m), 40.0 + k * 0.1, 0.2)
        for k in range(10): add(bell(int(rng.integers(86, 98)), 0.6), 40.1 + k * 0.12, 0.06)
        add(xylo(91, 0.4), 42.9, 0.12); add(xylo(88, 0.4), 43.2, 0.12)
        add(sweep(600, 1500, 0.45, vib=0.03) * np.minimum(1, env_t(0.45) * 30), 46.0, 0.25)
        add(sweep(400, 1300, 1.0, vib=0.04) * np.sin(np.pi * env_t(1.0)), 48.1, 0.2)
        add(bell(91), 49.2, 0.28)
        for k, m in enumerate([84, 88, 91, 96, 91, 88, 84, 88, 91, 96]): add(xylo(m, 0.3), 49.3 + k * 0.08, 0.1)
        for k, m in enumerate([72, 76, 79, 84]): add(xylo(m, 1.0), 56.5 + k * 0.12, 0.22)
        d = 0.9; tt = env_t(d)
        noise = bp(rng.standard_normal(len(tt)), 0, 500)
        car = np.sin(2 * np.pi * np.cumsum(np.linspace(250, 1800, len(tt))) / SR)
        slurp = noise * car * np.sin(np.pi * tt / d) * (1 + 0.5 * np.sin(2 * np.pi * 16 * tt))
        add(slurp / (np.abs(slurp).max() + 1e-9), 57.3, 0.45)
        for m in [48, 60, 64, 67, 72, 76]: add(pluck(m, 2.4), 58.3, 0.12)
        add(bell(84, 2.0), 58.3, 0.15)
        buf = buf[:int(DUR * SR)]
        return buf / max(1e-9, np.abs(buf).max())

    def voice_track(self, n):
        ep = self.ep
        voice = np.zeros(n)
        vdir = os.environ.get('NN_TTS_DIR', os.path.join(ROOT, '.tts'))
        try:
            from kokoro_onnx import Kokoro
            k = Kokoro(os.path.join(vdir, 'kokoro-v1.0.int8.onnx'), os.path.join(vdir, 'voices-v1.0.bin'))
        except Exception as e:
            print('WARNING: voice engine unavailable:', e); return voice
        vname = ep.get('voice', 'af_heart')
        try:
            if vname not in k.get_voices(): vname = 'af_heart'
        except Exception:
            pass
        hook = ep.get('hook', {}); tw = self.twist
        cues = [(1.0, hook.get('burst_say', hook.get('burst', 'Achoo!')), 1.1, 1.0), (2.1, hook.get('line', ''), 1.15, 1.0)]
        for i, it in enumerate(self.items):
            cues.append((self.LAND[i] + 0.02, it.get('say', it.get('word', '')), 1.0, 1.0))
            cues.append((self.SECOND[i] + 0.02, it.get('say', it.get('word', '')), 1.0, 0.8))
        cues += [(40.05, ep.get('celebrate', ''), 1.05, 1.0), (42.6, tw.get('peek_line', "Wait... who's that?"), 1.0, 1.0),
                 (46.0, tw.get('reveal', ''), 1.0, 1.0), (49.22, self.titem.get('say', ''), 1.05, 1.0),
                 (50.2, tw.get('laugh', ''), 1.1, 1.0), (52.2, ep.get('outro', ''), 1.15, 1.0)]
        limits = {2.1: 2.8, 40.05: 2.4, 42.6: 3.3, 46.0: 2.0, 50.2: 1.9, 52.2: 4.2}
        for at, txt, spd, g in cues:
            txt = (txt or '').replace('\n', ' ').strip()
            if not txt: continue
            s, sr = k.create(txt, voice=vname, speed=spd, lang='en-us')
            s = np.asarray(s, float)
            s = np.interp(np.linspace(0, len(s) - 1, int(len(s) * SR / sr)), np.arange(len(s)), s)
            nz = np.where(np.abs(s) > 0.01)[0]
            if len(nz) == 0: continue
            s = s[max(0, nz[0] - 200): nz[-1] + 2000]
            lim = limits.get(at)
            if lim and len(s) / SR > lim:  # too long for its slot: speed up
                s2, sr = k.create(txt, voice=vname, speed=min(1.5, spd * (len(s) / SR) / lim), lang='en-us')
                s = np.asarray(s2, float); s = np.interp(np.linspace(0, len(s) - 1, int(len(s) * SR / sr)), np.arange(len(s)), s)
                nz = np.where(np.abs(s) > 0.01)[0]; s = s[max(0, nz[0] - 200): nz[-1] + 2000]
            s = s / (np.abs(s).max() + 1e-9) * g
            i = int(at * SR); m = min(len(s), n - i)
            voice[i:i + m] += s[:m]
        return voice

    def audio(self, path):
        music = self.music_and_fx() * 0.9
        voice = self.voice_track(len(music))
        win = int(0.25 * SR)
        env = np.convolve((np.abs(voice) > 0.02).astype(float), np.ones(win) / win, 'same')
        mix = music * (1 - 0.55 * np.clip(env * 3, 0, 1)) + voice * 0.8
        mix = mix / np.abs(mix).max() * 0.92
        fl = int(0.4 * SR); mix[-fl:] *= np.linspace(1, 0, fl)
        with wave.open(path, 'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
            wf.writeframes((mix * 32767).astype(np.int16).tobytes())

    def render(self, out_mp4):
        wav = out_mp4 + '.wav'
        self.audio(wav)
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(surf)
        p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}',
                              '-r', str(FPS), '-i', '-', '-i', wav, '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
                              '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', '-shortest', out_mp4],
                             stdin=subprocess.PIPE)
        for f in range(int(FPS * DUR)):
            self.frame(ctx, f / FPS); surf.flush(); p.stdin.write(bytes(surf.get_data()))
        p.stdin.close(); p.wait(); os.remove(wav)
        if p.returncode != 0: raise SystemExit('ffmpeg failed')


def main():
    path = sys.argv[1]
    ep = json.load(open(path))
    E = Episode(ep)
    d = os.path.dirname(os.path.abspath(path))
    if '--stills' in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index('--stills') + 1:]]
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(surf)
        for t in ts:
            E.frame(ctx, t); surf.write_to_png(os.path.join(d, f'still_{t:05.1f}.png'))
        return
    E.thumbnail(os.path.join(d, 'thumbnail.jpg'))
    if '--thumb' in sys.argv: return
    E.render(os.path.join(d, 'video.mp4'))
    print('rendered', os.path.join(d, 'video.mp4'))


if __name__ == '__main__':
    main()
