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
import text_box
import fill_style
import line_style
import pychart_util
import chart_object
import arrow
import legend
import font
import pie_plot_doc
import theme

from pychart_types import *
from types import *

class T(chart_object.T):
    __doc__ = pie_plot_doc.doc
    keys = {
        "start_angle" : (NumType, 90,
                         """The angle at which the first item is drawn."""),
        "center" : (CoordType, None, "The location of the center of the pie."),
        "radius" : (UnitType, None, "The radius of the pie."),
        "line_style" : (line_style.T, line_style.default, "The style of the outer edge of each pie slice."),

        "fill_styles" : (ListType, fill_style.standards.list(),
                         """The fill style of each item. The length of the
                         list should be equal to the length of the data. 
                         """),
        "arc_offsets" : (ListType, None,
                         """You can draw each pie "slice" shifted off-center.
                         This attribute, if non-None,
                         must be a number sequence whose length is equal to
                         the number of pie slices. The Nth value in arc_offsets
                         specify the amount of offset
                         (from the center of the circle)
                         for the Nth slice.
                         The value of None will draw all the slices
                         anchored at the center. 
                         """
                         ),
        "data" : (AnyType, None, pychart_util.data_desc),
        "label_format" : (FormatType, "%s",
                          "Format string of the label"),
        "label_col" : (IntType, 0,
                       """The column, within "data", from which the labels of items are retrieved."""),
        "data_col": (IntType, 1,
                     """ The column, within "data", from which the data values are retrieved."""),
        "label_offset": (UnitType, None, "The distance from the center of each label."),
        "arrow_style": (arrow.T, None,
                        """The style of arrow that connects a label
                        to the corresponding "pie"."""),
        "label_line_style": (line_style.T, None, "The style of the frame surrounding each label."),
        "label_fill_style": (fill_style.T, fill_style.default, "The fill style of the frame surrounding each label."),
        "shadow": (ShadowType, None, pychart_util.shadow_desc)
        }
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    def _total(self):
        v = 0
        for val in self.data:
            v += val[self.data_col]
        return v

    def check_integrity(self):
	self.type_check()
    def get_data_range(self, which):
        return (0, 1)
    def get_legend_entry(self):
        legends = []
        i = 0
        for val in self.data:
            fill = self.fill_styles[i]
            i = (i + 1) % len(self.fill_styles)
            legends.append(legend.Entry(line_style=self.line_style,
                                        fill_style=fill, 
                                        label=val[self.label_col]))
        return legends
    
    def draw(self, ar, can):
        center = self.center
        if not center:
            center = (ar.loc[0] + ar.size[0]/2.0,
                      ar.loc[1] + ar.size[1]/2.0)
        radius = self.radius
        if not radius:
            radius = min(ar.size[0]/2.0, ar.size[1]/2.0) * 0.5

        label_offset = radius + (self.label_offset or radius * 0.1)
        
        total = self._total()
        i = 0
        cur_angle = self.start_angle
        for val in self.data:
            fill = self.fill_styles[i]
            degree = 360 * float(val[self.data_col]) / float(total)
            
            off = (0, 0)
            if len(self.arc_offsets) > i:
                off = pychart_util.rotate(self.arc_offsets[i], 0, cur_angle - degree/2.0)
            x_center = center[0]+ off[0]
            y_center = center[1]+ off[1]
            
            can.ellipsis(self.line_style, fill,
                         x_center, y_center, radius, 1,
                         cur_angle - degree, cur_angle,
                         self.shadow)

            label = pychart_util.apply_format(self.label_format, val,
                                              self.label_col)
            if label != None:
                (x_label, y_label) = pychart_util.rotate(label_offset, 0, cur_angle - degree/2.0)
                (x_arrowtip, y_arrowtip) = pychart_util.rotate(radius, 0, cur_angle - degree/2.0)
                # Labels on left side of pie need
                # their text to avoid obscuring the pie
                if x_label < 0:
                    x_label = x_label - font.text_width(label)

                t = text_box.T(loc = (x_label + x_center, y_label + y_center),
                               text = label,
                               line_style = self.label_line_style,
                               fill_style = self.label_fill_style)
                if self.arrow_style:
                    t.add_arrow((x_arrowtip + x_center, y_arrowtip + y_center),
                                None, self.arrow_style)

                t.draw(can)
            cur_angle = (cur_angle - degree) % 360
            i = (i + 1) % len(self.fill_styles)


def init():
    old_val = T.keys["fill_styles"]
    T.keys["fill_styles"] = (old_val[0], fill_style.standards.list(),
                             old_val[2])
theme.add_reinitialization_hook(init)
