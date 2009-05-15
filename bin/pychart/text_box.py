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
import canvas
import line_style
import pychart_util
import fill_style
import font
import chart_object
import color
import arrow
import text_box_doc
from pychart_types import *
from types import *

class T(chart_object.T):
    __doc__ = text_box_doc.doc
    keys = {"text": (StringType, "???", "Text body. <<font>>"),
            "loc": (TupleType, (0,0),
                    "The location of the text box."),
            "line_style": (line_style.T, line_style.default,
                           """The line style of the surrounding frame."""),
            "fill_style": (fill_style.T, fill_style.white,
                           "Specifies the fill style of the text box."),
            "top_fudge": (UnitType, 0,
                          "The amount of space (in points) above the first line"),
            "bottom_fudge": (UnitType, 5,
                             "The amount of space below the last line"),
            "left_fudge": (UnitType, 5,
                           "The amount of space left of the box"),
            "right_fudge": (UnitType, 5,
                            "The amount of space right of the box"),
            "_arrows": (ListType, pychart_util.new_list, "The list of arrows. Not to be touched by the user directly"),
	    "radius": (UnitType, 0,
                       """Radius of the four corners of the rectangle.
                       If the value is zero, a sharp-cornered
                       rectangle is drawn."""),
            "shadow": (ShadowType, None,
                       pychart_util.shadow_desc)
            }
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    def get_dimension(self):
        x = self.loc[0] - self.left_fudge
        y = self.loc[1] - self.bottom_fudge
        width = font.text_width(self.text) + self.right_fudge + self.left_fudge
        height = (font.text_height(self.text))[0] + self.top_fudge + self.bottom_fudge
        return (x, y, width, height)
    
    def choose_end_point(self, tipx, tipy):
        (x, y, width, height) = self.get_dimension()
        
        minDist = -1
        minPoint = None
        vertices = [(x, y),
                    (x+width, y),
                    (x+width, y+height),
                    (x, y+height)]
            
        if tipx >= x and tipx < x+width:
            vertices.append((tipx, y))
            vertices.append((tipx, y+height))
        if tipy >= y and tipy < y+height:
            vertices.append((x, tipy))
            vertices.append((x+width, tipy))
            
        for startPoint in vertices:
            dist = ((startPoint[0] - tipx) **2 + (startPoint[1] - tipy) **2)
            if not minPoint or dist < minDist:
                minPoint = startPoint
                minDist = dist
            
        return minPoint
    
    def add_arrow(self, tipLoc, tail=None, arrow = arrow.default):
        """This method adds a straight arrow that points to
        @var{TIPLOC}, which is a tuple of integers. @var{TAIL}
        specifies the starting point of the arrow. It is either None
        or a string consisting of the following letters: 'l', 'c',
        'r', 't', 'm,', and 'b'.  Letters 'l', 'c', or 'r' means to
        start the arrow from the left, center, or right of the text
        box, respectively. Letters 't', 'm', or 'b' means to start the
        arrow from the top, middle or bottom of the text box.  For
        example, when @samp{tail = 'tc'} then arrow is drawn from
        top-center point of the text box. ARROW specifies the style of
        the arrow. <<arrow>>.
        """
        self._arrows.append((tipLoc, tail, arrow))
        
    def draw(self, can = None):
        if can == None:
            can = canvas.default_canvas()
        x = self.loc[0]
        y = self.loc[1]
        text_width = font.text_width(self.text)
        text_height = font.text_height(self.text)[0]
        (halign, valign, angle) = font.get_align(self.text)
        
        if self.line_style or self.fill_style:
            width = text_width+self.left_fudge+self.right_fudge
            height = text_height+self.bottom_fudge+self.top_fudge
            can.round_rectangle(self.line_style, self.fill_style,
                                   x-self.left_fudge, y-self.bottom_fudge,
                                   x-self.left_fudge+width, y-self.bottom_fudge+height,
                                   self.radius, self.shadow)

        if halign == 'L':
            can.show(x, y, self.text)
        elif halign == 'C':
            can.show(x+text_width/2.0, y, self.text)
        elif halign == 'R':
            can.show(x+text_width, y, self.text)
        else:
            raise Exception, "Unsupported alignment (" + halign + ")"

        # draw arrows
        for t in self._arrows:
            (tipLoc, tail, arrow) = t
            if tail:
                (x, y, width, height) = self.get_dimension()
                origin = [x, y]
                for ch in tail:
                    if ch == 'l':
                        origin[0] = x
                    elif ch == 'c':
                        origin[0] = x+width/2.0
                    elif ch == 'r':
                        origin[0] = x+width
                    elif ch == 'b':
                        origin[1] = y
                    elif ch == 'm':
                        origin[1] = y+height/2.0
                    elif ch == 't':
                        origin[1] = y+height
                    else:
                        raise ValueError, tail +  ": unknown tail location spec."
            else:
                origin = self.choose_end_point(tipLoc[0], tipLoc[1])
            arrow.draw((origin, tipLoc), can)
            

