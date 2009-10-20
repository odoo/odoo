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
import pychart_types
import types

def _check_attr_types(obj, keys):
    for attr in obj.__dict__.keys():
        if not keys.has_key(attr):
            raise Exception, "%s: unknown attribute '%s'" % (obj, attr)
        
        typeval, default_value, docstring = keys[attr][0:3]
        val = getattr(obj, attr)
        if val == None or typeval == pychart_types.AnyType:
            pass
        elif isinstance(typeval, types.FunctionType):
            # user-defined check procedure
            error = apply(typeval, (val,))
            if error != None:
                raise Exception, "%s: %s for attribute '%s', but got '%s'" % (obj, error, attr, val)
        elif 1:
            try:
                if isinstance(val, typeval):
                    pass
            except:
                raise Exception, "%s: Expecting type %s, but got %s (attr=%s, %s)"  % (obj, typeval, val, attr, keys[attr])

        else:
            raise Exception, "%s: attribute '%s' expects type %s but found %s" % (obj, attr, typeval, val)

def set_defaults(cls, **dict):
    validAttrs = getattr(cls, "keys")
    for attr, val in dict.items():
        if not validAttrs.has_key(attr):
            raise Exception, "%s: unknown attribute %s." % (cls, attr)
        tuple = list(validAttrs[attr])
        # 0 : type
        # 1: defaultValue
        # 2: document
        # 3: defaultValue document (optional)
        tuple[1] = val
        validAttrs[attr] = tuple
        
class T(object):
    def init(self, args):
        keys = self.keys
        for attr, tuple in keys.items():
            defaultVal = tuple[1]
            if isinstance(defaultVal, types.FunctionType):
                # if the value is procedure, use the result of the proc call
                # as the default value
                defaultVal = apply(defaultVal, ())
            setattr(self, attr, defaultVal)
            
        for key, val in args.items():
            setattr(self, key, val)
        _check_attr_types(self, keys)
        
    def __init__(self, **args):
        self.init(args)

    def type_check(self):
        _check_attr_types(self, self.keys)
