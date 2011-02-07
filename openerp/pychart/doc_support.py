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
import string
import sys
import re
import os.path
from pychart import *
from types import *
from pychart.pychart_types import *

oldstdout = sys.stdout
if os.path.exists("/dev/null"):
    sys.stdout = open("/dev/null", "w")

modules = {}
values = []

sys.stdout = oldstdout
g = globals()
for mod in g.keys():
    val = g[mod]
    if type(val) == ModuleType:
        dic = {}
        for name in val.__dict__.keys():
            v = val.__dict__[name]
            if name[0] != '_':
                values.append((v, mod + "." + name))
            if type(v) == type and issubclass(v, chart_object.T):
                dic[name] = v
        modules[mod] = dic

def stringify_type(t):
    s = str(t)
    if t == AnyType:
        return "any"
    if t == ShadowType:
        return "(xoff,yoff,fill)"
    elif re.search("NumType", s):    
        return "number"
    elif re.search("UnitType", s):    
        return "length in points (\\\\xref{unit})"
    elif re.search("CoordType", s):
        return "(x,y)"
    elif re.search("CoordSystemType", s):
        return "['linear'|'log'|'category']"
    elif re.search("CoordOrNoneType", s):
        return "(x,y) or None"
    elif re.search("TextAlignType", s):
        return "['R'|'L'|'C'|None]"
    elif re.search("FormatType", s):
        return "printf format string"
    elif re.search("IntervalType", s):
        return "Number or function"

    mo = re.match("<type '([^']+)'>", s)
    if mo:
        return mo.group(1)
    mo = re.match("<class 'pychart\.([^']+)'>", s)
    if mo:
        return mo.group(1)
    mo = re.match("<class '([^']+)'>", s)
    if mo:
        return mo.group(1)
    mo = re.match("pychart\\.(.*)", s)
    if mo:
        return mo.group(1)
    return s

def stringify_value(val):
    t = type(val)
    if t == StringType:
        return '"' + val + '"'
    if t == bool:
        if val: return "True"
        else: return "False"
        
    if t in (IntType, LongType, FloatType):
        return str(val)
    if val == None:
        return "None"
    if type(val) == ListType:
        return map(stringify_value, val)
    for pair in values:
        if pair[0] == val:
            return pair[1]
    return str(val)

def break_string(name):
    max_len = 10
    if len(name) < max_len:
        return name
    
    name = re.sub("(\\d\\d)([^\\d])", "\\1-\n\\2", name) 
    name = re.sub("black(.)", "black-\n\\1", name)

    elems = string.split(name, "\n")
    while 1:
        broken = 0
        for i in range(len(elems)):
            elem = elems[i]
            if len(elem) < max_len:
                continue
            broken = 1
            elem1 = elem[0:len(elem)/2]
            elem2 = elem[len(elem)/2:]
            elems[i:i+1] = [elem1, elem2]
            break
        if not broken:
            break
    name = "\n".join(elems)
    return name
