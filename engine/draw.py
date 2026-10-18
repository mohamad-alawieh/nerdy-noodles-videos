"""Nerdy Noodles drawing library: helpers, the Noodle mascot, objects and scenes (pycairo)."""
import math, random
import cairo
import rtl

W, H = 1920, 1080
FONT = "Poppins"


def hexc(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


INK = hexc('1E1E2E'); BLUE = hexc('3A86FF'); CREAM = hexc('FFE29A'); GOLD = hexc('E9A62C')
RED = hexc('FF5A36'); RED2 = hexc('E04423'); DARKRED = hexc('B8341C'); PINK = hexc('FF9FB8')
YEL = hexc('FFD23F'); ERASER = hexc('FF8FB1'); WHITE = (1, 1, 1); GREEN = hexc('2F5D50')
WOOD = hexc('8B5A2B'); CLOTH = hexc('FF6B6B')
NUMCOL = [hexc(c) for c in ['FF5A36', 'FFB627', '2EC4B6', '8E5CF7', 'FF6FB5', '3DDC84', 'FF8C42', '00B4D8', 'F15BB5', 'FFD23F', 'FF5A36']]


# ------------------------------------------------------------------ math / easing
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def seg(t, a, b): return clamp((t - a) / (b - a)) if b > a else float(t >= b)
def eo(x): return 1 - (1 - x) ** 3
def eio(x): return x * x * (3 - 2 * x)
def back(x):
    c = 1.9
    return max(0.02, 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2)
def lerp(a, b, k): return a + (b - a) * k


# ------------------------------------------------------------------ path helpers
def quad_to(ctx, cx, cy, x, y):
    x0, y0 = ctx.get_current_point()
    ctx.curve_to(x0 + 2 / 3 * (cx - x0), y0 + 2 / 3 * (cy - y0), x + 2 / 3 * (cx - x), y + 2 / 3 * (cy - y), x, y)


def wavy(ctx, x0, y0, n, w, a, ph=0.0):
    ctx.move_to(x0, y0)
    for k in range(n):
        s = -1 if k % 2 == 0 else 1
        amp = a * (1 + 0.25 * math.sin(ph + k))
        x = x0 + (k + 1) * w
        quad_to(ctx, x - w / 2, y0 + s * amp, x, y0)


def stroke(ctx, col, w, keep=False):
    ctx.set_source_rgb(*col); ctx.set_line_width(w)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke_preserve() if keep else ctx.stroke()


def fill(ctx, col, keep=False):
    ctx.set_source_rgb(*col)
    ctx.fill_preserve() if keep else ctx.fill()


def ellipse(ctx, cx, cy, rx, ry):
    ctx.new_sub_path()
    ctx.save(); ctx.translate(cx, cy); ctx.scale(rx, ry); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore()


def circle(ctx, cx, cy, r):
    ctx.new_sub_path(); ctx.arc(cx, cy, r, 0, 2 * math.pi)


def rrect(ctx, x, y, w, h, r):
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0); ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi); ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def poly(ctx, pts):
    ctx.move_to(*pts[0])
    for p in pts[1:]: ctx.line_to(*p)
    ctx.close_path()


def text(ctx, s, x, y, size, col, sw=0, scol=INK):
    if rtl.has_arabic(s):  # shaped right-to-left Arabic with the bundled Arabic font
        ctx.new_path(); rtl.path(ctx, s, x - rtl.width(s, size) / 2, y + size * 0.3, size)
        if sw: stroke(ctx, scol, sw, keep=True)
        fill(ctx, col); return
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(size)
    xa = ctx.text_extents(s)[4]
    ctx.move_to(x - xa / 2, y + size * 0.36)
    ctx.text_path(s)
    if sw: stroke(ctx, scol, sw, keep=True)
    fill(ctx, col)


def text_w(ctx, s, size):
    if rtl.has_arabic(s): return rtl.width(s, size)
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(size)
    return ctx.text_extents(s)[4]


def fit_size(ctx, s, size, maxw):
    w = text_w(ctx, s, size)
    return size if w <= maxw else size * maxw / w


def with_alpha(ctx, a, fn):
    if a <= 0: return
    if a >= 1: fn(); return
    ctx.push_group(); fn(); ctx.pop_group_to_source(); ctx.paint_with_alpha(a)


