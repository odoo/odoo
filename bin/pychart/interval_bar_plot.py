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
import fill_style
import pychart_util
import chart_object
import legend
import bar_plot_doc
import theme
from types import *
from pychart_types import *

fill_styles = None

_keys = {
    "direction" : (StringType, "vertical",
                   """The direction the growth of the bars. The value is either 'horizontal'
                   or 'vertical'."""),
    "data" : (AnyType, None, """Specifes data points. Unlike other types
    of charts, the "hcol"th column of the data must be a sequence of
    numbers, not just a single number. See also the description of
    "hcol"."""
    ),
    "data_label_offset": (CoordType, (0, 5),
                          "The location of data labels relative to the sample point. See also attribute data_label_format."),
    
    "data_label_format": (FormatType, None, """The
                          format string for the label displayed besides each
                          bar.  It can be a `printf' style format
                          string, or a two-parameter function that
                          takes (x,y) values and returns a string. """
                          + pychart_util.string_desc),
    
    "label": (StringType, "???", pychart_util.label_desc), 
    "bcol" : (IntType, 0,
              """Specifies the column from which base values (i.e., X values when attribute "direction" is "vertical", Y values otherwise) are extracted.
The
              combination of "data", "bcol", and "hcol" attributes defines
              the set of boxes drawn by this chart.
              See also the descriptions of the 'bcol' and 'data' attributes.
              """),
    "hcol": (IntType, 1,
             """The column from which the base and height of
             bars are extracted. See the below example:
              
@example
              d = [[5,[10,15,22]], [7,[22,23,5,10]], [8,[25,3]]]
              p = interval_bar_plot.T(data = d, bcol = 0, hcol = 1)
@end example

              Here, three sequence of bars will be drawn.
              The X locations of the bars
              will be 5, 7, and 8. For example, at location X=7,
              three bars are drawn,
              one corresponding to Y values of 22 to 45 (=22+23),
              and the second one for values 45 to 50, and the third one
              for values 50 to 60. The line and fill styles of the bars
              are picked in a round-robin fashion
              from attributes "line_styles" and
              "fill_styles".
             """),
    "line_styles": (ListType, [line_style.default, None],
                    """The list of line styles for bars.
                    The style of each bar is chosen in a round-robin fashion, if the
                    number of elements in "line_styles" is smaller than
                    actual number of boxes."""),
    "fill_styles": (ListType, [lambda: fill_styles.next(), None],
                    """List of fill styles for bars.
                    The style of each bar is chosen in a round-robin fashion, if the
                    number of elements in "line_styles" is smaller than
                    actual number of boxes.
                    If this attribute is omitted,
                    a style is picked from standard styles round-robin. <<fill_style>>."""),
    "cluster": (TupleType, (0, 1), """This attribute is used to
    cluster multiple bar plots side by side in a single chart.
    The value should be a tuple of two integers. The second value should be equal to the total number of bar plots in the chart. The first value should be the relative position of this chart; 0 places this chart the leftmost, and N-1
    (where N is the 2nd value of this attribute) places this chart the rightmost. Consider the below example:

@example
    a = area.T(...)
    p1 = interval_bar_plot.T(data = [[1, [20,10]][2,[30,5]]], cluster=(0,2))
    p2 = interval_bar_plot.T(data = [[1,[25,11,2]],[2,[10,5,3]]], cluster=(1,2))
    a.add_plot(p1, p2)
    a.draw()
@end example

    In this example, one group of bars will be drawn side-by-side at
    position x=1.
    Other two bars will be drawn side by side at position x=2.
    See also the description of attribute "cluster" for bar_plot.T.
    """),
    "width": (UnitType, 5, """Width of each box. The unit is in points.
@cindex width, bar chart
@cindex size, bar chart
"""),
    "cluster_sep": (UnitType, 0, """The separation between
    clustered boxes. The unit is points."""),
    "stack_on": (AnyType, None,
                 "The value must be either None or bar_plot.T. If not None, bars of this plot are stacked on top of another bar plot."),
    }

