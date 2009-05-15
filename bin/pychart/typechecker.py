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
import types
class IntervalTypeClass:
    def typeCheck(self, val):
        if type(val) in (types.IntType, types.LongType, types.FloatType,
                         types.FunctionType):
            return None
        return "Expecting a number or a function, but received '%s'", val
    def typeDescription(self):
        return "A number or function"
    def varDescription(self, name):
        return "A number or function"

IntervalType = IntervalTypeClass()

