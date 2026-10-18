"""Arabic (and any complex-script) text as real cairo paths: HarfBuzz shapes the text with the bundled
Baloo Bhaijaan 2 font (OFL, assets/fonts) and we trace each glyph outline into the cairo context, so Arabic
letters join correctly, run right-to-left, and can be outlined/filled like the rest of the cartoon text."""
import os, re
import uharfbuzz as hb

FONT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'fonts', 'BalooBhaijaan2.ttf')
ARABIC = re.compile(r'[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]')
_font = None


def has_arabic(s):
    return bool(ARABIC.search(s or ''))


def _get_font():
    global _font
    if _font is None:
        blob = hb.Blob.from_file_path(FONT_FILE)
        face = hb.Face(blob); _font = hb.Font(face)
        _font.set_variations({'wght': 800})
    return _font


def shape(s):
    f = _get_font()
    buf = hb.Buffer(); buf.add_str(s); buf.guess_segment_properties()
    hb.shape(f, buf, {})
    return f, buf.glyph_infos, buf.glyph_positions


def width(s, size):
    f, infos, pos = shape(s)
    return sum(p.x_advance for p in pos) * size / f.face.upem


class _Pen:
    def __init__(self, ctx, ox, oy, k):
        self.c, self.ox, self.oy, self.k = ctx, ox, oy, k
        self.cur = (0, 0)

    def _p(self, x, y): return self.ox + x * self.k, self.oy - y * self.k

    def moveTo(self, p): self.c.move_to(*self._p(*p)); self.cur = p
    def lineTo(self, p): self.c.line_to(*self._p(*p)); self.cur = p

    def curveTo(self, a, b, p):
        self.c.curve_to(*self._p(*a), *self._p(*b), *self._p(*p)); self.cur = p

    def qCurveTo(self, a, p):
        x0, y0 = self.cur
        c1 = (x0 + 2 / 3 * (a[0] - x0), y0 + 2 / 3 * (a[1] - y0))
        c2 = (p[0] + 2 / 3 * (a[0] - p[0]), p[1] + 2 / 3 * (a[1] - p[1]))
        self.curveTo(c1, c2, p)

    def closePath(self): self.c.close_path()
    def endPath(self): pass


def path(ctx, s, x_left, baseline, size):
    """Append the shaped text as a path starting at x_left (visual left edge) on the given baseline."""
    f, infos, pos = shape(s)
    k = size / f.face.upem
    x = 0
    for info, p in zip(infos, pos):
        pen = _Pen(ctx, x_left + (x + p.x_offset) * k, baseline - p.y_offset * k, k)
        f.draw_glyph_with_pen(info.codepoint, pen)
        x += p.x_advance