class T(chart_object.T):
    __doc__ = bar_plot_doc.doc
    keys = _keys
    def check_integrity(self):
        self.type_check()
    def get_value(self, bval):
        for pair in self.data:
            if pair[self.bcol] == bval:
                return pair[self.hcol]
	raise ValueError, str(bval) + ": can't find the xval"

    def __get_data_range(self, col):
        gmin = 99999999
        gmax = -99999999
        for item in self.data:
            seq = item[col]
            if seq[0] < gmin: gmin = seq[0]
            max = 0
            for v in seq:
                max += v
            if max > gmax: gmax = max
        return (gmin, gmax)
    
    def get_data_range(self, which):
        if self.direction == 'vertical':
            if which == 'X':
                return pychart_util.get_data_range(self.data, self.bcol)
            else:
                return self.__get_data_range(self.hcol)
        else:
            assert self.direction == 'horizontal'
            if which == 'Y':
                return pychart_util.get_data_range(self.data, self.bcol)
            else:
                return self.__get_data_range(self.hcol)

    def get_style(self, nth):
        line_style = self.line_styles[nth % len(self.line_styles)]
        fill_style = self.fill_styles[nth % len(self.fill_styles)]
        return (line_style, fill_style)
    
    def draw_vertical(self, ar, can):
        for pair in self.data:
            xval = pair[self.bcol]
            yvals = pychart_util.get_sample_val(pair, self.hcol)
            
            if None in (xval, yvals): continue

            ybot = 0
            
            totalWidth = (self.width+self.cluster_sep) * self.cluster[1] - self.cluster_sep
            firstX = ar.x_pos(xval) - totalWidth/2.0
            thisX = firstX + (self.width+self.cluster_sep) * self.cluster[0] - self.cluster_sep

            cury = yvals[0]
            n = 0
            
            for yval in yvals[1:]:
                (line_style, fill_style) = self.get_style(n)
                can.rectangle(line_style, fill_style,
                              thisX, ar.y_pos(cury), thisX+self.width, 
                              ar.y_pos(cury + yval))
                cury += yval
                n += 1
                
                if self.data_label_format:
                    can.show(thisX + self.width/2.0 + self.data_label_offset[0],
                             ar.y_pos(cury) + self.data_label_offset[1],
                             "/hC" + pychart_util.apply_format(self.data_label_format, (pair[self.bcol], pair[self.hcol]), 1))
	    
    def draw_horizontal(self, ar, can):
        for pair in self.data:
            yval = pair[self.bcol]
            xvals = pychart_util.get_sample_val(pair, self.hcol)

            if None in (xvals, yval): continue

            totalWidth = (self.width+self.cluster_sep) * self.cluster[1] - self.cluster_sep
            firstY = ar.y_pos(yval) - totalWidth/2.0
            thisY = firstY + (self.width+self.cluster_sep) * self.cluster[0] - self.cluster_sep

            curx = xvals[0]
            n = 0
            for xval in xvals[1:]:
                line_style, fill_style = self.get_style(n)
                can.rectangle(line_style, fill_style,
                              ar.x_pos(curx), thisY,
                              ar.x_pos(xval), thisY+self.width)
                curx = xval
                n += 1
                
    def get_legend_entry(self):
        if self.label:
            return legend.Entry(line_style=self.line_styles[0],
                                fill_style=self.fill_styles[0],
                                label=self.label)
        return None
        
    def draw(self, ar, can):
	self.type_check()
        can.clip(ar.loc[0], ar.loc[1],
                 ar.loc[0] + ar.size[0], ar.loc[1] + ar.size[1])
            
        if self.direction == "vertical":
            self.draw_vertical(ar, can)
        else:
            self.draw_horizontal(ar, can)

        can.endclip()

def init():
    global fill_styles
    fill_styles = fill_style.standards.iterate()
    
theme.add_reinitialization_hook(init)

