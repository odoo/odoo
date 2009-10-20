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
import color
import line_style
import fill_style
import chart_object
import object_set
import pychart_util
import tick_mark_doc
from pychart_types import *

_keys = {
    "line_style": (line_style.T, line_style.default, "The line style of the tick mark."),
    "fill_style": (fill_style.T, fill_style.white, "The fill style."),
    "size": (UnitType, 5, "Size of the tick mark."),
    }

class T(chart_object.T):
    __doc__ = tick_mark_doc.doc
    keys = _keys
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    
    def predraw_check(self):
	if not hasattr(self, "type_checked"):
	    self.type_check()
	self.type_checked = 1

class Circle(T):
    """Draws a circle. """
    def draw(self, can, x, y):
	self.predraw_check()
        can.ellipsis(self.line_style, self.fill_style, x, y,
                        self.size/2.0, 1)
        
class Square(T):
    """Draws a square."""
    def draw(self, can, x, y):
	self.predraw_check()
        # move to the bottom-left corner
        x = x - self.size/2.0
        y = y - self.size/2.0
        can.rectangle(self.line_style, self.fill_style,
                         x, y, x+self.size, y+self.size)

class Triangle(T):
    """Draws a triangle pointing up."""
    def draw(self, can, x, y):
	self.predraw_check()
        can.polygon(self.line_style, self.fill_style,
                       ((x-self.size/1.6, y-self.size/2.0),
                        (x+self.size/1.6, y-self.size/2.0),
                        (x, y+self.size/2.0)))
class DownTriangle(T):
    """Draws a triangle pointing down."""
    def draw(self, can, x, y):
	self.predraw_check()
        can.polygon(self.line_style, self.fill_style,
                       ((x, y-self.size/2.0),
                        (x-self.size/1.6, y+self.size/2.0),
                        (x+self.size/1.6, y+self.size/2.0)))


class X(T):
    """Draw a "X"-shaped tick mark. Attribute "fill-style" is ignored."""
    keys = pychart_util.union_dict(T.keys,
                         {"line_style": (line_style.T,
                                         line_style.T(width=0.7),
                                         "The line style of the tick mark")})
    def draw(self, can, x, y):
	self.predraw_check()
        # move to the bottom-left corner
        x = x - self.size/2.0
        y = y - self.size/2.0
        can.line(self.line_style, x, y, x+self.size, y+self.size)
        can.line(self.line_style, x+self.size, y, x, y+self.size)
        
class Plus(T):
    """Draw a "+"-shaped tick mark. Attribute "fill-style" is ignored."""
    keys = pychart_util.union_dict(T.keys,
                         {"line_style": (line_style.T, 
                                        line_style.T(width=1),
                                         "The line style of the tick mark.")})
    def draw(self, can, x, y):
	self.predraw_check()
        # move to the bottom-left corner
        can.line(self.line_style, x-self.size/1.4, y, x+self.size/1.4, y)
        can.line(self.line_style, x, y-self.size/1.4, x, y+self.size/1.4)
        
class Diamond(T):
    """Draw a square rotated at 45 degrees."""
    def draw(self, can, x, y):
	self.predraw_check()
        # move to the bottom-left corner
        can.polygon(self.line_style, self.fill_style,
                   ((x-self.size/1.4, y), (x, y+self.size/1.4),
                    (x+self.size/1.4, y), (x, y-self.size/1.4)))

class Star(T):
    """Draw a "*". Attribute "fill-style" is ignored."""
    keys = pychart_util.union_dict(T.keys,
                         {"line_style": (line_style.T,
                                        line_style.T(width=1),
                                         "The line style of the tick mark.")})
    def draw(self, can, x, y):
	self.predraw_check()
        # move to the bottom-left corner
        midx = x
        midy = y
        d_len = self.size / 2.0
        r_len = self.size * 1.414 / 2.0
        can.line(self.line_style, x-d_len, y-d_len, x+d_len, y+d_len)
        can.line(self.line_style, x+d_len, y-d_len, x-d_len, y+d_len) 
        can.line(self.line_style, midx, y-r_len, midx, y+r_len)
        can.line(self.line_style, x-r_len, midy, x+r_len, midy)
        
class Null(T):
    """This tickmark doesn't draw anything. All the attributes are ignored."""
    def __init__ (self):
        self.line_style = None
        self.fill_style = None
        self.size = -1
    def draw(self, can, x, y):
        pass
    
standards = object_set.T()
def _intern(style):
    standards.add(style)
    return style
     
square = _intern(Square())
square3 = _intern(Square(size=3))
square5 = square
x = _intern(X())
x3 = _intern(X(size=3))
x5 = x
star = _intern(Star())
star3 = _intern(Star(size=3))
star5 = star
plus = _intern(Plus())
plus3 = _intern(Plus(size=3))
plus5 = plus
dia = _intern(Diamond())
dia3 = _intern(Diamond(size=3))
dia5 = dia
tri = _intern(Triangle())
tri3 = _intern(Triangle(size=3))
tri5 = tri
dtri = _intern(DownTriangle())
dtri3 = _intern(DownTriangle(size=3))
dtri5 = dtri
circle1 = _intern(Circle(size=1))
circle2 = _intern(Circle(size=3))
circle3 = _intern(Circle(size=5))
blacksquare = _intern(Square(fill_style=fill_style.black))
blacksquare3 = _intern(Square(size=3, fill_style=fill_style.black))
blackdia = _intern(Diamond(fill_style=fill_style.black))
blackdia3 = _intern(Diamond(size=3, fill_style=fill_style.black))
blacktri = _intern(Triangle(fill_style=fill_style.black))
blacktri3 = _intern(Triangle(size=3, fill_style=fill_style.black))
blackdtri = _intern(DownTriangle(fill_style=fill_style.black))
blackdtri3 = _intern(DownTriangle(size=3, fill_style=fill_style.black))
blackcircle1 = _intern(Circle(size=1, fill_style=fill_style.black))
blackcircle3 = _intern(Circle(size=3, fill_style=fill_style.black))
gray70square = _intern(Square(fill_style=fill_style.gray70))
gray70square3 = _intern(Square(size=3, fill_style=fill_style.gray70))
gray70dia = _intern(Diamond(fill_style=fill_style.gray70))
gray70dia3 = _intern(Diamond(size=3, fill_style=fill_style.gray70))
gray70tri = _intern(Triangle(fill_style=fill_style.gray70))
gray70tri3 = _intern(Triangle(size=3, fill_style=fill_style.gray70))
gray70dtri = _intern(DownTriangle(fill_style=fill_style.gray70))
gray70dtri3 = _intern(DownTriangle(size=3, fill_style=fill_style.gray70))
gray70circle1 = _intern(Circle(size=1, fill_style=fill_style.gray70))
gray70circle3 = _intern(Circle(size=3, fill_style=fill_style.gray70))
default = _intern(Null())

