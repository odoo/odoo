# -*- coding: utf-8 -*-
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
import pychart_util
import color
import line_style
import chart_object
import object_set
import types
import theme
import fill_style_doc
from pychart_types import *
from scaling import *

_keys = {
    "bgcolor" : (color.T, color.white, "The background color."),
    "line_style": (line_style.T, line_style.default,
                   pychart_util.line_desc),
    "line_interval": (NumType, 3,
                      "The interval between successive stitch lines.")
    }

class T(chart_object.T):
    __doc__ = fill_style_doc.doc
    keys = _keys
##AUTOMATICALLY GENERATED
##END AUTOMATICALLY GENERATED
    def __str__(self):
        s = name_table().lookup(self)
        if s:
            return s
        return "<fillstyle: bg=%s line=%s interval=%s>" % \
               (self.bgcolor, self.line_style, self.line_interval)

class Plain(T):
    """This class just fills the region with solid background color.
Attributes line_style and line_interval are ignored."""
    def draw(self, can, x1, y1, x2, y2):
        pass
    
class Diag(T):
    "This class fills the region with diagonal lines."

    def draw(self, can, x1, y1, x2, y2):
        line_width = self.line_style.width
        interval = self.line_interval * 1.414
        x1 -= line_width
        y1 -= line_width
        x2 += line_width
        y2 += line_width
        len = max(y2 - y1, x2 - x1)
        curx = x1 - len
        while curx < x2:
            can.line(self.line_style, curx, y1, curx+len, y1+len)
            curx += interval
            
class Rdiag(T):
    """Fills the region with diagonal lines, but tilted in the opposite
direction from fill_style.Diag."""
    def draw(self, can, x1, y1, x2, y2):    
        line_width = self.line_style.width
        interval = self.line_interval * 1.414
        x1 -= line_width
        y1 -= line_width
        x2 += line_width
        y2 += line_width
        len = max(y2 - y1, x2 - x1)
        curx = x1
        while curx < x2 + len:
            can.line(self.line_style, curx, y1, curx-len, y1+len)
            curx += interval
            
class Vert(T):
    "Fills the region with vertical lines"
    def draw(self, can, x1, y1, x2, y2):    
        interval = self.line_interval
        curx = x1
        while curx < x2:
            can.line(self.line_style, curx, y1, curx, y2)
            curx += interval
            
class Horiz(T):
    "Fills the region with horizontal lines"
    def draw(self, can, x1, y1, x2, y2):
        interval = self.line_interval
        cury = y1
        while cury < y2:
            can.line(self.line_style, x1, cury, x2, cury)            
            cury += interval
            
class Stitch(T):
    "Fills the region with horizontal and vertical lines."
    def draw(self, can, x1, y1, x2, y2):
        interval = self.line_interval
        cury = y1
        while cury < y2:
            can.line(self.line_style, x1, cury, x2, cury)
            cury += interval
        curx = x1
        while curx < x2:
            can.line(self.line_style, curx, y1, curx, y2)
            curx += interval

class Wave(T):
    "Fills the region with horizontal wavy lines."
    def draw(self, can, x1, y1, x2, y2):
        x1 = xscale(x1)
        x2 = xscale(x2)
        y1 = yscale(y1)
        y2 = yscale(y2)
        line_width = nscale(self.line_style.width)
        interval = nscale(self.line_interval)
        
        can.set_line_style(self.line_style)        
        x1 -= line_width
        x2 += line_width
        cury = y1
        half = interval/2.0
        while cury < y2:
            curx = x1
            can.newpath()
            can.moveto(curx, cury)
            while curx < x2:
                can.lineto(curx + half, cury + half)
                can.lineto(curx + interval, cury)
                curx += interval
            can.stroke()
            cury += interval

class Vwave(T):
    """Fills the region with vertical wavy lines."""
    def draw(self, can, x1, y1, x2, y2):
        x1 = xscale(x1)
        x2 = xscale(x2)
        y1 = yscale(y1)
        y2 = yscale(y2)
        line_width = nscale(self.line_style.width)
        interval = nscale(self.line_interval)
        
        can.set_line_style(self.line_style)
        y1 -= line_width
        y2 += line_width
        curx = x1
        half = interval/2.0
        while curx < x2:
            cury = y1
            can.newpath()
            can.moveto(curx, cury)
            while cury < y2:
                can.lineto(curx + half, cury + half)
                can.lineto(curx, cury + interval)
                cury += interval
            can.stroke()
            curx += interval        

