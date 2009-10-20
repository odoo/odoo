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
import coord
import line_style
import legend
import axis
import pychart_util
import chart_object
import fill_style
import canvas
import area_doc
import linear_coord
import category_coord
import theme
from pychart_types import *
from types import *

_dummy_legend = legend.T()

def range_doc(t):
    u = t.upper()
    
    return """Specifies the range of %s values that are displayed in the
    chart. IF the value is None, both the values are computed
    automatically from the samples.  Otherwise, the value must be a
    tuple of format (MIN, MAX). MIN and MAX must be either None or a
    number. If None, the value is computed automatically from the
    samples. For example, if %s_range = (None,5), then the minimum %s
    value is computed automatically, but the maximum %s value is fixed
    at 5.""" % (u, t, u, u)
    
_keys = {
    "loc" : (CoordType, (0,0),
             """The location of the bottom-left corner of the chart.
@cindex chart location
@cindex location, chart
"""),
    "size" : (CoordType, (120,110),
              """The size of the chart-drawing area, excluding axis labels,
              legends, tick marks, etc.
@cindex chart size
@cindex size, chart              
              """),
    "bg_style": (fill_style.T, None, "Background fill-pattern."),
    "border_line_style": (line_style.T, None, "Line style of the outer frame of the chart."),
    "x_coord":
    (coord.T, linear_coord.T(),
     """Set the X coordinate system.""",
     """A linear coordinate system."""),
    "y_coord": (coord.T, linear_coord.T(),
                "Set the Y coordinate system.",
                """A linear coordinate system."""),
    "x_range": (CoordType, None, range_doc("x")),
    "y_range": (CoordType, None, range_doc("y")),
    "x_axis": (axis.X, None, "The X axis. <<axis>>."),
    "x_axis2": (axis.X, None, """The second X axis. This axis should be non-None either when you want to display plots with two distinct domains or when
    you just want to display two axes at the top and bottom of the chart.
    <<axis>>"""),
    "y_axis": (axis.Y, None, "The Y axis. <<axis>>."),
    "y_axis2": (axis.Y, None,
                """The second Y axis. This axis should be non-None either when you want to display plots with two distinct ranges or when
                you just want to display two axes at the left and right of the chart. <<axis>>"""),
    "x_grid_style" : (line_style.T, None,
                      """The style of horizontal grid lines.
@cindex grid lines"""),
    "y_grid_style" : (line_style.T, line_style.gray70_dash3,
                      "The style of vertical grid lines."),
    "x_grid_interval": (IntervalType, None,
                        """The horizontal grid-line interval.
                        A numeric value
                        specifies the interval at which
                        lines are drawn. If value is a function, it
                        takes two arguments, (MIN, MAX), that tells
                        the minimum and maximum values found in the
                        sample data. The function should return a list
                        of values at which lines are drawn."""),
    "y_grid_interval": (IntervalType, None,
                        "The vertical grid-line interval. See also x_grid_interval"),
    "x_grid_over_plot": (IntType, False,
                      "If True, grid lines are drawn over plots. Otherwise, plots are drawn over grid lines."),
    "y_grid_over_plot": (IntType, False, "See x_grid_over_plot."),
    "plots": (ListType, pychart_util.new_list,
               """Used only internally by pychart."""),
    "legend": (legend.T, _dummy_legend, "The legend of the chart.",
               """a legend is by default displayed
               in the right-center of the chart."""),
    }


class T(chart_object.T):
    keys = _keys
    __doc__ = area_doc.doc
##AUTOMATICALLY GENERATED

