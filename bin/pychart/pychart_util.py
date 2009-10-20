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
import sys
import math
import types
import traceback
from types import *

def inch_to_point(inch):
    return inch * 72.0
def point_to_inch(pt):
    return float(pt) / 72.0

def rotate(x, y, degree):
    """Rotate a coordinate around point (0,0).
    - x and y specify the coordinate.
    - degree is a number from 0 to 360.
    Returns a new coordinate.
    """
    radian = float(degree) * 2 * math.pi / 360.0
    newx = math.cos(radian) * x - math.sin(radian) * y
    newy = math.sin(radian) * x + math.cos(radian) * y
    return (newx, newy)

debug_level = 1

def warn(*strs):
    for s in strs:
        sys.stderr.write(str(s))
        sys.stderr.write(" ")
    sys.stderr.write("\n")

def info(*strs):
    if debug_level < 100:
	return
    for s in strs:
        sys.stderr.write(str(s))
    sys.stderr.write("\n")

def get_sample_val(l, col):
    if len(l) <= col:
        return None
    return l[col]

def get_data_list(data, col):
    # data = [ elem[col] for elem in data if elem[col] != None ]
    r = []
    for item in data:
        val = get_sample_val(item, col)
        if val != None:
            r.append(val)
    return r        
    
def get_data_range(data, col):
    data = get_data_list(data, col)
    for item in data:
        if type(item) not in (types.IntType, types.LongType, types.FloatType):
            raise TypeError, "Non-number passed to data: %s" % (data)
    return (min(data), max(data))

def round_down(val, bound):
    return int(val/float(bound)) * bound

def round_up(val, bound):
    return (int((val-1)/float(bound))+1) * bound

    
#
# Attribute type checking stuff
#

def new_list():
    return []

def union_dict(dict1, dict2):
    dict = dict1.copy()
    dict.update(dict2)
    return dict

def TextVAlignType(val):
    if val in ('T', 'B', 'M', None):
        return None
    return "Text vertical alignment must be one of T(op), B(ottom), or M(iddle).\n"

def TextAlignType(val):
    if val in ('C', 'R', 'L', None):
        return None
    return "Text horizontal alignment must be one of C(enter), R(ight), or L(eft)."

def apply_format(format, val, defaultidx):
    if format == None:
        return None
    elif type(format) == StringType:
        return format % val[defaultidx]
    else:
        return apply(format, val)

    
data_desc = "Specifies the data points. <<chart_data>>"
label_desc = "The label to be displayed in the legend. <<legend>>, <<font>>"
xcol_desc = """The column, within attribute "data", from which the X values of sample points are extracted. <<chart_data>>"""
ycol_desc = """The column, within attribute "data", from which the Y values of sample points are extracted. <<chart_data>>"""
tick_mark_desc = "Tick marks to be displayed at each sample point. <<tick_mark>>"
line_desc="The style of the line. "

def interval_desc(w):
    return "When the value is a number, it specifies the interval at which %s are drawn. Otherwise, the value must be a function that takes no argument and returns the list of numbers. The return value specifies the X or Y points at which %s are drawn." % (w,w)

shadow_desc = """The value is either None or a tuple. When non-None,
a drop-shadow is drawn beneath the object. X-off, and y-off specifies the
offset of the shadow relative to the object, and fill specifies the
style of the shadow (@pxref{module-fill-style})."""

string_desc = """The appearance of the string produced here can be
controlled using escape sequences. <<font>>"""

#
#

class symbol_lookup_table:
    def __init__(self, dict, objs):
        self.names = {}
        for name, val in dict.items():
            for obj in objs.list():
                if val == obj:
                    self.names[val] = name
                    break
    def lookup(self, obj):
        if self.names.has_key(obj):
            return self.names[obj]
        return None
