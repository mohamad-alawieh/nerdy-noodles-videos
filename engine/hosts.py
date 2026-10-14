"""Nerdy Noodles hosts: the star of an episode or Short.

Every host shares Noodle's pose vocabulary (eyes, mouth, arms, squash, look) and the same footprint:
local 800x700 box, centred on x=400, standing on local y=646, so the engines can swap hosts freely.
Every host wears the channel's round nerd glasses.

    draw_host(ctx, host, t, cx, cy, s, frac, eyes, mouth, look, sq, arms, brows, shadow=True)

`host` is None / "noodle" / "car" / {"kind": "car", "color": "#3A86FF", "driving": true}.
"""
import math

from draw import (INK, WHITE, PINK, YEL, WOOD, hexc, clamp, quad_to, stroke, fill, ellipse, circle, rrect, poly,
                  darker, draw_noodle)

HOST_KINDS = ['noodle', 'car', 'duck', 'dino', 'cat', 'tree']
HOST_COLORS = {'noodle': '#FF5A36', 'car': '#3A86FF', 'duck': '#FFD23F', 'dino': '#3DDC84', 'cat': '#FF9F43',
               'tree': '#4CAF50'}
# local y of the top of each host's head (where a hat or object "on the head" rests)
HOST_HEAD_Y = {'noodle': 294, 'car': 236, 'duck': 168, 'dino': 160, 'cat': 166, 'tree': 52}
HOST_NAMES = {'noodle': 'Noodle', 'car': 'Zoomy', 'duck': 'Quackers', 'dino': 'Stompy', 'cat': 'Mittens',
              'tree': 'Twiggy'}


def host_spec(host):
    """Normalise a host value from JSON into a dict with kind and color."""
    if not host: host = 'noodle'
    if isinstance(host, str): host = {'kind': host}
    h = dict(host)
    h['kind'] = h.get('kind', 'noodle')
    if h['kind'] not in HOST_KINDS:
        raise ValueError('unknown host kind %r (use one of %s)' % (h['kind'], ', '.join(HOST_KINDS)))
    h.setdefault('color', HOST_COLORS[h['kind']])
    h.setdefault('name', HOST_NAMES[h['kind']])
    return h


# ------------------------------------------------------------------ shared face parts
def _arm_angles(t, arms):
    if arms == 'rest': ar = al = 1.05 + 0.05 * math.sin(t * 4)
    elif arms == 'wave': al = 1.05; ar = -1.05 + 0.45 * math.sin(t * 11)
    elif arms == 'cheer': al = ar = -1.15 + 0.25 * math.sin(t * 12)
    elif arms == 'shock': al = ar = -0.35
    elif arms == 'dance':
        al = -0.6 + 0.9 * math.sin(t * math.pi * 2); ar = -0.6 - 0.9 * math.sin(t * math.pi * 2)
    else: al = ar = 1.05
    return ((1, ar), (-1, al))


def _stick_arms(ctx, t, arms, sx0, sy, length, hand):
    """Noodle-style bendy arms; hand(ctx, x, y, side) draws the hand."""
    for side, a in _arm_angles(t, arms):
        sx = 400 + side * sx0
        hx, hy = sx + side * length * math.cos(a), sy + length * math.sin(a)
        mx, my = (sx + hx) / 2 + side * 15, (sy + hy) / 2 - 15
        ctx.move_to(sx, sy); quad_to(ctx, mx, my, hx, hy); stroke(ctx, INK, 16)
        hand(ctx, hx, hy, side)


def _glove(ctx, x, y, side):
    circle(ctx, x, y, 24); fill(ctx, WHITE, True); stroke(ctx, INK, 9)


def _paw(col):
    def f(ctx, x, y, side):
        circle(ctx, x, y, 26); fill(ctx, col, True); stroke(ctx, INK, 9)
    return f


