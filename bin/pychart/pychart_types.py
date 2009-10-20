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
import pychart_util
import types
AnyType = 9998

def CoordType(val):
    if type(val) != types.TupleType and type(val) != types.ListType:
        return (" not a valid coordinate.")
    if len(val) != 2:
        return "Coordinate must be a pair of numbers.\n"
    if val[0] != None:
        error = NumType(val[0])
        if error: return error
    if val[1] != None:    
        error = NumType(val[1])
        if error: return error
    return None    

def IntervalType(val):
    if type(val) in (types.IntType, types.LongType,
                     types.FloatType, types.FunctionType):
	return None
    return "Expecting a number or a function"

def CoordOrNoneType(val):
    if type(val) not in (types.TupleType, types.ListType):
        return "Expecting a tuple or a list."
    if len(val) != 2:
        return "Coordinate must be a pair of numbers.\n"
    for v in val:
        if v != None and NumType(val[0]) != None:
            return "Expecting a pair of numbers"
    return None    
    
def NumType(val):
    if type(val) in (types.IntType, types.LongType, types.FloatType):
        return None
    else:
        return "Expecting a number, found \"" + str(val) + "\""

def UnitType(val):
    if type(val) in (types.IntType, types.LongType, types.FloatType):
        return None
    else:
        return "Expecting a unit, found \"" + str(val) + "\""
    
def ShadowType(val):
    if type(val) not in (types.TupleType, types.ListType):
	return "Expecting tuple or list."
    if len(val) != 3:
	return "Expecting (xoff, yoff, fill)."
    return None

def FormatType(val):
    if type(val) in (types.StringType, types.FunctionType):
        return None
    return "Format must be a string or a function"