##END AUTOMATICALLY GENERATED
    def x_pos(self, xval):
        "Return the x position (on the canvas) corresponding to XVAL."
        off = self.x_coord.get_canvas_pos(self.size[0], xval,
                                          self.x_range[0], self.x_range[1])
        return self.loc[0] + off
    
    def y_pos(self, yval):
        "Return the y position (on the canvas) corresponding to YVAL."
        off = self.y_coord.get_canvas_pos(self.size[1], yval,
                                          self.y_range[0], self.y_range[1])
        return self.loc[1] + off

    def x_tic_points(self, interval):
        "Return the list of X values for which tick marks and grid lines are drawn."
        if type(interval) == FunctionType:
            return apply(interval, self.x_range)

        return self.x_coord.get_tics(self.x_range[0], self.x_range[1], interval)
    def y_tic_points(self, interval):
        "Return the list of Y values for which tick marks and grid lines are drawn."
        if type(interval) == FunctionType:
            return apply(interval, self.y_range)

        return self.y_coord.get_tics(self.y_range[0], self.y_range[1], interval)
    def __draw_x_grid_and_axis(self, can):
        if self.x_grid_style:
            for i in self.x_tic_points(self.x_grid_interval):
                x = self.x_pos(i)
                if x > self.loc[0]:
                    can.line(self.x_grid_style,
                             x, self.loc[1], x, self.loc[1]+self.size[1])
        if self.x_axis:
            self.x_axis.draw(self, can)
        if self.x_axis2:
            self.x_axis2.draw(self, can)
    def __draw_y_grid_and_axis(self, can):
        if self.y_grid_style:
            for i in self.y_tic_points(self.y_grid_interval):
                y = self.y_pos(i)
                if y > self.loc[1]:
                    can.line(self.y_grid_style,
                             self.loc[0], y,
                             self.loc[0]+self.size[0], y)
        if self.y_axis:
            self.y_axis.draw(self, can)
        if self.y_axis2:
            self.y_axis2.draw(self, can)

    def __get_data_range(self, r, which, coord, interval):
        if isinstance(coord, category_coord.T):
            # This info is unused for the category coord type.
            # So I just return a random value.
            return ((0,0), 1)

        r = r or (None, None)
        
        if len(self.plots) == 0:
            raise ValueError, "No chart to draw, and no data range specified.\n";
        dmin, dmax = 999999, -999999
 
        for plot in self.plots:
            this_min, this_max = plot.get_data_range(which)
            dmin = min(this_min, dmin)
            dmax = max(this_max, dmax)

        if interval and type(interval) == FunctionType:
            tics = apply(interval, (dmin, dmax))
            dmin = tics[0]
            dmax = tics[len(tics)-1]
        else:
            dmin, dmax, interval = coord.get_min_max(dmin, dmax, interval)

        if r[0] != None:
            dmin = r[0]
        if r[1] != None:
            dmax = r[1]
        return ((dmin, dmax), interval)
    def draw(self, can = None):
        "Draw the charts."

        if can == None:
            can = canvas.default_canvas()
            
        self.type_check()
        for plot in self.plots:
            plot.check_integrity()
            
        self.x_range, self.x_grid_interval = \
                      self.__get_data_range(self.x_range, 'X',
                                            self.x_coord,
                                            self.x_grid_interval)
            
        self.y_range, self.y_grid_interval = \
                      self.__get_data_range(self.y_range, 'Y',
                                            self.y_coord,
                                            self.y_grid_interval)
        
        can.rectangle(self.border_line_style, self.bg_style,
                      self.loc[0], self.loc[1],
                      self.loc[0] + self.size[0], self.loc[1] + self.size[1])

        if not self.x_grid_over_plot:
            self.__draw_x_grid_and_axis(can)

        if not self.y_grid_over_plot:
            self.__draw_y_grid_and_axis(can)

        clipbox = theme.adjust_bounding_box([self.loc[0], self.loc[1],
                                             self.loc[0] + self.size[0],
                                             self.loc[1] + self.size[1]])

        can.clip(clipbox[0], clipbox[1],
                 clipbox[2], clipbox[3])

        for plot in self.plots:
            plot.draw(self, can)
            
        can.endclip()
            
        if self.x_grid_over_plot:
            self.__draw_x_grid_and_axis(can)
        if self.y_grid_over_plot:
            self.__draw_y_grid_and_axis(can)

        if self.legend == _dummy_legend:
            self.legend = legend.T()
            
        if self.legend:
            legends = []
            for plot in self.plots:
                entry = plot.get_legend_entry()
                if entry == None:
                    pass
                elif type(entry) != ListType:
                    legends.append(entry)
                else:
                    for e in entry:
                        legends.append(e)
            self.legend.draw(self, legends, can)

    def add_plot(self, *plots):
        "Add PLOTS... to the area."
        self.plots.extend(plots)