# ------------------------------------------------------------------ Noodle mascot
def draw_noodle(ctx, t, cx, cy, s, frac=1.0, eyes='normal', mouth='smile', look=(0, 0), sq=0.0,
                arms='rest', brows=False, shadow=True):
    if shadow:
        ellipse(ctx, cx, cy + 200 * s, 250 * s * (1 - sq * 0.3), 22 * s)
        ctx.set_source_rgba(0, 0, 0, 0.16); ctx.fill()
    ctx.save()
    ctx.translate(cx, cy)
    by = 196 * s
    ctx.translate(0, by); ctx.scale(1 + sq * 0.6, 1 - sq); ctx.translate(0, -by)
    ctx.scale(s, s); ctx.translate(-400, -450)

    if arms == 'rest': ar = al = 1.05 + 0.05 * math.sin(t * 4)
    elif arms == 'wave': al = 1.05; ar = -1.05 + 0.45 * math.sin(t * 11)
    elif arms == 'cheer': al = ar = -1.15 + 0.25 * math.sin(t * 12)
    elif arms == 'shock': al = ar = -0.35
    elif arms == 'dance':
        al = -0.6 + 0.9 * math.sin(t * math.pi * 2); ar = -0.6 - 0.9 * math.sin(t * math.pi * 2)
    else: al = ar = 1.05
    for side, a in ((1, ar), (-1, al)):
        sx, sy = 400 + side * 215, 470
        hx, hy = sx + side * 120 * math.cos(a), sy + 120 * math.sin(a)
        mx, my = (sx + hx) / 2 + side * 15, (sy + hy) / 2 - 15
        ctx.move_to(sx, sy); quad_to(ctx, mx, my, hx, hy); stroke(ctx, INK, 16)
        circle(ctx, hx, hy, 24); fill(ctx, WHITE, True); stroke(ctx, INK, 9)

    ctx.save(); ctx.translate(560, 230); ctx.rotate(math.radians(35)); ctx.translate(-560, -230)
    rrect(ctx, 535, 90, 50, 230, 8); fill(ctx, YEL, True); stroke(ctx, INK, 10)
    rrect(ctx, 535, 70, 50, 40, 10); fill(ctx, ERASER, True); stroke(ctx, INK, 10)
    ctx.move_to(560, 115); ctx.line_to(560, 318); stroke(ctx, hexc('E8B21C'), 8)
    ctx.restore()

    ellipse(ctx, 400, 382, 233, 34); fill(ctx, DARKRED, True); stroke(ctx, INK, 10)
    if frac > 0.01:
        k = eo(clamp(frac))
        ellipse(ctx, 400, 380 - 8 * k, 215 * (0.55 + 0.45 * k), 78 * k + 8)
        fill(ctx, CREAM, True); stroke(ctx, INK, 10)
        rows = [(215, 375, 6, 60), (240, 338, 5, 60), (290, 304, 4, 54)]
        nrows = 1 if frac < 0.35 else (2 if frac < 0.7 else 3)
        for (x0, y0, n, w) in rows[:nrows]:
            yy = 380 - (380 - y0) * k
            wavy(ctx, x0 + (1 - k) * 60, yy, n, w * (0.8 + 0.2 * k), 50 * k, t * 6); stroke(ctx, GOLD, 11)
        if frac > 0.95:
            wig = 6 * math.sin(t * 5)
            for col, wd in ((INK, 10), (CREAM, 6)):
                ctx.move_to(330, 296); quad_to(ctx, 300 + wig, 226, 350, 206); quad_to(ctx, 390, 192, 380, 232)
                stroke(ctx, col, wd)
                ctx.move_to(455, 292); quad_to(ctx, 465, 232 - wig, 510, 240); stroke(ctx, col, wd)

    ctx.move_to(165, 380); quad_to(ctx, 165, 625, 400, 625); quad_to(ctx, 635, 625, 635, 380); ctx.close_path()
    fill(ctx, RED, True); stroke(ctx, INK, 12)
    rrect(ctx, 325, 612, 150, 34, 14); fill(ctx, RED2, True); stroke(ctx, INK, 12)
    ctx.move_to(190, 420); quad_to(ctx, 400, 455, 610, 420)
    ctx.set_source_rgba(1, 1, 1, 0.5); ctx.set_line_width(10); ctx.stroke()
    ellipse(ctx, 250, 548, 30, 18); fill(ctx, PINK)
    ellipse(ctx, 550, 548, 30, 18); fill(ctx, PINK)

    lr = 64 if eyes == 'shock' else 58
    ctx.move_to(267, 488); ctx.line_to(225, 470); stroke(ctx, INK, 14)
    ctx.move_to(533, 488); ctx.line_to(575, 470); stroke(ctx, INK, 14)
    for ex in (325, 475):
        circle(ctx, ex, 495, lr); fill(ctx, WHITE, True); stroke(ctx, INK, 14)
        lx, ly = look
        if eyes in ('normal', 'shock'):
            pr = 13 if eyes == 'shock' else 22
            px, py = ex + 6 + lx * 16, 500 + ly * 16
            circle(ctx, px, py, pr); fill(ctx, INK)
            circle(ctx, px + pr * 0.35, py - pr * 0.35, pr * 0.32); fill(ctx, WHITE)
        elif eyes == 'happy':
            ctx.move_to(ex - 24, 508); quad_to(ctx, ex, 470, ex + 24, 508); stroke(ctx, INK, 12)
        elif eyes == 'closed':
            ctx.move_to(ex - 24, 498); quad_to(ctx, ex, 510, ex + 24, 498); stroke(ctx, INK, 12)
        elif eyes == 'squint':
            d = 1 if ex < 400 else -1
            ctx.move_to(ex - 24 * d, 488); ctx.line_to(ex + 18 * d, 500); ctx.line_to(ex - 24 * d, 512)
            stroke(ctx, INK, 12)
    ctx.move_to(383, 492); quad_to(ctx, 400, 476, 417, 492); stroke(ctx, INK, 14)
    if brows:
        for ex in (325, 475):
            ctx.move_to(ex - 30, 410); quad_to(ctx, ex, 392, ex + 30, 410); stroke(ctx, INK, 12)

    if mouth == 'smile':
        ctx.move_to(360, 572); quad_to(ctx, 400, 606, 440, 572); stroke(ctx, INK, 13)
    elif mouth == 'o':
        ellipse(ctx, 400, 585, 20, 25); fill(ctx, INK)
    elif mouth == 'big_o':
        ellipse(ctx, 400, 585, 34, 30); fill(ctx, INK)
    elif mouth == 'achoo':
        ellipse(ctx, 400, 582, 48, 26); fill(ctx, INK)
    elif mouth == 'laugh':
        ctx.move_to(352, 565); quad_to(ctx, 400, 630, 448, 565); ctx.close_path(); fill(ctx, INK)
        ellipse(ctx, 400, 592, 18, 9); fill(ctx, hexc('FF6B8A'))
    ctx.restore()


# ------------------------------------------------------------------ objects
def _face(ctx, x=0, y=0, s=1.0, mood='happy', sun=False):
    if sun:
        rrect(ctx, x - 22 * s, y - 14 * s, 19 * s, 13 * s, 4 * s); fill(ctx, INK)
        rrect(ctx, x + 3 * s, y - 14 * s, 19 * s, 13 * s, 4 * s); fill(ctx, INK)
        ctx.move_to(x - 4 * s, y - 9 * s); ctx.line_to(x + 4 * s, y - 9 * s); stroke(ctx, INK, 4 * s)
    else:
        circle(ctx, x - 11 * s, y - 7 * s, 5.5 * s); fill(ctx, INK)
        circle(ctx, x + 11 * s, y - 7 * s, 5.5 * s); fill(ctx, INK)
        circle(ctx, x - 9.5 * s, y - 8.5 * s, 1.8 * s); fill(ctx, WHITE)
        circle(ctx, x + 12.5 * s, y - 8.5 * s, 1.8 * s); fill(ctx, WHITE)
    if mood == 'worried':
        ellipse(ctx, x, y + 9 * s, 5 * s, 6 * s); fill(ctx, INK)
    else:
        ctx.move_to(x - 10 * s, y + 5 * s); quad_to(ctx, x, y + 15 * s, x + 10 * s, y + 5 * s); stroke(ctx, INK, 4 * s)


def _shape_path(ctx, shape, r):
    if shape == 'circle': circle(ctx, 0, 0, r)
    elif shape == 'square': rrect(ctx, -r * .9, -r * .9, r * 1.8, r * 1.8, r * .15)
    elif shape == 'rectangle': rrect(ctx, -r * 1.2, -r * .7, r * 2.4, r * 1.4, r * .12)
    elif shape == 'triangle': poly(ctx, [(0, -r), (r * 1.05, r * .8), (-r * 1.05, r * .8)])
    elif shape == 'diamond': poly(ctx, [(0, -r * 1.1), (r * .8, 0), (0, r * 1.1), (-r * .8, 0)])
    elif shape == 'oval': ellipse(ctx, 0, 0, r * 1.2, r * .78)
    elif shape == 'pentagon': poly(ctx, [(r * math.cos(-math.pi / 2 + k * 2 * math.pi / 5), r * math.sin(-math.pi / 2 + k * 2 * math.pi / 5)) for k in range(5)])
    elif shape == 'hexagon': poly(ctx, [(r * math.cos(k * math.pi / 3), r * math.sin(k * math.pi / 3)) for k in range(6)])
    elif shape == 'star': _star_path(ctx, r * 1.1, r * .5)
    elif shape == 'heart': _heart_path(ctx, r)
    elif shape == 'moon':
        ctx.new_sub_path(); ctx.arc(0, 0, r, math.radians(-60), math.radians(240))
        ctx.arc_negative(r * .45, -r * .2, r * .75, math.radians(200), math.radians(-40)); ctx.close_path()
    else: circle(ctx, 0, 0, r)


def _star_path(ctx, R, r):
    poly(ctx, [((R if k % 2 == 0 else r) * math.cos(-math.pi / 2 + k * math.pi / 5),
                (R if k % 2 == 0 else r) * math.sin(-math.pi / 2 + k * math.pi / 5)) for k in range(10)])


def _heart_path(ctx, r):
    ctx.move_to(0, r * .95)
    ctx.curve_to(-r * 1.5, -r * .1, -r * .75, -r * 1.2, 0, -r * .45)
    ctx.curve_to(r * .75, -r * 1.2, r * 1.5, -r * .1, 0, r * .95); ctx.close_path()


def darker(c, k=0.75): return tuple(v * k for v in c)


OBJECT_KINDS = ['noodle', 'star', 'heart', 'ball', 'balloon', 'apple', 'fish', 'cupcake', 'block', 'shape',
                'egg', 'cookie', 'leaf', 'car', 'duck', 'sock', 'planet', 'flower', 'dino', 'bubble',
                'tree', 'cat', 'dog', 'cow', 'pig', 'frog', 'bird', 'bus', 'sheep', 'horse', 'rooster', 'owl']