class Lines(T):
    """Fills the region with a series of short line segments."""
    def draw(self, can, x1, y1, x2, y2):
        interval = nscale(self.line_interval)
        cury = y1
        j = 0
        while cury < y2:
            curx = x1
            if j % 2 == 1:
                curx += interval/2.0
            while curx < x2:
                can.line(self.line_style, curx, cury, curx+interval/2.0, cury)
                curx += interval * 1.5
            j += 1
            cury += interval

default = Plain()

color_standards = object_set.T()
grayscale_standards = object_set.T()

def _intern_both(style):
    global color_standards, grayscale_standards
    color_standards.add(style)
    grayscale_standards.add(style)
    return style

def _intern_color(style):
    global color_standards, grayscale_standards    
    color_standards.add(style)
    return style

def _intern_grayscale(style):
    global color_standards, grayscale_standards    
    grayscale_standards.add(style)
    return style

black = _intern_both(Plain(bgcolor=color.gray_scale(0.0), line_style=None))

red = _intern_color(Plain(bgcolor=color.red))
darkseagreen = _intern_color(Plain(bgcolor=color.darkseagreen))
blue = _intern_color(Plain(bgcolor=color.blue))
aquamarine1 = _intern_color(Plain(bgcolor=color.aquamarine1))
gray70 = _intern_both(Plain(bgcolor=color.gray70, line_style=None))
brown = _intern_color(Plain(bgcolor=color.brown))
darkorchid = _intern_color(Plain(bgcolor=color.darkorchid))    
diag = _intern_both(Diag(line_style=line_style.T(cap_style=2)))
green = _intern_color(Plain(bgcolor=color.green))
gray50 = _intern_both(Plain(bgcolor=color.gray50, line_style=None))
white = _intern_both(Plain(bgcolor=color.gray_scale(1.0), line_style=None))
goldenrod = _intern_color(Plain(bgcolor=color.goldenrod))
rdiag = _intern_both(Rdiag(line_style=line_style.T(cap_style=2)))
vert = _intern_both(Vert(line_interval=1.8))

gray30 = _intern_both(Plain(bgcolor=color.gray30, line_style=None))
gray20 = _intern_both(Plain(bgcolor=color.gray20, line_style=None))
gray10 = _intern_both(Plain(bgcolor=color.gray10, line_style=None))
diag2 = _intern_both(Diag(line_style=line_style.T(width=3, cap_style=2),
                      line_interval=6))
rdiag2 = _intern_both(Rdiag(line_style=line_style.T(width=3, cap_style=2),
                        line_interval=6))
yellow = _intern_color(Plain(bgcolor=color.yellow))
diag3 = _intern_both(Diag(line_style=line_style.T(width=3, color=color.gray50, cap_style=2),
                      line_interval=6))
horiz = _intern_both(Horiz(line_interval=1.8))
gray90 = _intern_both(Plain(bgcolor=color.gray90, line_style=None))
rdiag3 = _intern_both(Rdiag(line_style=line_style.T(width=3,
                                                          color=color.gray50,
                                                          cap_style=2),
                        line_interval=6))

wave = _intern_both(Wave(line_style=line_style.T(cap_style=2, join_style=1)))
vwave = _intern_both(Vwave(line_style=line_style.T(cap_style=2, join_style=1)))
stitch = _intern_both(Stitch(line_style=line_style.T(cap_style=2, join_style=1)))
lines = _intern_both(Lines(line_style=line_style.T()))

diag_fine = _intern_both(Diag(line_style=line_style.T(width=0.75,cap_style=2),
                              line_interval = 1.5))
diag2_fine = _intern_both(Diag(line_style=line_style.T(width=0.75, cap_style=2),
                               line_interval=1.5))
diag3_fine = _intern_both(Diag(line_style=line_style.T(width=0.75,
                                                       color = color.gray50,
                                                       cap_style=2),
                               line_interval=1.5))
rdiag_fine = _intern_both(Rdiag(line_style=line_style.T(width=0.75,cap_style=2),
                              line_interval = 1.5))
rdiag2_fine = _intern_both(Rdiag(line_style=line_style.T(width=0.75, cap_style=2),
                               line_interval=1.5))
rdiag3_fine = _intern_both(Rdiag(line_style=line_style.T(width=0.75,
                                                       color = color.gray50,
                                                       cap_style=2),
                               line_interval=1.5))

horiz_fine = _intern_both(Horiz(line_interval=1.5))
vert_fine = _intern_both(Vert(line_interval=1.5))

#
# Fill styles for color charts.
#

standards = None
_name_table = None

def init():
    global standards, _name_table
    if theme.use_color:
        standards = color_standards
    else:
        standards = grayscale_standards
    _name_table = None

def name_table():
    global _name_table
    if not _name_table:
        _name_table = pychart_util.symbol_lookup_table(globals(), standards)
    return _name_table

init()
theme.add_reinitialization_hook(init)

