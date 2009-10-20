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
import font
import pychart_util
import chart_object
import line_style
import math
import theme
import axis_doc
from pychart_types import *
from types import *

class T(chart_object.T):
    keys = {
       "tic_interval" : (IntervalType, None, 
                         pychart_util.interval_desc("tick marks")),
       "tic_len" : (UnitType, 6, """The length of tick lines. The value can be negative, in which case the tick lines are drawn right of (or above) the axis."""),
       "minor_tic_interval" : (IntervalType, None,
                               pychart_util.interval_desc("minor tick marks")),
       "minor_tic_len" : (UnitType, 3, """The length of minor tick marks.  The value can be negative, in which case the tick lines are drawn right of (or above) the axis."""),
       "line_style": (line_style.T, line_style.default, 
                      "Specifies the style of axis and tick lines."),
       "label": (types.StringType, "axis label",
                 "The descriptive string displayed below (or to the left of) the axis. <<font>>."),
       "format": (FormatType, "%s", 
                  """The format string for tick labels.
                  It can be a `printf' style format string, or 
                  a single-parameter function that takes an X (or Y) value
                  and returns a string. """ +
                  pychart_util.string_desc),
       "label_offset": (CoordOrNoneType, (None,None),
                        """The location for drawing the axis label, 
                        relative to the middle point of the axis.
                        If the value is None, the label is displayed
                        below (or to the left of) of axis at the middle."""),
       "tic_label_offset": (CoordType, (0,0),
                            """The location for drawing tick labels, 
                            relative to the tip of the tick line."""),
       "offset": (UnitType, 0,
                  """The location of the axis. 
                  The value of 0 draws the
                  axis at the left (for the Y axis) or bottom (for the X axis)
                  edge of the drawing area.
                  """)
       }

class X(T):
    keys = pychart_util.union_dict(T.keys,
                                   {"draw_tics_above": (IntType, 0,
                                                        "If true, tick lines and labels are drawn above the axis line.")})
    __doc__ = axis_doc.doc_x
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    def draw_below(self, ar, can):
        self.type_check()
        self.tic_interval = self.tic_interval or ar.x_grid_interval
        y_base = ar.loc[1] + self.offset
      
        can.line(self.line_style, ar.loc[0], y_base,
                    ar.loc[0]+ ar.size[0], y_base)

        tic_dic = {}
        max_tic_height = 0
      
        for i in ar.x_tic_points(self.tic_interval):
            tic_dic[i] = 1
            ticx = ar.x_pos(i)

            str = "/hC" + pychart_util.apply_format(self.format, (i, ), 0)

            (total_height, base_height) = font.text_height(str)
            max_tic_height = max(max_tic_height, total_height)

            can.line(self.line_style, ticx, y_base, ticx, y_base-self.tic_len)
            can.show(ticx+self.tic_label_offset[0], 
                        y_base-self.tic_len-base_height+self.tic_label_offset[1],
                        str)
         
        if self.minor_tic_interval:
            for i in ar.x_tic_points(self.minor_tic_interval):
                if tic_dic.has_key(i):
                    # a major tic was drawn already.
                    pass
                else:
                    ticx = ar.x_pos(i)
                    can.line(self.line_style, ticx, y_base, ticx,
                                y_base-self.minor_tic_len)

        self.draw_label(ar, can, y_base - self.tic_len - max_tic_height - 10)
        
    def draw_above(self, ar, can):
        y_base = ar.loc[1] + self.offset
      
        tic_dic = {}
        max_tic_height = 0
      
        for i in ar.x_tic_points(self.tic_interval):
            tic_dic[i] = 1
            ticx = ar.x_pos(i)

            str = "/hC" + pychart_util.apply_format(self.format, (i, ), 0)

            (total_height, base_height) = font.text_height(str)
            max_tic_height = max(max_tic_height, total_height)

            can.line(self.line_style, ticx, y_base, ticx, y_base + self.tic_len)
            can.show(ticx+self.tic_label_offset[0], 
                     y_base + self.tic_len + base_height + self.tic_label_offset[1],
                     str)
         
        if self.minor_tic_interval:
            for i in ar.x_tic_points(self.minor_tic_interval):
                if tic_dic.has_key(i):
                    # a major tic was drawn already.
                    pass
                else:
                    ticx = ar.x_pos(i)
                    can.line(self.line_style, ticx, y_base, ticx,
                             y_base + self.minor_tic_len)
        self.draw_label(ar, can, y_base + self.tic_len + max_tic_height + 10)
        
    def draw_label(self, ar, can, ylabel):
        if self.label == None: return
    
        str = "/hC/vM" + self.label
        (label_height, base_height) = font.text_height(str)
        xlabel = ar.loc[0] + ar.size[0]/2.0
        if self.label_offset[0] != None:
            xlabel += self.label_offset[0]
        if self.label_offset[1] != None:
            ylabel += self.label_offset[1]
        can.show(xlabel, ylabel, str)
        
    def draw(self, ar, can):
        self.type_check()
        self.tic_interval = self.tic_interval or ar.x_grid_interval
        y_base = ar.loc[1] + self.offset
        can.line(self.line_style, ar.loc[0], y_base,
                 ar.loc[0]+ ar.size[0], y_base)
        if self.draw_tics_above:
            self.draw_above(ar, can)
        else:
            self.draw_below(ar, can)