def draw_object(ctx, t, item, x, y, rot=0.0, sc=1.0, mood='happy', sun=False, alpha=1.0):
    kind = item.get('kind', 'ball')
    col = hexc(item.get('color', '#FFB627'))
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(sc, sc)
    if alpha < 1: ctx.push_group()
    ph = t * 9 + x * 0.01
    face_xy = (0, 0); fs = 1.0
    if kind == 'noodle':
        for c, wd in ((INK, 24), (CREAM if 'color' not in item else col, 14)):
            ctx.move_to(-80, 0)
            for k in range(4):
                s = -1 if k % 2 == 0 else 1
                quad_to(ctx, -80 + k * 36 + 18, s * 26 * math.sin(ph + k * 0.6 + 1.2), -80 + (k + 1) * 36, 0)
            stroke(ctx, c, wd)
        circle(ctx, 76, -4, 24); fill(ctx, CREAM if 'color' not in item else col, True); stroke(ctx, INK, 7)
        face_xy = (76, 0); fs = 0.85
    elif kind == 'star':
        _star_path(ctx, 66, 30); fill(ctx, col, True); stroke(ctx, INK, 8); face_xy = (0, 6)
    elif kind == 'heart':
        _heart_path(ctx, 58); fill(ctx, col, True); stroke(ctx, INK, 8); face_xy = (0, -6)
    elif kind == 'ball':
        circle(ctx, 0, 0, 56); fill(ctx, col, True); stroke(ctx, INK, 8)
        ctx.save(); circle(ctx, 0, 0, 52); ctx.clip()
        ctx.move_to(-60, 20); quad_to(ctx, 0, 50, 60, 20); stroke(ctx, WHITE, 12); ctx.restore()
        face_xy = (0, -8)
    elif kind == 'balloon':
        ctx.move_to(0, 60); quad_to(ctx, 18 * math.sin(ph), 90, 0, 125); stroke(ctx, INK, 4)
        ellipse(ctx, 0, 0, 46, 58); fill(ctx, col, True); stroke(ctx, INK, 8)
        poly(ctx, [(0, 56), (-9, 68), (9, 68)]); fill(ctx, col, True); stroke(ctx, INK, 5)
        ellipse(ctx, -18, -26, 8, 14); ctx.set_source_rgba(1, 1, 1, 0.6); ctx.fill()
    elif kind == 'apple':
        ctx.move_to(0, -44); quad_to(ctx, 4, -62, 10, -70); stroke(ctx, WOOD, 8)
        ellipse(ctx, 22, -60, 18, 9); fill(ctx, hexc('3DDC84'), True); stroke(ctx, INK, 5)
        ctx.move_to(0, -40); ctx.curve_to(-30, -62, -70, -40, -60, 4); ctx.curve_to(-52, 50, -20, 62, 0, 50)
        ctx.curve_to(20, 62, 52, 50, 60, 4); ctx.curve_to(70, -40, 30, -62, 0, -40); ctx.close_path()
        fill(ctx, col, True); stroke(ctx, INK, 8)
    elif kind == 'fish':
        poly(ctx, [(-40, 0), (-80, -32), (-80, 32)]); fill(ctx, darker(col), True); stroke(ctx, INK, 7)
        ellipse(ctx, 0, 0, 60, 38); fill(ctx, col, True); stroke(ctx, INK, 8)
        face_xy = (24, -2); fs = 0.85
    elif kind == 'cupcake':
        poly(ctx, [(-44, 0), (44, 0), (32, 58), (-32, 58)]); fill(ctx, col, True); stroke(ctx, INK, 7)
        for k in range(-2, 3):
            ctx.move_to(k * 14, 4); ctx.line_to(k * 11, 54); stroke(ctx, darker(col), 4)
        ctx.move_to(-52, 4); ctx.curve_to(-60, -30, -20, -40, -10, -48); ctx.curve_to(0, -70, 30, -50, 20, -40)
        ctx.curve_to(50, -40, 62, -10, 52, 4); ctx.close_path(); fill(ctx, hexc('FFD1E3'), True); stroke(ctx, INK, 7)
        circle(ctx, 8, -62, 12); fill(ctx, RED, True); stroke(ctx, INK, 5)
        face_xy = (0, -14); fs = 0.9
    elif kind == 'block':
        rrect(ctx, -54, -54, 108, 108, 14); fill(ctx, col, True); stroke(ctx, INK, 8)
        rrect(ctx, -42, -42, 84, 84, 10); ctx.set_source_rgba(1, 1, 1, 0.35); ctx.fill()
        text(ctx, item.get('text', 'A'), 0, -4, 78, WHITE, sw=10)
        face_xy = None
    elif kind == 'shape':
        _shape_path(ctx, item.get('shape', 'circle'), 56); fill(ctx, col, True); stroke(ctx, INK, 8)
        face_xy = (0, 4 if item.get('shape') == 'triangle' else 0)
    elif kind == 'egg':
        ellipse(ctx, 0, 6, 44, 58); fill(ctx, col, True); stroke(ctx, INK, 8)
        ctx.move_to(-40, 10); ctx.line_to(-20, 0); ctx.line_to(0, 12); ctx.line_to(20, 0); ctx.line_to(40, 10)
        stroke(ctx, WHITE, 6); face_xy = (0, 26)
    elif kind == 'cookie':
        circle(ctx, 0, 0, 56); fill(ctx, hexc('E0A458'), True); stroke(ctx, INK, 8)
        for (cx2, cy2) in [(-30, -20), (28, -26), (-24, 30), (32, 22), (4, 38)]:
            circle(ctx, cx2, cy2, 7); fill(ctx, darker(hexc('8B5A2B'), 0.8))
    elif kind == 'leaf':
        ctx.move_to(-60, 30); ctx.curve_to(-50, -50, 40, -60, 64, -34); ctx.curve_to(50, 40, -20, 56, -60, 30); ctx.close_path()
        fill(ctx, col, True); stroke(ctx, INK, 8)
        ctx.move_to(-56, 28); quad_to(ctx, 0, -6, 58, -32); stroke(ctx, darker(col, 0.6), 5)
        face_xy = (2, 14); fs = 0.8
    elif kind == 'car':
        rrect(ctx, -70, -10, 140, 50, 18); fill(ctx, col, True); stroke(ctx, INK, 8)
        ctx.move_to(-40, -10); quad_to(ctx, -30, -48, 0, -48); quad_to(ctx, 34, -48, 44, -10); ctx.close_path()
        fill(ctx, col, True); stroke(ctx, INK, 8)
        rrect(ctx, -26, -38, 52, 24, 8); fill(ctx, hexc('BDE7FF'), True); stroke(ctx, INK, 5)
        for wx in (-40, 40):
            circle(ctx, wx, 42, 18); fill(ctx, INK); circle(ctx, wx, 42, 7); fill(ctx, (0.8, 0.8, 0.8))
        face_xy = (-48, 12); fs = 0.6
    elif kind == 'duck':
        ellipse(ctx, -6, 20, 58, 36); fill(ctx, col, True); stroke(ctx, INK, 8)
        circle(ctx, 22, -26, 32); fill(ctx, col, True); stroke(ctx, INK, 8)
        poly(ctx, [(48, -24), (76, -16), (48, -6)]); fill(ctx, hexc('FF8C42'), True); stroke(ctx, INK, 5)
        face_xy = (20, -26); fs = 0.75
    elif kind == 'sock':
        ctx.move_to(-24, -62); ctx.line_to(24, -62); ctx.line_to(24, 16); quad_to(ctx, 70, 20, 64, 46)
        quad_to(ctx, 60, 64, 20, 62); ctx.line_to(-6, 62); quad_to(ctx, -26, 60, -24, 30); ctx.close_path()
        fill(ctx, col, True); stroke(ctx, INK, 8)
        rrect(ctx, -26, -64, 52, 18, 6); fill(ctx, WHITE, True); stroke(ctx, INK, 5)
        face_xy = (0, -12); fs = 0.8
    elif kind == 'planet':
        circle(ctx, 0, 0, 48); fill(ctx, col, True); stroke(ctx, INK, 8)
        ctx.save(); ctx.scale(1, 22 / 92); ctx.new_path(); ctx.arc(0, 0, 92, -0.25, math.pi + 0.25); ctx.restore()
        stroke(ctx, INK, 12, keep=True); stroke(ctx, hexc('FFD23F'), 6)
        face_xy = (0, -10); fs = 0.85
    elif kind == 'flower':
        for k in range(6):
            a = k * math.pi / 3 + 0.3 * math.sin(t * 2)
            ellipse(ctx, 40 * math.cos(a), 40 * math.sin(a), 26, 26); fill(ctx, col, True); stroke(ctx, INK, 6)
        circle(ctx, 0, 0, 32); fill(ctx, YEL, True); stroke(ctx, INK, 7)
        fs = 0.8
    elif kind == 'dino':
        ctx.move_to(-70, 30); quad_to(ctx, -90, -10, -50, 0)
        ctx.curve_to(-40, -40, 20, -40, 30, -10); ctx.line_to(30, -40); quad_to(ctx, 34, -70, 64, -60)
        quad_to(ctx, 84, -50, 70, -30); ctx.line_to(56, -30); ctx.line_to(52, 20); quad_to(ctx, 40, 48, 0, 48)
        ctx.line_to(-40, 48); ctx.close_path(); fill(ctx, col, True); stroke(ctx, INK, 8)
        for k in range(4):
            poly(ctx, [(-40 + k * 18, -26 + abs(k - 1.5) * 4), (-31 + k * 18, -44 + abs(k - 1.5) * 4), (-22 + k * 18, -26 + abs(k - 1.5) * 4)])
            fill(ctx, darker(col), True); stroke(ctx, INK, 4)
        for lx in (-30, 20):
            rrect(ctx, lx, 40, 18, 22, 6); fill(ctx, col, True); stroke(ctx, INK, 6)
        face_xy = (58, -48); fs = 0.55
    elif kind == 'bubble':
        circle(ctx, 0, 0, 54); ctx.set_source_rgba(*col, 0.45); ctx.fill_preserve(); stroke(ctx, INK, 6)
        ellipse(ctx, -20, -22, 10, 16); ctx.set_source_rgba(1, 1, 1, 0.8); ctx.fill()
    elif kind == 'tree':
        rrect(ctx, -15, 4, 30, 58, 8); fill(ctx, hexc('9C6B3E'), True); stroke(ctx, INK, 7)
        blobs = [(0, -26, 42), (-34, -2, 28), (34, -2, 28)]
        for (bx, by, r) in blobs: circle(ctx, bx, by, r)
        ctx.set_source_rgb(*INK); ctx.set_line_width(16); ctx.stroke()
        for (bx, by, r) in blobs: circle(ctx, bx, by, r)
        fill(ctx, col)
        face_xy = (0, -18); fs = 0.85
    elif kind == 'cat':
        for sd in (-1, 1):
            poly(ctx, [(sd * 16, -36), (sd * 44, -66), (sd * 46, -16)]); fill(ctx, col, True); stroke(ctx, INK, 7)
            poly(ctx, [(sd * 24, -36), (sd * 40, -54), (sd * 40, -26)]); fill(ctx, PINK)
        ellipse(ctx, 0, 4, 54, 46); fill(ctx, col, True); stroke(ctx, INK, 8)
        for sd in (-1, 1):
            for dy in (-2, 8):
                ctx.move_to(sd * 26, 10 + dy); ctx.line_to(sd * 62, 4 + dy * 1.8); stroke(ctx, INK, 3)
        poly(ctx, [(-6, 6), (6, 6), (0, 13)]); fill(ctx, hexc('FF6B8A'))
        face_xy = (0, 2); fs = 0.95
    elif kind == 'dog':
        for sd in (-1, 1):
            ctx.save(); ctx.translate(sd * 46, -2); ctx.rotate(sd * 0.35)
            ellipse(ctx, 0, 0, 16, 36); fill(ctx, darker(col, 0.65), True); stroke(ctx, INK, 7); ctx.restore()
        ellipse(ctx, 0, 0, 48, 46); fill(ctx, col, True); stroke(ctx, INK, 8)
        ellipse(ctx, 0, 24, 26, 18); fill(ctx, hexc('FFF1E0'), True); stroke(ctx, INK, 5)
        ellipse(ctx, 0, 14, 10, 7); fill(ctx, INK)
        circle(ctx, -11, -12, 5.5); fill(ctx, INK); circle(ctx, 11, -12, 5.5); fill(ctx, INK)
        circle(ctx, -9.5, -13.5, 1.8); fill(ctx, WHITE); circle(ctx, 12.5, -13.5, 1.8); fill(ctx, WHITE)
        ctx.move_to(-9, 26); quad_to(ctx, 0, 34, 9, 26); stroke(ctx, INK, 4)
        face_xy = None
    elif kind == 'cow':
        for sd in (-1, 1):
            poly(ctx, [(sd * 22, -38), (sd * 34, -62), (sd * 38, -34)]); fill(ctx, hexc('FFF3B0'), True); stroke(ctx, INK, 6)
            ctx.save(); ctx.translate(sd * 52, -20); ctx.rotate(sd * -0.5)
            ellipse(ctx, 0, 0, 22, 11); fill(ctx, WHITE, True); stroke(ctx, INK, 6); ctx.restore()
        ellipse(ctx, 0, 0, 46, 48); fill(ctx, WHITE, True); stroke(ctx, INK, 8)
        ctx.save(); ellipse(ctx, 0, 0, 42, 44); ctx.clip()
        ellipse(ctx, -30, -24, 18, 14); fill(ctx, INK); ellipse(ctx, 32, -6, 12, 16); fill(ctx, INK); ctx.restore()
        ellipse(ctx, 0, 28, 34, 20); fill(ctx, hexc('FFB3C6'), True); stroke(ctx, INK, 6)
        circle(ctx, -11, 28, 4.5); fill(ctx, INK); circle(ctx, 11, 28, 4.5); fill(ctx, INK)
        face_xy = None
        circle(ctx, -14, -10, 5.5); fill(ctx, INK); circle(ctx, 14, -10, 5.5); fill(ctx, INK)
        circle(ctx, -12.5, -11.5, 1.8); fill(ctx, WHITE); circle(ctx, 15.5, -11.5, 1.8); fill(ctx, WHITE)
    elif kind == 'pig':
        for sd in (-1, 1):
            poly(ctx, [(sd * 18, -40), (sd * 46, -56), (sd * 44, -22)]); fill(ctx, col, True); stroke(ctx, INK, 7)
        circle(ctx, 0, 0, 50); fill(ctx, col, True); stroke(ctx, INK, 8)
        ellipse(ctx, 0, 14, 22, 15); fill(ctx, darker(col, 0.85), True); stroke(ctx, INK, 5)
        ellipse(ctx, -7, 14, 4, 6); fill(ctx, INK); ellipse(ctx, 7, 14, 4, 6); fill(ctx, INK)
        circle(ctx, -16, -16, 5.5); fill(ctx, INK); circle(ctx, 16, -16, 5.5); fill(ctx, INK)
        circle(ctx, -14.5, -17.5, 1.8); fill(ctx, WHITE); circle(ctx, 17.5, -17.5, 1.8); fill(ctx, WHITE)
        ctx.move_to(-10, 34); quad_to(ctx, 0, 41, 10, 34); stroke(ctx, INK, 4)
        face_xy = None
    elif kind == 'frog':
        ellipse(ctx, 0, 14, 60, 40); fill(ctx, col, True); stroke(ctx, INK, 8)
        for sd in (-1, 1):
            circle(ctx, sd * 28, -22, 20); fill(ctx, col, True); stroke(ctx, INK, 7)
            circle(ctx, sd * 28, -22, 11); fill(ctx, WHITE)
            circle(ctx, sd * 28 + 2, -21, 6); fill(ctx, INK)
        ctx.move_to(-34, 14); quad_to(ctx, 0, 40, 34, 14); stroke(ctx, INK, 5)
        ellipse(ctx, -40, 22, 9, 6); fill(ctx, PINK); ellipse(ctx, 40, 22, 9, 6); fill(ctx, PINK)
        face_xy = None
    elif kind == 'bird':
        poly(ctx, [(-40, 0), (-70, -18), (-66, 14)]); fill(ctx, darker(col), True); stroke(ctx, INK, 6)
        for lx in (-10, 10):
            ctx.move_to(lx, 40); ctx.line_to(lx, 56); stroke(ctx, hexc('FF8C42'), 5)
        circle(ctx, 0, 0, 46); fill(ctx, col, True); stroke(ctx, INK, 8)
        ctx.save(); ctx.translate(-12, 12); ctx.rotate(0.25 * math.sin(ph))
        ellipse(ctx, 0, 0, 24, 15); fill(ctx, darker(col, 0.82), True); stroke(ctx, INK, 6); ctx.restore()
        poly(ctx, [(40, -8), (64, 0), (40, 8)]); fill(ctx, hexc('FF8C42'), True); stroke(ctx, INK, 5)
        face_xy = (14, -10); fs = 0.75
    elif kind == 'bus':
        rrect(ctx, -84, -48, 168, 86, 16); fill(ctx, col, True); stroke(ctx, INK, 8)
        for k in range(3):
            rrect(ctx, -70 + k * 38, -36, 30, 26, 6); fill(ctx, hexc('BDE7FF'), True); stroke(ctx, INK, 4)
        rrect(ctx, 46, -36, 26, 50, 6); fill(ctx, hexc('BDE7FF'), True); stroke(ctx, INK, 4)
        circle(ctx, 76, 22, 6); fill(ctx, hexc('FFF3B0'), True); stroke(ctx, INK, 3)
        for wx in (-50, 46):
            circle(ctx, wx, 42, 17); fill(ctx, INK); circle(ctx, wx, 42, 7); fill(ctx, (0.8, 0.8, 0.8))
        face_xy = (-30, 14); fs = 0.6
    elif kind == 'sheep':
        for lx in (-22, 22):
            rrect(ctx, lx - 7, 30, 14, 30, 5); fill(ctx, INK)
        wool = [(-34, -6, 26), (0, -20, 28), (34, -6, 26), (-30, 22, 24), (0, 28, 26), (30, 22, 24)]
        for (bx, by, r) in wool: circle(ctx, bx, by, r)
        ctx.set_source_rgb(*INK); ctx.set_line_width(14); ctx.stroke()
        for (bx, by, r) in wool: circle(ctx, bx, by, r)
        fill(ctx, WHITE if 'color' not in item else col)
        for sd in (-1, 1):
            ellipse(ctx, sd * 30, -6, 12, 7); fill(ctx, hexc('3B3B4F'), True); stroke(ctx, INK, 4)
        ellipse(ctx, 0, 4, 26, 32); fill(ctx, hexc('3B3B4F'), True); stroke(ctx, INK, 6)
        circle(ctx, -9, -4, 4.5); fill(ctx, WHITE); circle(ctx, 9, -4, 4.5); fill(ctx, WHITE)
        circle(ctx, -8, -4, 2.4); fill(ctx, INK); circle(ctx, 10, -4, 2.4); fill(ctx, INK)
        ctx.move_to(-7, 18); quad_to(ctx, 0, 24, 7, 18); stroke(ctx, WHITE, 3)
        face_xy = None
    elif kind == 'horse':
        for sd in (-1, 1):
            poly(ctx, [(sd * 12, -46), (sd * 28, -70), (sd * 32, -40)]); fill(ctx, col, True); stroke(ctx, INK, 6)
        ctx.save(); ctx.rotate(0.12)
        ellipse(ctx, 0, 0, 36, 56); fill(ctx, col, True); stroke(ctx, INK, 8)
        ellipse(ctx, 0, 34, 28, 22); fill(ctx, darker(col, 0.8), True); stroke(ctx, INK, 6)
        circle(ctx, -9, 36, 4); fill(ctx, INK); circle(ctx, 9, 36, 4); fill(ctx, INK)
        for k in range(2):  # forelock
            ellipse(ctx, -4 + k * 8, -50 + k * 10, 10, 13); fill(ctx, hexc('6B3E1F'), True); stroke(ctx, INK, 4)
        circle(ctx, -14, -14, 5.5); fill(ctx, INK); circle(ctx, 14, -14, 5.5); fill(ctx, INK)
        circle(ctx, -12.5, -15.5, 1.8); fill(ctx, WHITE); circle(ctx, 15.5, -15.5, 1.8); fill(ctx, WHITE)
        ctx.move_to(-10, 48); quad_to(ctx, 0, 54, 10, 48); stroke(ctx, INK, 3)
        ctx.restore(); face_xy = None
    elif kind == 'rooster':
        poly(ctx, [(-30, 0), (-74, -40), (-62, 0), (-78, 10), (-40, 24)]); fill(ctx, hexc('2EC4B6'), True); stroke(ctx, INK, 6)
        for lx in (-10, 12):
            ctx.move_to(lx, 40); ctx.line_to(lx, 60); stroke(ctx, hexc('FF8C42'), 6)
        ellipse(ctx, 0, 10, 44, 38); fill(ctx, col, True); stroke(ctx, INK, 8)
        circle(ctx, 22, -26, 26); fill(ctx, col, True); stroke(ctx, INK, 7)
        for k in range(3):
            circle(ctx, 8 + k * 12, -54 + abs(k - 1) * 4, 9); fill(ctx, hexc('FF3B30'), True); stroke(ctx, INK, 4)
        poly(ctx, [(44, -28), (62, -22), (44, -16)]); fill(ctx, hexc('FFB627'), True); stroke(ctx, INK, 4)
        ellipse(ctx, 42, -8, 6, 10); fill(ctx, hexc('FF3B30'), True); stroke(ctx, INK, 3)
        face_xy = (22, -24); fs = 0.7
    elif kind == 'owl':
        ellipse(ctx, 0, 6, 46, 56); fill(ctx, col, True); stroke(ctx, INK, 8)
        for sd in (-1, 1):
            poly(ctx, [(sd * 20, -40), (sd * 36, -66), (sd * 42, -34)]); fill(ctx, col, True); stroke(ctx, INK, 6)
        ellipse(ctx, 0, 24, 26, 26); fill(ctx, hexc('FFF1E0'), True); stroke(ctx, INK, 5)
        for sd in (-1, 1):
            circle(ctx, sd * 18, -14, 15); fill(ctx, WHITE, True); stroke(ctx, INK, 5)
            circle(ctx, sd * 18 + 2, -13, 7); fill(ctx, INK)
        poly(ctx, [(-6, 0), (6, 0), (0, 12)]); fill(ctx, hexc('FFB627'), True); stroke(ctx, INK, 3)
        face_xy = None
    else:
        circle(ctx, 0, 0, 56); fill(ctx, col, True); stroke(ctx, INK, 8)
    if face_xy is not None:
        _face(ctx, face_xy[0], face_xy[1], fs, mood, sun)
    if alpha < 1:
        ctx.pop_group_to_source(); ctx.paint_with_alpha(alpha)
    ctx.restore()