def _eyes(ctx, eyes, look, pts, lr=58, brows=False, temples=True):
    """Round nerd glasses with eyes inside (same look as Noodle's)."""
    k = lr / 58.0
    if eyes == 'shock': lr *= 64 / 58.0
    (x1, y1), (x2, y2) = pts
    if temples:
        ctx.move_to(x1 - lr + 2, y1 - 7 * k); ctx.line_to(x1 - lr - 40 * k, y1 - 25 * k); stroke(ctx, INK, 14 * k)
        ctx.move_to(x2 + lr - 2, y2 - 7 * k); ctx.line_to(x2 + lr + 40 * k, y2 - 25 * k); stroke(ctx, INK, 14 * k)
    for (ex, ey) in pts:
        circle(ctx, ex, ey, lr); fill(ctx, WHITE, True); stroke(ctx, INK, 14 * k)
        lx, ly = look
        if eyes in ('normal', 'shock'):
            pr = (13 if eyes == 'shock' else 22) * k
            px, py = ex + 6 * k + lx * 16 * k, ey + 5 * k + ly * 16 * k
            circle(ctx, px, py, pr); fill(ctx, INK)
            circle(ctx, px + pr * 0.35, py - pr * 0.35, pr * 0.32); fill(ctx, WHITE)
        elif eyes == 'happy':
            ctx.move_to(ex - 24 * k, ey + 13 * k); quad_to(ctx, ex, ey - 25 * k, ex + 24 * k, ey + 13 * k); stroke(ctx, INK, 12 * k)
        elif eyes == 'closed':
            ctx.move_to(ex - 24 * k, ey + 3 * k); quad_to(ctx, ex, ey + 15 * k, ex + 24 * k, ey + 3 * k); stroke(ctx, INK, 12 * k)
        elif eyes == 'squint':
            d = 1 if ex < (x1 + x2) / 2 else -1
            ctx.move_to(ex - 24 * k * d, ey - 7 * k); ctx.line_to(ex + 18 * k * d, ey + 5 * k)
            ctx.line_to(ex - 24 * k * d, ey + 17 * k); stroke(ctx, INK, 12 * k)
    # bridge
    ctx.move_to(x1 + lr - 6 * k, y1 - 3 * k); quad_to(ctx, (x1 + x2) / 2, y1 - 19 * k, x2 - lr + 6 * k, y2 - 3 * k)
    stroke(ctx, INK, 14 * k)
    if brows:
        for (ex, ey) in pts:
            ctx.move_to(ex - 30 * k, ey - 85 * k); quad_to(ctx, ex, ey - 103 * k, ex + 30 * k, ey - 85 * k)
            stroke(ctx, INK, 12 * k)


def _mouth(ctx, mouth, x, y, k=1.0):
    ctx.save(); ctx.translate(x, y); ctx.scale(k, k)
    if mouth == 'smile':
        ctx.move_to(-40, -13); quad_to(ctx, 0, 21, 40, -13); stroke(ctx, INK, 13)
    elif mouth == 'o':
        ellipse(ctx, 0, 0, 20, 25); fill(ctx, INK)
    elif mouth == 'big_o':
        ellipse(ctx, 0, 0, 34, 30); fill(ctx, INK)
    elif mouth == 'achoo':
        ellipse(ctx, 0, -3, 48, 26); fill(ctx, INK)
    elif mouth == 'laugh':
        ctx.move_to(-48, -20); quad_to(ctx, 0, 45, 48, -20); ctx.close_path(); fill(ctx, INK)
        ellipse(ctx, 0, 7, 18, 9); fill(ctx, hexc('FF6B8A'))
    ctx.restore()


def _cheeks(ctx, pts, rx=30, ry=18):
    for (x, y) in pts:
        ellipse(ctx, x, y, rx, ry); fill(ctx, PINK)


