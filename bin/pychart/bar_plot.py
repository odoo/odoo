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
import error_bar
import bar_plot_doc
import theme
from types import *
from pychart_types import *

fill_styles = None

_keys = {
    "direction" : (StringType, "vertical",
                   """The direction the growth of the bars. The value is either 'horizontal'
                   or 'vertical'."""),
    "data" : (AnyType, None, pychart_util.data_desc),
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
              the set of boxes drawn by this chart. See the
              below example:
              
@example
              d = [[5,10], [7,22], [8,25]]
              p = bar_plot.T(data = d, bcol = 1, hcol = 2)
@end example

              Here, three bars will be drawn. The X values of the bars
              will be 5, 7, and 8. The Y values of the bars will be
              10, 22, and 25, respectively. (In practice, because
              the values of bcol and hcol defaults to 1 and 2, you can
              write the above example just as "p = bar_plot.T(data = d)".
              """),
    "hcol": (IntType, 1,
             """The column from which the height of each bar is extracted.
             See also the description of the 'bcol' attribute."""),
    "line_style": (line_style.T, line_style.default,
                   "The style of the outer frame of each box."),
    "fill_style": (fill_style.T, lambda: fill_styles.next(),
                   "Defines the fill style of each box.",
                   "The style is picked from standard styles round-robin."),
    "legend_line_style": (line_style.T, None,
                          """The line style used to draw a legend entry. Usually, the value is None, meaning that the value of "line_style" attribute is used."""),
    "legend_fill_style": (fill_style.T, None,
                   """The fill style used to draw a legend entry. Usually, the value is None, meaning that the value of "fill_style" attribute is used."""),
                          
    "cluster": (TupleType, (0, 1), """This attribute is used to
    cluster multiple bar plots side by side in a single chart.
    The value should be a tuple of two integers. The second value should be equal to the total number of bar plots in the chart. The first value should be the relative position of this chart; 0 places this chart the leftmost, and N-1
    (where N is the 2nd value of this attribute) places this chart the rightmost. Consider the below example:

@example
    a = area.T(...)
    p1 = bar_plot.T(data = [[1,20][2,30]], cluster=(0,2))
    p2 = bar_plot.T(data = [[1,25],[2,10]], cluster=(1,2))
    a.add_plot(p1, p2)
    a.draw()
@end example

    In this example, one group of bars will be drawn side-by-side at
    position x=1, one with height 20, the other with height 25. The
    other two bars will be drawn side by side at position x=2, one
    with height 30 and the other with height 10.
    """),
    "width": (UnitType, 5, """Width of each box. 
@cindex width, bar chart
@cindex size, bar chart
"""),
    "cluster_sep": (UnitType, 0, """The separation between
    clustered boxes."""),
    "stack_on": (AnyType, None,
                 "The value must be either None or bar_plot.T. If not None, bars of this plot are stacked on top of another bar plot."),
    "error_minus_col": (IntType, -1,
                  """Specifies the column from which the depth of the errorbar is extracted.  This attribute is meaningful only when
                  error_bar != None.
                  """),
    "qerror_minus_col":  (IntType, -1,
                  """The depth of the "quartile" errorbar is extracted from 
                  this column in data. This attribute is meaningful only
                  when error_bar != None. """),
    "error_plus_col": (IntType, -1,
                  """The depth of the errorbar is extracted from 
                  this column in data. This attribute is meaningful only
                  when error_bar != None."""),
    "qerror_plus_col":  (IntType, -1, 
                  """The depth of the "quartile" errorbar is extracted from 
                  this column in data. This attribute is meaningful only
                  when error_bar != None."""),
    "error_bar": (error_bar.T, None,
                  "Specifies the style of the error bar. <<error_bar>>"),
    "_abs_data" : (ListType, None,
                   "Used only internally."),
    }

def find_bar_plot(ar, nth):
    "Find the NTH barplot of the cluster in area AR."
    for plot in ar.plots:
        if isinstance(plot, T) and plot.cluster[0] == nth:
            return plot
    raise Exception, "The %dth bar plot in the cluster not found." % nth   

class T(chart_object.T):
    __doc__ = bar_plot_doc.doc
    keys = _keys
    def check_integrity(self):
        self.type_check()
        self.compute_abs_data()
    def compute_abs_data(self):
        if self._abs_data != None:
            return
        
        if self.stack_on == None:
            self._abs_data = self.data
        else:
            n = []
            for pair in self.data:
                self.stack_on.compute_abs_data()
                newpair = list(pair[:])
                newpair[self.hcol] = self.stack_on.get_value(newpair[self.bcol]) + pair[self.hcol]
                n.append(newpair)
            self._abs_data = n
            
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    def get_value(self, bval):
        for pair in self._abs_data:
            if pair[self.bcol] == bval:
                return pair[self.hcol]
	raise ValueError, str(bval) + ": can't find the xval"

    def get_data_range(self, which):
        if self.direction == 'vertical':
            if which == 'X':
                return pychart_util.get_data_range(self._abs_data, self.bcol)
            else:
                return pychart_util.get_data_range(self._abs_data, self.hcol)
        else:
            assert self.direction == 'horizontal'
            if which == 'Y':
                return pychart_util.get_data_range(self._abs_data, self.bcol)
            else:
                return pychart_util.get_data_range(self._abs_data, self.hcol)

    def get_bar_width(self, ar, nth):
        off = 0
        for i in range(0, nth):
            plot = find_bar_plot(ar, i)
            off += plot.width + plot.cluster_sep
        return off
    
    def draw_vertical(self, ar, can):
        for pair in self.data:
            xval = pair[self.bcol]
            yval = pychart_util.get_sample_val(pair, self.hcol)
            
            if None in (xval, yval): continue

            ybot = 0
            if self.stack_on:
                ybot = self.stack_on.get_value(xval)
                yval += ybot

            totalWidth = self.get_bar_width(ar, self.cluster[1])
            firstX = ar.x_pos(xval) - totalWidth/2.0
            thisX = firstX + self.get_bar_width(ar, self.cluster[0])

            can.rectangle(self.line_style, self.fill_style,
                             thisX, ar.y_pos(ybot), thisX+self.width, 
                             ar.y_pos(yval))

            if self.error_bar:
                plus = pair[self.error_minus_col or self.error_plus_col]
                minus = pair[self.error_plus_col or self.error_minus_col]
                qplus = 0
                qminus = 0
                if self.qerror_minus_col or self.qerror_plus_col:
                    qplus = pair[self.qerror_minus_col or self.qerror_plus_col]
                    qminus = pair[self.qerror_plus_col or self.qerror_minus_col]
                if None not in (plus, minus, qplus, qminus): 
                    self.error_bar.draw(can, (thisX+self.width/2.0, ar.y_pos(yval)),
                                        ar.y_pos(yval - minus),
                                        ar.y_pos(yval + plus),
                                        ar.y_pos(yval - qminus),
                                        ar.y_pos(yval + qplus))
                    
            if self.data_label_format:
                can.show(thisX + self.width/2.0 + self.data_label_offset[0],
                            ar.y_pos(yval) + self.data_label_offset[1],
                            "/hC" + pychart_util.apply_format(self.data_label_format, (pair[self.bcol], pair[self.hcol]), 1))
	    
    def draw_horizontal(self, ar, can):
        for pair in self.data:
            yval = pair[self.bcol]
            xval = pychart_util.get_sample_val(pair, self.hcol)

            if None in (xval, yval): continue

            xbot = 0
            if self.stack_on:
                xbot = self.stack_on.get_value(yval)
                xval += xbot
            totalWidth = self.get_bar_width(ar, self.cluster[1])
            firstY = ar.y_pos(yval) - totalWidth/2.0
            thisY = firstY + self.get_bar_width(ar, self.cluster[0])
            
            can.rectangle(self.line_style, self.fill_style,
                          ar.x_pos(xbot), thisY,
                          ar.x_pos(xval), thisY+self.width)

            if self.data_label_format:
                can.show(ar.x_pos(xval) + self.data_label_offset[0],
		            thisY + self.width/2.0 + self.data_label_offset[1],
                            "/vM/hL" + pychart_util.apply_format(self.data_label_format, (pair[self.bcol], pair[self.hcol]), 1))

    def get_legend_entry(self):
        if self.label:
            return legend.Entry(line_style=(self.legend_line_style or self.line_style),
                                fill_style=(self.legend_fill_style or self.fill_style),
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