# ------------------------------------------------------------------ scenes
SCENES = ['kitchen', 'space', 'ocean', 'park', 'classroom', 'candy', 'jungle', 'snow', 'road', 'farm', 'forest',
          'pond', 'sky', 'night', 'city']
_rnd = random.Random(11)
_FLOAT = [(_rnd.uniform(0, W), _rnd.uniform(0, 820), _rnd.choice('1234567890+=ABC'), _rnd.uniform(60, 120), _rnd.uniform(0, 6)) for _ in range(16)]
_STARS = [(_rnd.uniform(0, W), _rnd.uniform(0, 820), _rnd.uniform(2, 6), _rnd.uniform(0, 6)) for _ in range(90)]
_BUBS = [(_rnd.uniform(0, W), _rnd.uniform(0, 900), _rnd.uniform(8, 26), _rnd.uniform(0, 6)) for _ in range(30)]
_FLAKES = [(_rnd.uniform(0, W), _rnd.uniform(0, 1080), _rnd.uniform(4, 10), _rnd.uniform(0, 6)) for _ in range(70)]

FLOOR_Y = 830


def _cloud(ctx, cx, cy, s):
    for (dx, dy, r) in ((0, 0, 50), (55, -20, 60), (115, 0, 48)):
        circle(ctx, cx + dx * s, cy + dy * s, r * s)
    ctx.set_source_rgb(1, 1, 1); ctx.fill()