# ------------------------------------------------------------------ hosts (local coordinates)
def _car(ctx, t, col, eyes, mouth, look, arms, brows, driving):
    bob = 5 * math.sin(t * 15) if driving else 0.0
    # antenna (waves with the arms pose)
    wob = {'cheer': 0.5 * math.sin(t * 12), 'wave': 0.35 * math.sin(t * 11), 'dance': 0.6 * math.sin(t * 6.3),
           'shock': -0.25}.get(arms, 0.12 * math.sin(t * 4))
    ax, ay = 560, 262 + bob
    tx, ty = ax + 120 * math.sin(0.3 + wob), ay - 120 * math.cos(0.3 + wob)
    ctx.move_to(ax, ay); quad_to(ctx, (ax + tx) / 2 + 10, (ay + ty) / 2, tx, ty); stroke(ctx, INK, 8)
    circle(ctx, tx, ty, 18); fill(ctx, hexc('FF5A36'), True); stroke(ctx, INK, 7)
    ctx.save(); ctx.translate(0, bob)
    # cabin
    ctx.move_to(195, 410); ctx.curve_to(205, 275, 285, 232, 400, 232); ctx.curve_to(515, 232, 595, 275, 605, 410)
    ctx.close_path(); fill(ctx, col, True); stroke(ctx, INK, 12)
    ctx.move_to(235, 405); ctx.curve_to(245, 300, 300, 262, 400, 262); ctx.curve_to(500, 262, 555, 300, 565, 405)
    ctx.close_path(); fill(ctx, hexc('BDE7FF'), True); stroke(ctx, INK, 8)
    ctx.move_to(280, 330); quad_to(ctx, 300, 290, 345, 280); ctx.set_source_rgba(1, 1, 1, 0.7); ctx.set_line_width(10); ctx.stroke()
    # body
    rrect(ctx, 100, 395, 600, 195, 70); fill(ctx, col, True); stroke(ctx, INK, 12)
    ctx.move_to(150, 425); quad_to(ctx, 400, 405, 650, 425); ctx.set_source_rgba(1, 1, 1, 0.45); ctx.set_line_width(10); ctx.stroke()
    for hx in (165, 635):
        circle(ctx, hx, 470, 30); fill(ctx, hexc('FFF3B0'), True); stroke(ctx, INK, 8)
    rrect(ctx, 115, 545, 570, 34, 17); fill(ctx, hexc('D9DEE8'), True); stroke(ctx, INK, 9)
    _cheeks(ctx, [(255, 510), (545, 510)], 30, 17)
    _mouth(ctx, mouth, 400, 500, 1.05)
    _eyes(ctx, eyes, look, [(335, 345), (465, 345)], 54, brows, temples=False)
    ctx.restore()
    # wheels
    spin = t * 14 if driving else 0.0
    for wx in (225, 575):
        circle(ctx, wx, 584, 62); fill(ctx, INK)
        circle(ctx, wx, 584, 30); fill(ctx, hexc('D9DEE8'), True); stroke(ctx, INK, 6)
        for k in range(3):
            a = spin + k * 2 * math.pi / 3
            ctx.move_to(wx, 584); ctx.line_to(wx + 26 * math.cos(a), 584 + 26 * math.sin(a)); stroke(ctx, INK, 6)


def _duck(ctx, t, col, eyes, mouth, look, arms, brows):
    org = hexc('FF8C42')
    for fx in (320, 480):
        ellipse(ctx, fx, 632, 62, 20); fill(ctx, org, True); stroke(ctx, INK, 9)
    # wings = arms
    for side, a in _arm_angles(t, arms):
        sx, sy = 400 + side * 190, 500
        cx, cy = sx + side * 70 * math.cos(a), sy + 70 * math.sin(a)
        ctx.save(); ctx.translate(cx, cy); ctx.rotate(math.atan2(math.sin(a), side * math.cos(a)))
        ellipse(ctx, 0, 0, 92, 40); fill(ctx, darker(col, 0.88), True); stroke(ctx, INK, 10); ctx.restore()
    ellipse(ctx, 400, 520, 225, 125); fill(ctx, col, True); stroke(ctx, INK, 12)
    ellipse(ctx, 400, 560, 120, 65); ctx.set_source_rgba(1, 1, 1, 0.35); ctx.fill()
    for dx, h in ((-22, 60), (0, 78), (22, 60)):
        ctx.move_to(400 + dx, 175); quad_to(ctx, 400 + dx * 2.2, 175 - h, 400 + dx * 3 + 6, 175 - h * 0.7)
        stroke(ctx, INK, 16, keep=False)
        ctx.move_to(400 + dx, 175); quad_to(ctx, 400 + dx * 2.2, 175 - h, 400 + dx * 3 + 6, 175 - h * 0.7)
        stroke(ctx, col, 8)
    circle(ctx, 400, 320, 160); fill(ctx, col, True); stroke(ctx, INK, 12)
    _cheeks(ctx, [(285, 390), (515, 390)], 28, 16)
    _eyes(ctx, eyes, look, [(335, 300), (465, 300)], 54, brows)
    # beak doubles as the mouth
    openk = {'o': 0.55, 'big_o': 0.9, 'achoo': 1.0, 'laugh': 0.8}.get(mouth, 0.0)
    if openk > 0:
        ellipse(ctx, 400, 422, 50, 10 + 26 * openk); fill(ctx, INK)
        if mouth == 'laugh':
            ellipse(ctx, 400, 432 + 10 * openk, 22, 9); fill(ctx, hexc('FF6B8A'))
        ellipse(ctx, 400, 446 + 18 * openk, 58, 18); fill(ctx, darker(org, 0.92), True); stroke(ctx, INK, 9)
        ellipse(ctx, 400, 404, 74, 24); fill(ctx, org, True); stroke(ctx, INK, 9)
    else:
        ellipse(ctx, 400, 418, 74, 30); fill(ctx, org, True); stroke(ctx, INK, 9)
        ctx.move_to(340, 416); quad_to(ctx, 400, 438 if mouth == 'smile' else 426, 460, 416); stroke(ctx, INK, 7)
        circle(ctx, 382, 402, 4); fill(ctx, INK); circle(ctx, 418, 402, 4); fill(ctx, INK)


