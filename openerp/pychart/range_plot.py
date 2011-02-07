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
import pychart_util
import chart_object
import fill_style
import legend
import range_plot_doc
from pychart_types import *
from types import *
from scaling import *


class T(chart_object.T):
    __doc__ = range_plot_doc.doc
    keys = {
        "data" : (AnyType, None, pychart_util.data_desc),
        "label": (StringType, "???", pychart_util.label_desc),
        "xcol" : (IntType, 0, pychart_util.xcol_desc),
        "min_col": (IntType, 1,
                   "The lower bound of the sweep is extracted from "
                   + "this column of data."),
        "max_col": (IntType, 2, 
                   "The upper bound of the sweep is extracted from "
                   + "this column of data."),
        "line_style": (line_style.T, line_style.default,
                      "The style of the boundary line."),
        "fill_style": (fill_style.T, fill_style.default,
                      ""),
        }
    
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED

    def check_integrity(self):
	self.type_check()
    def get_data_range(self, which):
        if which == 'X':
            return pychart_util.get_data_range(self.data, self.xcol)
        else:
            ymax = (pychart_util.get_data_range(self.data, self.max_col))[1]
            ymin = (pychart_util.get_data_range(self.data, self.min_col))[0]
            return (ymin, ymax)
    def get_legend_entry(self):
        if self.label:
            return legend.Entry(line_style=self.line_style,
                                fill_style=self.fill_style,
                                label=self.label)
        return None

    def draw(self, ar, can):
        
        prevPair = None

        xmin=999999
        xmax=-999999
        ymin=999999
        ymax=-999999

        # Draw the boundary in a single stroke.
        can.gsave()
        can.newpath()
        for pair in self.data:
            x = pair[self.xcol]
            y = pychart_util.get_sample_val(pair, self.max_col)
            if y == None:
                continue
            
            xmin = min(xmin, ar.x_pos(x))
            xmax = max(xmax, ar.x_pos(x))
            ymin = min(ymin, ar.y_pos(y))
            ymax = max(ymax, ar.y_pos(y))
            if prevPair != None:
                can.lineto(xscale(ar.x_pos(x)), yscale(ar.y_pos(y)))
            else:
                can.moveto(xscale(ar.x_pos(x)), yscale(ar.y_pos(y)))
            prevPair = pair

        for i in range(len(self.data)-1, -1, -1):
            pair = self.data[i]
            x = pair[self.xcol]
            y = pychart_util.get_sample_val(pair, self.min_col)
            if None in (x, y):
                continue

            xmin = min(xmin, ar.x_pos(x))
            xmax = max(xmax, ar.x_pos(x))
            ymin = min(ymin, ar.y_pos(y))
            ymax = max(ymax, ar.y_pos(y))
            can.lineto(xscale(ar.x_pos(x)), yscale(ar.y_pos(y)))
        can.closepath()

        # create a clip region, and fill it.
        can.clip_sub()
        can.fill_with_pattern(self.fill_style, xmin, ymin, xmax, ymax)
        can.grestore()

        if self.line_style: 
            # draw the boundary.
            prevPair = None
            can.newpath()
            can.set_line_style(self.line_style)
            for pair in self.data:
                x = pair[self.xcol]
                y = pychart_util.get_sample_val(pair, self.min_col)
                if None in (x, y):
                    continue

                if prevPair != None:
                    can.lineto(xscale(ar.x_pos(x)), yscale(ar.y_pos(y)))
                else:
                    can.moveto(xscale(ar.x_pos(x)), yscale(ar.y_pos(y)))
                prevPair = pair
            can.stroke()

            prevPair = None
            can.newpath()
            can.set_line_style(self.line_style)
            for pair in self.data:
                x = pair[self.xcol]
                y = pychart_util.get_sample_val(pair, self.max_col)
                if y == None:
                    continue

                if prevPair != None:
                    can.lineto(xscale(ar.x_pos(x)), yscale(ar.y_pos(y)))
                else:
                    can.moveto(xscale(ar.x_pos(x)), yscale(ar.y_pos(y)))
                prevPair = pair
            can.stroke()


