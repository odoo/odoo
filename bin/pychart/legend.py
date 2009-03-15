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
import font
import line_style
import color
import fill_style
import chart_object
import pychart_util
import types
import legend_doc
import theme

from pychart_types import *
from types import *

class Entry(chart_object.T):
    keys = {"line_len" : (UnitType, None,
                          "Length of the sample line for line plots. If omitted, it is set to be theme.default_font_size"),
            "rect_size" : (UnitType, None,
                           "Size of the sample 'blob' for bar range charts. If omitted, it is set to be 70% of theme.default_size"),
            "tick_mark": (tick_mark.T, None, ""),
            "line_style": (line_style.T, None, ""),
            "fill_style": (fill_style.T, None, ""),
            "label": (StringType, "???", ""),
            }
    __doc__ = legend_doc.doc_entry
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    
    def label_width(self):
        return font.text_width(" " + self.label)
    def get_line_len(self):
        return self.line_len or theme.default_font_size
    def get_rect_size(self):
        return self.rect_size or theme.default_font_size * 7 / 10.0
        
    def sample_width(self):
        w = 0
        if self.fill_style != None:
            w += self.get_line_len()
        elif self.line_style != None:
            w += self.get_line_len()
        elif self.tick_mark != None:
            w += self.tick_mark.size
        return w
    def height(self):
        h = font.text_height(self.label)[0]
        return h
    
    def draw(self, ar, can, x_tick, x_label, y):
        """Draw a legend entry. X_TICK and X_LABEL are the X location \
        (in points) of where the sample and label are drawn."""

        rect_size = self.get_rect_size()
        line_len = self.get_line_len()
        
        nr_lines = len(self.label.split("\n"))
        text_height = font.text_height(self.label)[0]
        line_height = text_height / float(nr_lines)
        y_center = y + text_height - line_height/1.5
            
        if self.fill_style != None:
            can.rectangle(self.line_style, self.fill_style,
                             x_tick, y_center - rect_size/2.0,
                             x_tick + rect_size,
                             y_center + rect_size/2.0)
        elif self.line_style != None:
            can.line(self.line_style, x_tick, y_center,
                     x_tick + line_len, y_center)
            if self.tick_mark != None:
                self.tick_mark.draw(can, x_tick + line_len/2.0, y_center)
        elif self.tick_mark != None:
            self.tick_mark.draw(can, x_tick, y_center)
            
        can.show(x_label, y, self.label)

__doc__ = """Legend is a rectangular box drawn in a chart to describe
the meanings of plots. The contents of a legend box is extracted from
plots' "label", "line-style", and "tick-mark" attributes.

This module exports a single class, legend.T.  Legend.T is a part of
an area.T object, and is drawn automatically when area.draw() method
is called. """

class T(chart_object.T):
    __doc__ = legend_doc.doc
    keys = {
        "inter_row_sep": (UnitType, 0,
                          "Space between each row in the legend."),
        "inter_col_sep": (UnitType, 0,
                          "Space between each column in the legend."),
        "frame_line_style": (line_style.T, line_style.default, ""),
        "frame_fill_style": (fill_style.T, fill_style.white, ""),
        "top_fudge": (UnitType, 0,
                      "Amount of space above the first line."),
        "bottom_fudge": (UnitType, 3,
                         "Amount of space below the last line."),
        "left_fudge": (UnitType, 5,
                       "Amount of space left of the legend."),
        "right_fudge": (UnitType, 5,
                        "Amount of space right of the legend."),
        "loc": (CoordType, None,
                """Bottom-left corner of the legend.
                The default location of a legend is the bottom-right end of the chart."""),
	"shadow": (ShadowType, None, pychart_util.shadow_desc),
        "nr_rows": (IntType, 9999, "Number of rows in the legend. If the number of plots in a chart is larger than nr_rows, multiple columns are created in the legend."),

        }
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    def draw(self, ar, entries, can):
        if not self.loc:
            x = ar.loc[0] + ar.size[0] * 1.1
            y = ar.loc[1]
        else:
            x = self.loc[0]
            y = self.loc[1]

        nr_rows = min(self.nr_rows, len(entries))
        nr_cols = (len(entries)-1) / nr_rows + 1
        
        ymin = y
	max_label_width = [0] * nr_cols
        max_sample_width = [0] * nr_cols
        heights = [0] * nr_rows
        
        for i in range(len(entries)):
            l = entries[i]
            (col, row) = divmod(i, nr_rows)
            max_label_width[col] = max(l.label_width(), max_label_width[col])
            max_sample_width[col] = max(l.sample_width(), max_sample_width[col])
            heights[row] = max(l.height(), heights[row])

        for h in heights:
            y += h
        y += self.inter_row_sep * (nr_rows - 1)
        ymax = y

        tot_width = self.inter_col_sep * (nr_cols -1)
        for w in max_label_width:
            tot_width += w
        for w in max_sample_width:
            tot_width += w
            
	can.rectangle(self.frame_line_style, self.frame_fill_style,
                      x - self.left_fudge,	
                      ymin - self.bottom_fudge,	
                      x + tot_width + self.right_fudge,
                      ymax + self.top_fudge,
                      self.shadow)

        for col in range(nr_cols):
            this_y = y
            this_x = x
            for row in range(nr_rows):
                idx = col * nr_rows + row
                if idx >= len(entries):
                    continue
                this_y -= heights[row]
                l = entries[idx]
                if row != 0:
                    this_y -= self.inter_row_sep
                    
                l.draw(ar, can, this_x, this_x + max_sample_width[col], this_y)
            x += max_label_width[col] + max_sample_width[col] + self.inter_col_sep