def _dino(ctx, t, col, eyes, mouth, look, arms, brows):
    dk = darker(col, 0.72)
    ctx.move_to(560, 520); quad_to(ctx, 700, 540, 735, 640); quad_to(ctx, 640, 640, 545, 610); ctx.close_path()
    fill(ctx, col, True); stroke(ctx, INK, 11)
    for fx in (285, 425):
        rrect(ctx, fx, 595, 92, 50, 22); fill(ctx, col, True); stroke(ctx, INK, 10)
    _stick_arms(ctx, t, arms, 170, 480, 85, _paw(col))
    ellipse(ctx, 400, 520, 190, 122); fill(ctx, col, True); stroke(ctx, INK, 12)
    ellipse(ctx, 400, 545, 112, 80); fill(ctx, hexc('FFF3B0'), True); stroke(ctx, INK, 7)
    for y in (510, 545, 580):
        ctx.move_to(330, y); quad_to(ctx, 400, y + 10, 470, y); stroke(ctx, darker(hexc('FFF3B0'), 0.85), 5)
    # back spikes around the head
    for k in range(5):
        a = math.radians(-150 + k * 30)
        bx, by = 400 + 168 * math.cos(a), 318 + 138 * math.sin(a)
        nx, ny = math.cos(a), math.sin(a)
        poly(ctx, [(bx - ny * 30, by + nx * 30), (bx + nx * 55, by + ny * 55), (bx + ny * 30, by - nx * 30)])
        fill(ctx, dk, True); stroke(ctx, INK, 8)
    ellipse(ctx, 400, 320, 185, 150); fill(ctx, col, True); stroke(ctx, INK, 12)
    for (sx, sy, r) in ((270, 230, 14), (300, 205, 9), (520, 225, 12)):
        circle(ctx, sx, sy, r); fill(ctx, dk)
    _cheeks(ctx, [(275, 390), (525, 390)], 28, 16)
    _eyes(ctx, eyes, look, [(333, 300), (467, 300)], 54, brows)
    circle(ctx, 382, 372, 5); fill(ctx, INK); circle(ctx, 418, 372, 5); fill(ctx, INK)
    _mouth(ctx, mouth, 400, 420, 1.0)
    if mouth == 'smile':
        poly(ctx, [(372, 418), (382, 432), (390, 420)]); fill(ctx, WHITE, True); stroke(ctx, INK, 3)


def _cat(ctx, t, col, eyes, mouth, look, arms, brows):
    dk = darker(col, 0.75)
    wag = 18 * math.sin(t * 3)
    for c, wd in ((INK, 46), (col, 30)):
        ctx.move_to(540, 600); quad_to(ctx, 700, 600, 690 + wag, 480); quad_to(ctx, 680 + wag, 420, 640 + wag, 420)
        stroke(ctx, c, wd)
    for fx in (325, 475):
        ellipse(ctx, fx, 632, 58, 24); fill(ctx, col, True); stroke(ctx, INK, 9)
    _stick_arms(ctx, t, arms, 160, 480, 100, _paw(col))
    ellipse(ctx, 400, 530, 175, 118); fill(ctx, col, True); stroke(ctx, INK, 12)
    ellipse(ctx, 400, 555, 95, 72); fill(ctx, hexc('FFF1E0'), True); stroke(ctx, INK, 6)
    for side in (-1, 1):
        poly(ctx, [(400 + side * 70, 190), (400 + side * 175, 95), (400 + side * 180, 250)]); fill(ctx, col, True); stroke(ctx, INK, 11)
        poly(ctx, [(400 + side * 100, 195), (400 + side * 162, 135), (400 + side * 162, 225)]); fill(ctx, PINK)
    ellipse(ctx, 400, 320, 190, 158); fill(ctx, col, True); stroke(ctx, INK, 12)
    for dx in (-30, 0, 30):
        ctx.move_to(400 + dx, 168); ctx.line_to(400 + dx * 0.8, 200); stroke(ctx, dk, 10)
    _cheeks(ctx, [(270, 385), (530, 385)], 28, 16)
    _eyes(ctx, eyes, look, [(333, 300), (467, 300)], 54, brows)
    poly(ctx, [(384, 372), (416, 372), (400, 390)]); fill(ctx, hexc('FF6B8A'), True); stroke(ctx, INK, 5)
    for side in (-1, 1):
        for k, dy in enumerate((-8, 6, 20)):
            ctx.move_to(400 + side * 120, 395 + dy); ctx.line_to(400 + side * 215, 380 + dy * 2.2); stroke(ctx, INK, 5)
    if mouth == 'smile':
        ctx.move_to(366, 400); quad_to(ctx, 382, 420, 400, 396); quad_to(ctx, 418, 420, 434, 400); stroke(ctx, INK, 8)
    else:
        _mouth(ctx, mouth, 400, 420, 0.85)


