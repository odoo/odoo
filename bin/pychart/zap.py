#
# Copyright (C) 2000-2005 by Yasushi Saito (yasushi.saito@gmail.com)
# 
# Jockey is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.
#
# Jockey is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
import fill_style
import line_style
import copy

def _draw_zap(can, p1, p2, style, pat):
    x = copy.deepcopy(p1)
    x.extend(p2)
    can.polygon(None, pat, x)
    can.lines(style, p1)
    can.lines(style, p2)
    

def zap_horizontally(can, style, pat, x1, y1, x2, y2, xsize, ysize):
    """Draw a horizontal "zapping" symbol on the canvas that shows
    that a graph is ripped in the middle.

    Parameter <fill_style> specifies the style for the zig-zag lines.
    PAT specifies the pattern with which the area is filled.
    The symbol is drawn in the rectangle (<x1>, <y1>) - (<x2>, <y2>).
    Each "zigzag" has the width <xsize>, height <ysize>."""

    assert isinstance(style, line_style.T)
    assert isinstance(pat, fill_style.T)

    points = []
    points2 = []
    x = x1
    y = y1
    while x < x2:
        points.append((x, y))
        points2.append((x, y + (y2-y1)))
        x += xsize
        if y == y1:
            y += ysize
        else:
            y -= ysize

    points2.reverse()
    _draw_zap(can, points, points2, style, pat)

def zap_vertically(can, style, pat, x1, y1, x2, y2, xsize, ysize):
    """Draw a vertical "zapping" symbol on the canvas that shows
    that a graph is ripped in the middle.

    Parameter <fill_style> specifies the style for the zig-zag lines.
    PAT specifies the pattern with which the area is filled.
    The symbol is drawn in the rectangle (<x1>, <y1>) - (<x2>, <y2>).
    Each "zigzag" has the width <xsize>, height <ysize>."""
    
    points = []
    points2 = []
    x = x1
    y = y1
    while y < y2:
        points.append((x, y))
        points2.append((x + (x2-x1), y))
        y += ysize
        if x == x1:
            x += xsize
        else:
            x -= xsize

    points2.reverse()
    _draw_zap(can, points, points2, style, pat)

