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
import tick_mark
import line_style
import pychart_util
import chart_object
import fill_style
import types
import error_bar_doc
import object_set
from pychart_types import *

__doc__ = """Pychart offers several styles of error bars. Some of them
only displays the min/max confidence interval, while others can display
quartiles in addition to min/max.""" 

class T(chart_object.T):
    keys = {}
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    pass

# Two horizontal lines at min & max locations.
class error_bar1(T):
    __doc__ = error_bar_doc.doc_1
    keys = {"tic_len" : (UnitType, 10, "Length of the horizontal bars"),
            "line_style": (line_style.T, line_style.default, "")
            }
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    def draw(self, can, loc, min, max, qmin = None, qmax = None):
        x = loc[0]
        y = min
        can.line(self.line_style, x-self.tic_len/2.0, y, x+self.tic_len/2.0, y)
        y = max
        can.line(self.line_style, x-self.tic_len/2.0, y, x+self.tic_len/2.0, y)

class error_bar2(T):
    __doc__ = error_bar_doc.doc_2
    keys = {"tic_len" : (UnitType, 3,
                        "The length of the horizontal bars"),
            "hline_style": (line_style.T, line_style.default,
                           "The style of the horizontal bars."),
            "vline_style": (line_style.T, None,
                           "The style of the vertical bar.")
             }

##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    def draw(self, can, loc, min, max, qmin = None, qmax = None):
        vline_style = self.vline_style
        if not vline_style:
            vline_style = self.hline_style
        x = loc[0]
        y1 = min
        can.line(self.hline_style, x-self.tic_len/2.0, y1, x+self.tic_len/2.0, y1)
        y2 = max
        can.line(self.hline_style, x-self.tic_len/2.0, y2, x+self.tic_len/2.0, y2)
        can.line(vline_style, x, y1, x, y2)

class error_bar3(T):
    # Tufte style
    __doc__ = "This style is endorsed by the Tufte's books. " \
              + error_bar_doc.doc_3
    keys = { "line_style": (line_style.T, line_style.default, "")
             }

##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    def draw(self, can, loc, min, max, qmin, qmax):
        x = loc[0]
        can.line(self.line_style, x, min, x, qmin)
        can.line(self.line_style, x, qmax, x, max)

class error_bar4(T):
    __doc__ = error_bar_doc.doc_4
    keys = { "line_style": (line_style.T, line_style.default, ""),
             "fill_style": (fill_style.T, fill_style.gray70, ""),
             "box_width": (UnitType, 4, ""),
             "tic_len": (UnitType, 4, "")
             }
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    def draw(self, can, loc, min, max, qmin, qmax):
        x = loc[0]
        style = self.line_style
        y1 = min
        can.line(style, x-self.tic_len/2.0, y1, x+self.tic_len/2.0, y1)
        y2 = max
        can.line(style, x-self.tic_len/2.0, y2, x+self.tic_len/2.0, y2)
        can.line(style, x, y1, x, y2)

        can.rectangle(style, self.fill_style,
                      x-self.box_width/2.0, qmin,
                      x+self.box_width/2.0, qmax)

# vertical line
class error_bar5(T):
    __doc__ = error_bar_doc.doc_5
    keys = { "line_style": (line_style.T, line_style.default, "")
             }
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    def draw(self, can, loc, min, max, qmin = None, qmax = None):
        x = loc[0]
        y = loc[1]

        min = (min - y) *1 + y
        max = (max - y) *1+ y
        can.line(self.line_style, x, min, x, max)

# a box
class error_bar6(T):
    __doc__ = error_bar_doc.doc_6
    keys = { "line_style": (line_style.T, line_style.default, ""),
             "fill_style": (fill_style.T, fill_style.gray70, ""),
             "center_line_style": (line_style.T, line_style.T(width=0.5), ""),
             "box_width": (UnitType, 4, ""),
             }
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    def draw(self, can, loc, min, max, qmin = None, qmax = None):
        x = loc[0]
        y = loc[1]

        can.rectangle(self.line_style, self.fill_style,
                      x - self.box_width / 2.0, min,
                      x + self.box_width / 2.0, max)
        can.line(self.center_line_style,
                 x - self.box_width/2.0, (min+max)/2.0,
                 x + self.box_width/2.0, (min+max)/2.0)

bar1 = error_bar1()
bar2 = error_bar2()
bar3 = error_bar3()
bar4 = error_bar4()
bar5 = error_bar5()
bar6 = error_bar6()

standards = object_set.T(bar1, bar2, bar3, bar4, bar5, bar6)

