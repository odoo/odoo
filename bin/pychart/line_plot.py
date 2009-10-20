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
import tick_mark
import line_style
import pychart_util
import error_bar
import chart_object
import legend
import object_set
import line_plot_doc
import theme
from pychart_types import *
from types import *

default_width = 1.2
line_style_itr = None


_keys = {
    "data" : (AnyType, None, pychart_util.data_desc),
    "label": (StringType, "???", pychart_util.label_desc),
    "data_label_offset": (CoordType, (0, 5),
                          """The location of data labels relative to the sample point. Meaningful only when data_label_format != None."""),
    "data_label_format": (FormatType, None,
                          """The format string for the label printed 
                          beside a sample point.
                          It can be a `printf' style format string, or 
                          a two-parameter function that takes the (x, y)
                          values and returns a string. """
                          + pychart_util.string_desc),
    "xcol" : (IntType, 0, pychart_util.xcol_desc),
    "ycol": (IntType, 1, pychart_util.ycol_desc),
    "y_error_minus_col": (IntType, 2,
                          """The column (within "data") from which the depth of the errorbar is extracted. Meaningful only when error_bar != None. <<error_bar>>"""),
    "y_error_plus_col": (IntType, -1,
                         """The column (within "data") from which the height of the errorbar is extracted. Meaningful only when error_bar != None. <<error_bar>>"""),
    "y_qerror_minus_col":  (IntType, -1, "<<error_bar>>"),
    "y_qerror_plus_col":  (IntType, -1, "<<error_bar>>"),

    "line_style": (line_style.T, lambda: line_style_itr.next(), pychart_util.line_desc,
                   "By default, a style is picked from standard styles round-robin. <<line_style>>"),

    "tick_mark": (tick_mark.T, None, pychart_util.tick_mark_desc),
    "error_bar": (error_bar.T, None,
                  "The style of the error bar. <<error_bar>>"),
    }

class T(chart_object.T):
    __doc__ = line_plot_doc.doc
    keys =  _keys
    def check_integrity(self):
	self.type_check()
        
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    def get_data_range(self, which):
        if which == 'X':
            return pychart_util.get_data_range(self.data, self.xcol)
        else:
            return pychart_util.get_data_range(self.data, self.ycol)
    def get_legend_entry(self):
        if self.label:
            return legend.Entry(line_style=self.line_style,
                                tick_mark=self.tick_mark,
                                fill_style=None,
                                label=self.label)
        return None
    
    def draw(self, ar, can):

        # Draw the line

        clipbox = theme.adjust_bounding_box([ar.loc[0], ar.loc[1],
                                             ar.loc[0] + ar.size[0],
                                             ar.loc[1] + ar.size[1]]);
        
        can.clip(clipbox[0],clipbox[1],clipbox[2],clipbox[3])
        if self.line_style:
            points = []
            for pair in self.data:
                yval = pychart_util.get_sample_val(pair, self.ycol)
                xval = pair[self.xcol]
                if None not in (xval, yval):
                    points.append((ar.x_pos(xval), ar.y_pos(yval)))
            can.lines(self.line_style, points)
        can.endclip()
        
        # Draw tick marks and error bars
        can.clip(ar.loc[0] - 10, ar.loc[1] - 10,
                ar.loc[0] + ar.size[0] + 10,
                ar.loc[1] + ar.size[1] + 10)
        for pair in self.data:
            x = pair[self.xcol]
            y = pychart_util.get_sample_val(pair, self.ycol)
            if None in (x, y): continue
            
            x_pos = ar.x_pos(x)
            y_pos = ar.y_pos(y)

            if self.error_bar:
                plus = pair[self.y_error_plus_col or self.y_error_minus_col]
                minus = pair[self.y_error_minus_col or self.y_error_plus_col]
                if self.y_qerror_minus_col or self.y_qerror_plus_col:
                    q_plus = pair[self.y_qerror_plus_col or self.y_qerror_minus_col]
                    q_minus = pair[self.y_qerror_minus_col or self.y_qerror_plus_col]
                    if None not in (minus,plus,q_minus,q_plus):
                        self.error_bar.draw(can, (x_pos, y_pos),
                                            ar.y_pos(y - minus),
                                            ar.y_pos(y + plus),
                                            ar.y_pos(y - q_minus),
                                            ar.y_pos(y + q_plus))
                else:
                    if None not in (minus,plus): #PDS
                        self.error_bar.draw(can, (x_pos, y_pos),
                                            ar.y_pos(y - minus),
                                            ar.y_pos(y + plus))
                        
            if self.tick_mark:
                self.tick_mark.draw(can, x_pos, y_pos)
            if self.data_label_format:
                can.show(x_pos + self.data_label_offset[0],
                            y_pos + self.data_label_offset[1],
                            "/hC" + pychart_util.apply_format(self.data_label_format, (x, y), 1))

        can.endclip()

def init():
    global line_style_itr
    line_styles = object_set.T()
    for org_style in line_style.standards.list():
        style = line_style.T(width = default_width, color = org_style.color,
                             dash = org_style.dash)
        line_styles.add(style)

    line_style_itr = line_styles.iterate()

theme.add_reinitialization_hook(init)