def _bg_tree(ctx, x, base, s, col):
    rrect(ctx, x - 16 * s, base - 120 * s, 32 * s, 120 * s, 8 * s); fill(ctx, hexc('9C6B3E'), True); stroke(ctx, INK, 6)
    blobs = [(x, base - 170 * s, 70 * s), (x - 48 * s, base - 130 * s, 48 * s), (x + 48 * s, base - 130 * s, 48 * s)]
    for (bx, by, r) in blobs: circle(ctx, bx, by, r)
    ctx.set_source_rgb(*INK); ctx.set_line_width(12); ctx.stroke()
    for (bx, by, r) in blobs: circle(ctx, bx, by, r)
    fill(ctx, col)


def _road(ctx, t):
    """A sunny country road that scrolls left, so the host looks like it is driving."""
    g = cairo.LinearGradient(0, 0, 0, FLOOR_Y); g.add_color_stop_rgb(0, *hexc('7CC6FF')); g.add_color_stop_rgb(1, *hexc('C8ECFF'))
    ctx.set_source(g); ctx.paint()
    circle(ctx, 1760, 130, 75); fill(ctx, YEL, True); stroke(ctx, INK, 8)
    for k in range(3):
        x = (300 + k * 760 - t * 25) % 2300 - 200
        _cloud(ctx, x, 140 + 70 * (k % 2), 0.9)
    for k in range(5):  # far hills
        x = (k * 520 - t * 40) % 2600 - 340
        ellipse(ctx, x, 700, 360, 170); fill(ctx, hexc('A8E6A3'), True); stroke(ctx, INK, 6)
    ctx.rectangle(0, 690, W, FLOOR_Y - 690); fill(ctx, hexc('6BCB77'))
    for k in range(7):  # roadside trees
        x = (k * 340 - t * 160) % 2380 - 230
        _bg_tree(ctx, x, 760, 0.75, hexc('4CAF50') if k % 2 else hexc('3E9E4A'))
    ctx.rectangle(0, 760, W, H - 760); fill(ctx, hexc('5B5F6E'))
    ctx.move_to(0, 760); ctx.line_to(W, 760); stroke(ctx, INK, 8)
    ctx.rectangle(0, 772, W, 10); fill(ctx, WHITE)
    for k in range(12):  # centre dashes
        x = (k * 220 - t * 480) % 2640 - 220
        rrect(ctx, x, 1000, 120, 16, 8); fill(ctx, YEL)


