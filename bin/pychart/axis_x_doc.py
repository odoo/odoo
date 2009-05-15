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
doc="""Attributes supported by this class are:
tic_label_offset(type:(x,y)):
    The location where the tick labels is drawn. Relative to the 
    tip of the tick mark. 
    default value=(0, 0).
format(type:printf format string):
    The format string for tick labels. It can be a `printf' style 
    format string, or a single-parameter function that returns a 
    string. See also font. 
    default value=%s.
minor_tic_len(type:number):
    The length of minor tick marks. 
    default value=3.
label_offset(type:(x,y) or None):
    The location where the axis label is drawn. Relative to the 
    left-bottom corner of the axis. 
    default value=(None, None).
grid_interval(type:Number or function):
    When the value is a number, it specifies the interval with which 
    grid lines are drawn. Otherwise, the value must be a function. 
    It must take no argument and return the list of numbers, which 
    specifies the X or Y points where grid lines are drawn. 
    default value=None.
label(type:str):
    The description of the axis. See also font. 
    default value=axis label.
grid_style(type:line_style.T):
    The style of grid lines. 
    default value=None.
tic_interval(type:Number or function):
    When the value is a number, it specifies the interval with which 
    tick marks are drawn. Otherwise, the value must be a function. 
    It must take no argument and return the list of numbers, which 
    specifies the X or Y points where tick marks are drawn. 
    default value=None.
line_style(type:line_style.T):
    The style of tick lines. 
    default value=default.
tic_len(type:number):
    The length of tick lines 
    default value=6.
minor_tic_interval(type:Number or function):
    When the value is a number, it specifies the interval with which 
    minor tick marks are drawn. Otherwise, the value must be a function. 
    It must take no argument and return the list of numbers, which 
    specifies the X or Y points where minor tick marks are drawn. 
    default value=None.
first_tic_value(type:number):
    The location of the first tick mark. Defaults to the x_range[0] 
    (or y_range[0]) of the area. 
    default value=None.
"""