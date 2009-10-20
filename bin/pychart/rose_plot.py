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
import canvas
import fill_style
import line_style
import pychart_util
import chart_object
import legend
import font
import color
from pychart_types import *

class T(chart_object.T):
    """Plots sector diagram which can be superimposed on one another.
    Sector diagrams are also known as wind roses"""
    keys = {
        "start_angle" : (NumType, 90, ""), # top of chart (north)
	"center" : (CoordType, None, ""),
	"base_radius" : (NumType, None, ""),
	"line_style" : (line_style.T, line_style.T(color=color.black, width=0.3), ""),
        "fill_styles" : (list, fill_style.standards.list()[:],
                         """The fill style of each item. The length of the
                         list should be equal to the length of the data.
                         """),
	"sector_centred":(int, 1,
			  """Bool indicating whether the sectors should be centred on each sector_width(e.g. on 0)"""),
	"dir_offset":  (UnitType, None,
			"""The distance between the directions and the outermost circle. Defaults fine for most cases"""),
        "data" : (AnyType, None, pychart_util.data_desc),
        "label_col" : (int, 0,
                       """The column, within "data", from which the labels of items are retrieved."""),
        "data_col": (int, 1,
                     """ The column, within "data", from which the data values are retrieved."""),
        "dir_line_style": (line_style.T, None, ""),
        "dir_fill_style": (fill_style.T, fill_style.default, ""),
	"shadow": (ShadowType, None, pychart_util.shadow_desc),
	"sector_width": (int, None, ""), # automatically generated
        }

    def __init__(self, colour=True, **args):
        chart_object.T.init(self, args)
	if colour:
  	    # the theme.color flag does not seem to affect the fill_style.standards,
	    #besides, I want the first two colors to resemble those of gnuplot's postscript terminal
  	    self.fill_styles = [fill_style.Plain(bgcolor=color.red),
				fill_style.Plain(bgcolor=color.green),
				fill_style.Plain(bgcolor=color.blue),
				fill_style.Plain(bgcolor=color.magenta)]

    def check_integrity(self):
        nSectors = len(self.data[0][self.data_col])
        if (360%nSectors != 0):
            raise Exception('Length of dataset ' + str(nSectors) + ' not a divisor of 360 degrees!')
        for dataset in self.data:
            length = len(dataset[self.data_col])
            if length != nSectors:
                raise Exception('Lengths of datasets given is different!')
            for val in dataset[self.data_col]:
                if (val < 0) | (val > 1):
                    raise Exception('Data value ' + str(val) + ' not between 0 and 1!')
        self.sector_width = 360/nSectors
        self.type_check()

    def get_data_range(self, which):
        return (0, 1)

    def get_legend_entry(self):
        legends = []
        i = 0
        for dataset in self.data:
            fill = self.fill_styles[i]
            i = (i + 1) % len(self.fill_styles)
            legends.append(legend.Entry(line_style=self.line_style,
                                    fill_style=fill,
                                    label=dataset[self.label_col]))
        return legends

    def draw(self, ar, can):
        center = self.center
        if not center:
            center = (ar.loc[0] + ar.size[0]/2.0,
                            ar.loc[1] + ar.size[1]/2.0)
        base_radius = self.base_radius # the maximum radius of a wedge
        if not base_radius:
            base_radius = min(ar.size[0]/2.0, ar.size[1]/2.0) #* 0.8

        sector_decrement = 1./(len(self.data)*2) * self.sector_width # each following sector diagram will have its sector width decremented by half this amount (in degrees)
        i = 0
        for dataset in self.data:
            cur_angle = self.start_angle
            if self.sector_centred:
                cur_angle -= self.sector_width/2.
            fill = self.fill_styles[i]
            x_center = center[0]
            y_center = center[1]

            if not i: # draw directions around sector diagram once off
                dir_offset = base_radius + (self.dir_offset or base_radius * 0.04)
                directions = ['N', 'E', 'S', 'W']
                angle = self.start_angle

                can.ellipsis(line_style.T(color=color.black, width=0.3, dash=line_style.dash1), None,
                             x_center, y_center, base_radius, 1,
                             0, 360) #

                for d in directions:
                    x_label, y_label = pychart_util.rotate(dir_offset, 0, angle) # coords for bottom left corner of box
                    tw = font.text_width(d)
                    half = 1/3. # normal arithmetic does not seem to apply to these text_box objects...
                    if (angle == 0): # east
                        y_label -= font.text_height(d)[0]*half # move down half
                    elif (angle == -180): # west
                        y_label -= font.text_height(d)[0]*half # move down half
                        x_label -= font.text_width(d) # move left full
                    elif (angle == 90): # north
                        x_label -= font.text_height(d)[0]*half # move left half
                    elif (angle == -90): # south
                        y_label -= font.text_height(d)[0]*.8 # move down (couldn't figure out how to set this dynamically so I fudged...)
                        x_label -= font.text_height(d)[0]*half # move left half
                    canvas.show(x_label + x_center, y_label + y_center, d)
                    angle -= 360/len(directions)

            for val in dataset[self.data_col]: # now draw the sectors
                radius = base_radius*val # scale the radius
                start = cur_angle-self.sector_width+i*sector_decrement
                stop = cur_angle-i*sector_decrement # these may seem confusing, but remember that we need to go counterclockwise

                can.ellipsis(self.line_style, fill,
                             x_center, y_center, radius, 1, start, stop, self.shadow) 
                cur_angle = (cur_angle - self.sector_width) % 360 # we want to go in anticlockwise direction (North, West, South, etc. as in meteorology)
            i = (i + 1) % len(self.fill_styles)