def _farm(ctx, t):
    ctx.set_source_rgb(*hexc('9ED8FF')); ctx.paint()
    circle(ctx, 1760, 130, 75); fill(ctx, YEL, True); stroke(ctx, INK, 8)
    _cloud(ctx, 1250 + 30 * math.sin(t * .3), 140, 1.0); _cloud(ctx, 760 + 20 * math.sin(t * .25), 90, 0.7)
    ellipse(ctx, 500, 820, 900, 230); fill(ctx, hexc('A8E6A3'), True); stroke(ctx, INK, 6)
    ellipse(ctx, 1500, 840, 900, 210); fill(ctx, hexc('8FD694'), True); stroke(ctx, INK, 6)
    # red barn on the far hill
    bx, by = 1235, 655
    ctx.save(); ctx.translate(bx, by); ctx.scale(0.75, 0.75); ctx.translate(-bx, -by)
    poly(ctx, [(bx - 90, by), (bx, by - 80), (bx + 90, by)]); fill(ctx, hexc('B8341C'), True); stroke(ctx, INK, 7)
    rrect(ctx, bx - 80, by, 160, 110, 4); fill(ctx, hexc('E04423'), True); stroke(ctx, INK, 7)
    rrect(ctx, bx - 30, by + 40, 60, 70, 3); fill(ctx, WHITE, True); stroke(ctx, INK, 5)
    ctx.move_to(bx - 30, by + 40); ctx.line_to(bx + 30, by + 110); ctx.move_to(bx + 30, by + 40); ctx.line_to(bx - 30, by + 110)
    stroke(ctx, INK, 4); ctx.restore()
    ctx.rectangle(0, FLOOR_Y, W, H - FLOOR_Y); fill(ctx, hexc('6BCB77'))
    for k in range(0, W + 120, 120):  # fence
        rrect(ctx, k, 742, 22, 90, 6); fill(ctx, hexc('E8C9A0'), True); stroke(ctx, INK, 5)
    for y in (765, 800):
        rrect(ctx, 0, y, W, 14, 6); fill(ctx, hexc('E8C9A0'), True); stroke(ctx, INK, 5)
    for k in range(60):
        x = k * 33; ctx.move_to(x, FLOOR_Y + 4); ctx.line_to(x + 8, FLOOR_Y - 14); ctx.line_to(x + 16, FLOOR_Y + 4)
        fill(ctx, hexc('4D9F5A'))


def _forest(ctx, t):
    ctx.set_source_rgb(*hexc('CDEFD6')); ctx.paint()
    for k, x in enumerate((60, 760, 1180, 1880)):
        _bg_tree(ctx, x, 700, 1.1, hexc('8FD694'))
    ctx.rectangle(0, 690, W, FLOOR_Y - 690); fill(ctx, hexc('8FD694'))
    for k, x in enumerate((240, 880, 1560, 1760)):
        _bg_tree(ctx, x, 830, 1.35 + 0.15 * (k % 2), hexc('3E9E4A') if k % 2 else hexc('4CAF50'))
    ctx.rectangle(0, FLOOR_Y, W, H - FLOOR_Y); fill(ctx, hexc('7BC67E'))
    for (mx, my) in ((560, 870), (1260, 900)):
        rrect(ctx, mx - 10, my - 10, 20, 34, 6); fill(ctx, hexc('FFF1E0'), True); stroke(ctx, INK, 5)
        ctx.move_to(mx - 34, my - 6); quad_to(ctx, mx, my - 64, mx + 34, my - 6); ctx.close_path()
        fill(ctx, hexc('FF5A36'), True); stroke(ctx, INK, 5)
        circle(ctx, mx - 10, my - 26, 5); fill(ctx, WHITE); circle(ctx, mx + 12, my - 20, 4); fill(ctx, WHITE)
    for k in range(60):
        x = k * 33; ctx.move_to(x, FLOOR_Y + 4); ctx.line_to(x + 8, FLOOR_Y - 14); ctx.line_to(x + 16, FLOOR_Y + 4)
        fill(ctx, hexc('4D9F5A'))