def _tree(ctx, t, col, eyes, mouth, look, arms, brows):
    bark = hexc('9C6B3E')
    leaf2 = darker(col, 0.8)
    # branch arms with leafy hands
    def leafy(ctx, x, y, side):
        for (dx, dy, r) in ((0, 0, 34), (side * 24, -20, 24), (-side * 10, -30, 22)):
            circle(ctx, x + dx, y + dy, r)
        ctx.set_source_rgb(*INK); ctx.set_line_width(14); ctx.stroke_preserve(); fill(ctx, col)
    for side, a in _arm_angles(t, arms):
        a = a * 0.6 - 0.6  # branches reach outwards/upwards, never droop to the ground
        sx, sy = 400 + side * 72, 470
        hx, hy = sx + side * 150 * math.cos(a), sy + 150 * math.sin(a)
        mx, my = (sx + hx) / 2 + side * 15, (sy + hy) / 2 - 15
        for c, wd in ((INK, 30), (bark, 18)):
            ctx.move_to(sx, sy); quad_to(ctx, mx, my, hx, hy); stroke(ctx, c, wd)
        leafy(ctx, hx, hy, side)
    # trunk with roots
    ctx.move_to(250, 646); quad_to(ctx, 315, 620, 318, 540); ctx.line_to(322, 300); ctx.line_to(478, 300)
    ctx.line_to(482, 540); quad_to(ctx, 485, 620, 550, 646); ctx.close_path(); fill(ctx, bark, True); stroke(ctx, INK, 12)
    for (x0, y0, x1, y1) in ((345, 560, 352, 610), (450, 570, 446, 620), (360, 330, 356, 365)):
        ctx.move_to(x0, y0); ctx.line_to(x1, y1); stroke(ctx, darker(bark, 0.75), 6)
    # canopy (outline only around the union)
    blobs = [(400, 190, 150), (255, 270, 105), (545, 270, 105), (300, 140, 100), (500, 140, 100), (400, 300, 95)]
    for (x, y, r) in blobs: circle(ctx, x, y, r)
    ctx.set_source_rgb(*INK); ctx.set_line_width(24); ctx.stroke()
    for (x, y, r) in blobs: circle(ctx, x, y, r)
    fill(ctx, col)
    for (x, y, r) in ((300, 230, 26), (480, 150, 22), (560, 290, 18), (390, 110, 16)):
        circle(ctx, x, y, r); fill(ctx, leaf2)
    for (x, y) in ((250, 300), (520, 210), (430, 260)):
        circle(ctx, x, y, 15); fill(ctx, hexc('FF5A36'), True); stroke(ctx, INK, 5)
    _cheeks(ctx, [(340, 500), (460, 500)], 22, 13)
    _eyes(ctx, eyes, look, [(352, 430), (448, 430)], 44, brows, temples=False)
    _mouth(ctx, mouth, 400, 535, 0.8)


def draw_host(ctx, host, t, cx, cy, s, frac=1.0, eyes='normal', mouth='smile', look=(0, 0), sq=0.0,
              arms='rest', brows=False, shadow=True):
    h = host_spec(host)
    kind = h['kind']
    if kind == 'noodle':
        return draw_noodle(ctx, t, cx, cy, s, frac, eyes, mouth, look, sq, arms, brows, shadow)
    col = hexc(h['color'])
    if shadow:
        ellipse(ctx, cx, cy + 200 * s, (300 if kind == 'car' else 250) * s * (1 - sq * 0.3), 22 * s)
        ctx.set_source_rgba(0, 0, 0, 0.16); ctx.fill()
    ctx.save()
    ctx.translate(cx, cy)
    by = 196 * s
    ctx.translate(0, by); ctx.scale(1 + sq * 0.6, 1 - sq); ctx.translate(0, -by)
    ctx.scale(s, s); ctx.translate(-400, -450)
    if kind == 'car': _car(ctx, t, col, eyes, mouth, look, arms, brows, h.get('driving', False))
    elif kind == 'duck': _duck(ctx, t, col, eyes, mouth, look, arms, brows)
    elif kind == 'dino': _dino(ctx, t, col, eyes, mouth, look, arms, brows)
    elif kind == 'cat': _cat(ctx, t, col, eyes, mouth, look, arms, brows)
    elif kind == 'tree': _tree(ctx, t, col, eyes, mouth, look, arms, brows)
    ctx.restore()
