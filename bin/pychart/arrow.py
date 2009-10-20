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
import line_style
import color
import chart_object
import object_set
import math
import arrow_doc
import canvas

from pychart_types import *
from types import *
from scaling import *

__doc__ = """
Arrow is an optional component of a chart that draws line segments with
an arrowhead. To draw an arrow, one creates an arrow.T object, and calls
its "draw" method usually after area.draw() is called (otherwise, area.draw()
may overwrite the arrow). For example, the below code draws an arrow
from (10,10) to (20,30).

ar = area.T(...)
a = arrow.T(head_style = 1)
ar.draw()
a.draw([(10,10), (20,30)])
"""

def draw_arrowhead(can, tailx, taily, tipx, tipy, thickness, head_len, style):
    can.comment("ARROWHEAD tail=(%d,%d) tip=(%d,%d)\n" 
	        % (tailx, taily, tipx, tipy))
    
    halfthickness = thickness/2.0
    dx = tipx - tailx
    dy = tipy - taily
    arrow_len = math.sqrt(dx*dx + dy*dy)
    angle = math.atan2(dy, dx) * 360 / (2*math.pi)
    base = arrow_len - head_len
    can.push_transformation((tailx, taily), None, angle)    

    can.newpath()
    if style == 0:
        can.moveto(base, - halfthickness)
        can.lineto(base, halfthickness)
        can.lineto(arrow_len, 0)
        can.closepath()
    elif style == 1:
        depth = head_len / 2.5
        can.moveto(base - depth, -halfthickness)
        can.lineto(base, 0)
        can.lineto(base - depth, halfthickness)
        can.lineto(arrow_len, 0)
        can.closepath()
    elif style == 2:
        can.moveto(base + head_len/2.0, 0)
        can.path_arc(base + head_len / 2.0, 0, head_len / 2.0, 1.0, 0, 400)
    elif style == 3:
        can.moveto(base, 0)
        can.lineto(base + head_len/2.0, -halfthickness)
        can.lineto(arrow_len, 0)
        can.lineto(base + head_len/2.0, halfthickness)
        can.closepath()
    else:
        raise Exception, "Arrow style must be a number between 0 and 3."
    can.fill()
    can.pop_transformation()
    can.comment("end ARROWHEAD.\n")

def draw_arrowbody(can, tailx, taily, tipx, tipy, head_len):
    dx = tipx - tailx
    dy = tipy - taily
    arrow_len = math.sqrt(dx*dx + dy*dy)
    angle = math.atan2(dy, dx) * 360 / (2*math.pi)
    base = arrow_len - head_len
    can.push_transformation((tailx, taily), None, angle)
    can.moveto(0, 0)
    can.lineto(base+head_len*0.1, 0)
    can.stroke()
    can.pop_transformation()


class T(chart_object.T):
    __doc__ = arrow_doc.doc
    keys = {
        "thickness" : (UnitType, 4,
                        "The width of the arrow head."),
        "head_len": (UnitType, 8,
                    "The length of the arrow head."),
        "head_color": (color.T, color.default,
                      "The color of the arrow head."),
        "line_style": (line_style.T, line_style.default,
                       "Line style."),
        "head_style": (IntType, 1,
                       "The value of 0 draws a triangular arrow head. The value of 1 draws a swallow-tail arrow head. The value of 2 draws a circular head. The value of 3 draws a diamond-shaped head.")
            }
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    def draw(self, points, can = None):
        """Parameter <points> specifies the
        list of points the arrow traverses through.
        It should contain at least two points, i.e.,
        the tail and tip. Parameter
        <can> is an optional parameter that specifies the output.
        <<canvas>>
        """
        if can == None: can = canvas.default_canvas()
        self.type_check()
        xtip = points[-1][0]
        ytip = points[-1][1]
        
        xtail = points[-2][0]
        ytail = points[-2][1]

        can.newpath()
        can.set_line_style(self.line_style)
        if len(points) > 2:
            can.moveto(points[0][0], points[0][1])
            for i in range(1, len(points)-1):
                can.lineto(points[i][0], points[i][1])

        draw_arrowbody(can, xscale(xtail), yscale(ytail),
                       yscale(xtip), yscale(ytip),
                       nscale(self.head_len))

        can.set_fill_color(self.head_color)
        draw_arrowhead(can, xscale(xtail), yscale(ytail),
                       xscale(xtip), yscale(ytip),
                       nscale(self.thickness),
                       nscale(self.head_len),
                       self.head_style)
        
        can.setbb(xtail, ytail)
        can.setbb(xtip, ytip)

standards = object_set.T()
def _intern(a):
    global standards
    standards.add(a)
    return a

a0 = _intern(T(head_style=0))
a1 = _intern(T(head_style=1))
a2 = _intern(T(head_style=2))
a3 = _intern(T(head_style=3))
gray0 = _intern(T(head_style=0, head_color = color.gray50,
                  line_style=line_style.T(color=color.gray50)))
gray1 = _intern(T(head_style=1, head_color = color.gray50,
                  line_style=line_style.T(color=color.gray50)))
gray2 = _intern(T(head_style=2, head_color = color.gray50,
                  line_style=line_style.T(color=color.gray50)))
gray3 = _intern(T(head_style=3, head_color = color.gray50,
                  line_style=line_style.T(color=color.gray50)))

fat0 = _intern(T(head_style=0, head_len=12, thickness=10, line_style=line_style.T(width=2)))
fat1 = _intern(T(head_style=1, head_len=12, thickness=10, line_style=line_style.T(width=2)))
fat2 = _intern(T(head_style=2, head_len=12, thickness=10, line_style=line_style.T(width=2)))
fat3 = _intern(T(head_style=3, head_len=12, thickness=10, line_style=line_style.T(width=2)))
fatgray0 = _intern(T(head_style=0, head_len=12, thickness=10,
                      head_color = color.gray50,
                      line_style=line_style.T(width=2, color=color.gray50)))
fatgray1 = _intern(T(head_style=1, head_len=12, thickness=10,
                      head_color = color.gray50,
                      line_style=line_style.T(width=2, color=color.gray50)))
fatgray2 = _intern(T(head_style=2, head_len=12, thickness=10,
                      head_color = color.gray50,
                      line_style=line_style.T(width=2, color=color.gray50)))
fatgray3 = _intern(T(head_style=3, head_len=12, thickness=10,
                      head_color = color.gray50,
                      line_style=line_style.T(width=2, color=color.gray50)))

default = a1