def _pond(ctx, t):
    ctx.set_source_rgb(*hexc('A6E3FF')); ctx.paint()
    circle(ctx, 1760, 130, 75); fill(ctx, YEL, True); stroke(ctx, INK, 8)
    _cloud(ctx, 1250 + 30 * math.sin(t * .3), 150, 1.0)
    ctx.rectangle(0, 640, W, H - 640); fill(ctx, hexc('7BC67E'))
    ellipse(ctx, 1500, 975, 640, 150); fill(ctx, hexc('3FA7D6'), True); stroke(ctx, INK, 8)
    ellipse(ctx, 330, 990, 360, 110); fill(ctx, hexc('3FA7D6'), True); stroke(ctx, INK, 8)
    for k in range(5):  # ripples
        r = (t * 40 + k * 60) % 300
        ellipse(ctx, 1500 + (k % 2) * 260 - 130, 985, 60 + r * 0.8, 12 + r * 0.15)
        ctx.set_source_rgba(1, 1, 1, 0.35 * (1 - r / 300)); ctx.set_line_width(4); ctx.stroke()
    for (lx, ly) in ((260, 990), (1300, 950), (1760, 1000)):
        ctx.save(); ctx.translate(lx, ly); ctx.scale(1, 0.4)
        ctx.new_sub_path(); ctx.arc(0, 0, 70, 0.4, 2 * math.pi - 0.1); ctx.line_to(0, 0); ctx.close_path(); ctx.restore()
        fill(ctx, hexc('4CAF50'), True); stroke(ctx, INK, 5)
    for x in (80, 150, 1860):  # reeds
        for k in range(3):
            ctx.move_to(x + k * 18, 760); quad_to(ctx, x + k * 18 + 10 * math.sin(t + k), 640, x + k * 22, 560 - k * 20)
            stroke(ctx, hexc('3E7D3A'), 9)
        rrect(ctx, x + 14, 540, 16, 60, 8); fill(ctx, hexc('8B5A2B'), True); stroke(ctx, INK, 4)
    ctx.move_to(0, 640); ctx.line_to(W, 640); stroke(ctx, INK, 6)


def _sky(ctx, t):
    g = cairo.LinearGradient(0, 0, 0, H); g.add_color_stop_rgb(0, *hexc('5EB8FF')); g.add_color_stop_rgb(1, *hexc('D6F0FF'))
    ctx.set_source(g); ctx.paint()
    circle(ctx, 1760, 140, 80); fill(ctx, YEL, True); stroke(ctx, INK, 8)
    for k in range(6):
        x = (200 + k * 420 - t * 30) % 2400 - 250
        _cloud(ctx, x, 180 + (k % 3) * 210, 0.8 + 0.25 * (k % 2))
    _cloud(ctx, 960, 960, 3.2); _cloud(ctx, 120, 1000, 2.6); _cloud(ctx, 1500, 1010, 2.6)  # cloud floor


def _night(ctx, t):
    g = cairo.LinearGradient(0, 0, 0, FLOOR_Y); g.add_color_stop_rgb(0, *hexc('1B1F5E')); g.add_color_stop_rgb(1, *hexc('3C3F8F'))
    ctx.set_source(g); ctx.paint()
    for (x, y, r, p) in _STARS[:60]:
        circle(ctx, x, y * 0.8, r * (0.7 + 0.3 * math.sin(t * 3 + p))); ctx.set_source_rgba(1, 1, 0.85, 0.85); ctx.fill()
    circle(ctx, 1700, 170, 80); fill(ctx, hexc('FFF3B0'), True); stroke(ctx, INK, 8)
    circle(ctx, 1735, 150, 70); fill(ctx, hexc('2D3175'))
    for x in (60, 1860):
        _bg_tree(ctx, x, 830, 1.3, hexc('2E6B47'))
    ctx.rectangle(0, FLOOR_Y, W, H - FLOOR_Y); fill(ctx, hexc('2E6B47'))