class Y(T):
    __doc__ = axis_doc.doc_y   
    keys = pychart_util.union_dict(T.keys,
                                   {"draw_tics_right": (IntType, 0,
                                                        "If true, tick lines and labels are drawn right of the axis line.")})
    
    def draw_left(self, ar, can):
        x_base = ar.loc[0] + self.offset
        xmin = 999999
        tic_dic = {}
        for i in ar.y_tic_points(self.tic_interval):
            y_tic = ar.y_pos(i)
            tic_dic[i] = 1
            can.line(self.line_style, x_base, y_tic,
                     x_base - self.tic_len, y_tic)
            str = pychart_util.apply_format(self.format, (i,), 0)
            if self.tic_len > 0: str = "/hR" + str

            tic_height, base_height = font.text_height(str)
            x = x_base - self.tic_len + self.tic_label_offset[0]
            can.show(x, y_tic - tic_height/2.0 + self.tic_label_offset[1],
                     str)
            xmin = min(xmin, x - font.text_width(str))
            
        if self.minor_tic_interval:
            for i in ar.y_tic_points(self.minor_tic_interval):
                if tic_dic.has_key(i):
                    # a major tic line was drawn already.
                    pass
                else:
                    y_tic = ar.y_pos(i)
                    can.line(self.line_style, x_base, y_tic,
                             x_base - self.minor_tic_len, y_tic)
               
        self.draw_label(ar, can, xmin - theme.default_font_size/2.0)

    def draw_right(self, ar, can):
        x_base = ar.loc[0] + self.offset
        xmax = 0
        tic_dic = {}
        for i in ar.y_tic_points(self.tic_interval):
            y_tic = ar.y_pos(i)
            tic_dic[i] = 1
            can.line(self.line_style, x_base, y_tic,
                     x_base + self.tic_len, y_tic)
            str = pychart_util.apply_format(self.format, (i,), 0)
            if self.tic_len > 0: str = "/hL" + str

            tic_height, base_height = font.text_height(str)
            x = x_base + self.tic_len + self.tic_label_offset[0]
            can.show(x, y_tic - tic_height/2.0 + self.tic_label_offset[1],
                     str)
            xmax = max(xmax, x + font.text_width(str))
            
        if self.minor_tic_interval:
            for i in ar.y_tic_points(self.minor_tic_interval):
                if tic_dic.has_key(i):
                    # a major tic line was drawn already.
                    pass
                else:
                    y_tic = ar.y_pos(i)
                    can.line(self.line_style, x_base, y_tic,
                             x_base + self.minor_tic_len, y_tic)

        self.draw_label(ar, can, xmax + theme.default_font_size)
        
    def draw_label(self, ar, can, xlabel):
        if self.label == None:
            return
        ylabel = ar.loc[1] + ar.size[1] / 2
        if self.label_offset[0] != None:
            xlabel += self.label_offset[0]
        if self.label_offset[1] != None:
            ylabel += self.label_offset[1]
        can.show(xlabel, ylabel, "/a90/hC" + self.label)

    def draw(self, ar, can):
        self.type_check()
        self.tic_interval = self.tic_interval or ar.y_grid_interval
        
        x_base = ar.loc[0] + self.offset
        can.line(self.line_style, x_base, ar.loc[1], x_base, ar.loc[1]+ar.size[1])
        if self.draw_tics_right:
            self.draw_right(ar, can)
        else:
            self.draw_left(ar, can)