def _city(ctx, t):
    ctx.set_source_rgb(*hexc('9ED8FF')); ctx.paint()
    _cloud(ctx, (500 - t * 20) % 2300 - 200, 120, 0.9)
    cols = ['FFB627', 'FF6FB5', '8E5CF7', '2EC4B6', 'FF8C42', '00B4D8']
    for k in range(9):  # buildings scroll slowly
        x = (k * 260 - t * 60) % 2340 - 210
        h = 260 + (k * 97) % 230
        rrect(ctx, x, 760 - h, 200, h, 10); fill(ctx, hexc(cols[k % 6]), True); stroke(ctx, INK, 7)
        for r in range(int(h // 70)):
            for c in range(3):
                rrect(ctx, x + 22 + c * 58, 760 - h + 26 + r * 70, 36, 40, 6); fill(ctx, hexc('FFF3B0'), True); stroke(ctx, INK, 3)
    ctx.rectangle(0, 760, W, H - 760); fill(ctx, hexc('5B5F6E'))
    ctx.move_to(0, 760); ctx.line_to(W, 760); stroke(ctx, INK, 8)
    ctx.rectangle(0, 772, W, 10); fill(ctx, WHITE)
    for k in range(12):
        x = (k * 220 - t * 300) % 2640 - 220
        rrect(ctx, x, 1000, 120, 16, 8); fill(ctx, WHITE)


def scene_bg(ctx, t, scene):
    if scene == 'space':
        g = cairo.LinearGradient(0, 0, 0, H); g.add_color_stop_rgb(0, *hexc('1B1464')); g.add_color_stop_rgb(1, *hexc('3A1C71'))
        ctx.set_source(g); ctx.paint()
        for (x, y, r, p) in _STARS:
            circle(ctx, x, y, r * (0.7 + 0.3 * math.sin(t * 3 + p))); ctx.set_source_rgba(1, 1, 1, 0.8); ctx.fill()
        circle(ctx, 1700, 170, 70); fill(ctx, hexc('FF8C42'), True); stroke(ctx, INK, 8)
        circle(ctx, 1500, 90, 26); fill(ctx, hexc('2EC4B6'), True); stroke(ctx, INK, 6)
        ctx.rectangle(0, FLOOR_Y, W, H - FLOOR_Y); fill(ctx, hexc('B8B8D1'))
        for k in range(14):
            ellipse(ctx, 80 + k * 140, FLOOR_Y + 70 + (k % 3) * 50, 40, 12); fill(ctx, hexc('9A9AB8'))
    elif scene == 'ocean':
        g = cairo.LinearGradient(0, 0, 0, H); g.add_color_stop_rgb(0, *hexc('48CAE4')); g.add_color_stop_rgb(1, *hexc('0077B6'))
        ctx.set_source(g); ctx.paint()
        for (x, y, r, p) in _BUBS:
            yy = (y - t * 60) % 900
            circle(ctx, x + 10 * math.sin(t * 2 + p), yy, r); ctx.set_source_rgba(1, 1, 1, 0.25); ctx.fill_preserve()
            ctx.set_source_rgba(1, 1, 1, 0.5); ctx.set_line_width(3); ctx.stroke()
        for sx in (180, 1780, 1600):
            ctx.move_to(sx, FLOOR_Y + 10)
            for k in range(5): quad_to(ctx, sx + (20 if k % 2 else -20) + 10 * math.sin(t * 2 + k), FLOOR_Y - 40 - k * 60, sx, FLOOR_Y - 60 - k * 60)
            stroke(ctx, hexc('2D6A4F'), 14)
        ctx.rectangle(0, FLOOR_Y, W, H - FLOOR_Y); fill(ctx, hexc('F6D7A7'))
        ctx.move_to(0, FLOOR_Y); ctx.line_to(W, FLOOR_Y); stroke(ctx, INK, 8)
        return
    elif scene == 'road':
        _road(ctx, t); return
    elif scene == 'farm':
        _farm(ctx, t)
    elif scene == 'pond':
        _pond(ctx, t); return
    elif scene == 'sky':
        _sky(ctx, t); return
    elif scene == 'night':
        _night(ctx, t)
    elif scene == 'city':
        _city(ctx, t); return
    elif scene == 'forest':
        _forest(ctx, t)
    elif scene == 'park':
        ctx.set_source_rgb(*hexc('8FD3FF')); ctx.paint()
        circle(ctx, 1760, 140, 80); fill(ctx, YEL, True); stroke(ctx, INK, 8)
        for (cx, cy, s) in ((1300 + 30 * math.sin(t * .3), 150, 1.0), (300 + 20 * math.sin(t * .25), 600, 0.8)):
            for (dx, dy, r) in ((0, 0, 50), (55, -20, 60), (115, 0, 48)):
                circle(ctx, cx + dx * s, cy + dy * s, r * s)
            ctx.set_source_rgb(1, 1, 1); ctx.fill()
        ctx.rectangle(0, FLOOR_Y, W, H - FLOOR_Y); fill(ctx, hexc('6BCB77'))
        for k in range(60):
            x = k * 33; ctx.move_to(x, FLOOR_Y + 4); ctx.line_to(x + 8, FLOOR_Y - 14); ctx.line_to(x + 16, FLOOR_Y + 4)
            fill(ctx, hexc('4D9F5A'))
    elif scene == 'candy':
        ctx.set_source_rgb(*hexc('FFC8DD')); ctx.paint()
        for k in range(0, W + 200, 160):
            ctx.move_to(k, 0); ctx.line_to(k + 60, 0); ctx.line_to(k - 200, FLOOR_Y); ctx.line_to(k - 260, FLOOR_Y); ctx.close_path()
        ctx.set_source_rgba(1, 1, 1, 0.35); ctx.fill()
        ctx.rectangle(0, FLOOR_Y, W, H - FLOOR_Y); fill(ctx, hexc('CDB4DB'))
        for k in range(16):
            circle(ctx, 60 + k * 125, FLOOR_Y + 90, 26); fill(ctx, NUMCOL[k % 10])
    elif scene == 'jungle':
        ctx.set_source_rgb(*hexc('B7E4C7')); ctx.paint()
        for k, x in enumerate((60, 260, 1660, 1860)):
            for j in range(4):
                ctx.save(); ctx.translate(x, 80 + j * 120); ctx.rotate((-1) ** (k + j) * 0.5 + 0.08 * math.sin(t + j))
                ellipse(ctx, 0, 0, 110, 34); fill(ctx, hexc('40916C'), True); stroke(ctx, INK, 6); ctx.restore()
        ctx.rectangle(0, FLOOR_Y, W, H - FLOOR_Y); fill(ctx, hexc('74C69D'))
    elif scene == 'snow':
        ctx.set_source_rgb(*hexc('A9D6FF')); ctx.paint()
        for (x, y, r, p) in _FLAKES:
            yy = (y + t * 50) % 1080
            circle(ctx, x + 14 * math.sin(t + p), yy, r); ctx.set_source_rgba(1, 1, 1, 0.9); ctx.fill()
        ctx.rectangle(0, FLOOR_Y, W, H - FLOOR_Y); fill(ctx, WHITE)
        ctx.move_to(0, FLOOR_Y); ctx.line_to(W, FLOOR_Y); stroke(ctx, hexc('8EB8E5'), 8)
        return
    else:  # kitchen / classroom
        base = BLUE if scene == 'kitchen' else hexc('FFB627')
        dot = hexc('4D93FF') if scene == 'kitchen' else hexc('FFC453')
        ctx.set_source_rgb(*base); ctx.paint()
        for gx in range(0, W + 120, 120):
            for gy in range(0, 840, 120):
                circle(ctx, gx + (60 if (gy // 120) % 2 else 0), gy + 40, 10)
        fill(ctx, dot)
        for (fx, fy, ch, sz, ph) in _FLOAT:
            yy = (fy - t * 18) % 860 - 40
            ctx.save(); ctx.translate(fx + 14 * math.sin(t + ph), yy); ctx.rotate(0.3 * math.sin(t * 0.7 + ph))
            ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(sz)
            ctx.move_to(0, 0); ctx.text_path(ch); ctx.set_source_rgba(1, 1, 1, 0.16); ctx.fill(); ctx.restore()
        if scene == 'kitchen':
            ctx.rectangle(0, FLOOR_Y, W, H - FLOOR_Y); fill(ctx, WHITE)
            for r in range(5):
                for c in range(W // 64 + 2):
                    if (r + c) % 2 == 0: ctx.rectangle(c * 64, FLOOR_Y + 12 + r * 64, 64, 64)
            fill(ctx, CLOTH)
            ctx.rectangle(0, FLOOR_Y, W, 14); fill(ctx, hexc('E84A4A'))
        else:
            ctx.rectangle(0, FLOOR_Y, W, H - FLOOR_Y); fill(ctx, hexc('C68B59'))
            for k in range(0, W, 160):
                ctx.move_to(k, FLOOR_Y); ctx.line_to(k, H); stroke(ctx, hexc('A86F42'), 4)
    ctx.move_to(0, FLOOR_Y); ctx.line_to(W, FLOOR_Y); stroke(ctx, INK, 8)


def board(ctx, t, line1, label, value):
    rrect(ctx, 110, 100, 560, 380, 22); fill(ctx, WOOD, True); stroke(ctx, INK, 10)
    rrect(ctx, 138, 128, 504, 324, 10); fill(ctx, GREEN)
    chalk = (0.95, 0.95, 0.92)
    text(ctx, line1, 390, 200, fit_size(ctx, line1, 62, 440), chalk)
    lw = text_w(ctx, label + '  ', 66)
    vw = text_w(ctx, value, 96)
    total = lw + vw
    sz = 66 if total < 460 else 66 * 460 / total
    vsz = 96 * sz / 66
    lw = text_w(ctx, label + '  ', sz); vw = text_w(ctx, value, vsz)
    x0 = 390 - (lw + vw) / 2
    text(ctx, label, x0 + lw / 2, 330, sz, chalk)
    text(ctx, value, x0 + lw + vw / 2, 330, vsz, YEL)
    ctx.move_to(170, 420); ctx.line_to(400, 420); ctx.set_source_rgba(1, 1, 1, 0.25); ctx.set_line_width(5); ctx.stroke()


def caption(ctx, s, alpha=1.0):
    if not s or alpha <= 0: return
    lines = s.split('\n'); size = 54
    mw = max(text_w(ctx, l, size) for l in lines)
    if mw > 1700: size = size * 1700 / mw; mw = 1700
    bw, bh = mw + 100, len(lines) * size * 1.3 + 36
    x, y = W / 2 - bw / 2, 1048 - bh

    def draw():
        rrect(ctx, x, y, bw, bh, 30); ctx.set_source_rgba(1, 1, 1, 0.96); ctx.fill_preserve(); stroke(ctx, INK, 7)
        for k, l in enumerate(lines):
            text(ctx, l, W / 2, y + 18 + size * 0.65 + k * size * 1.3, size, INK)
    with_alpha(ctx, alpha, draw)
