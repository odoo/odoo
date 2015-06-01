# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import reportlab
import reportlab.lib.units

units = [
    (re.compile('^(-?[0-9\.]+)\s*in$'), reportlab.lib.units.inch),
    (re.compile('^(-?[0-9\.]+)\s*cm$'), reportlab.lib.units.cm),
    (re.compile('^(-?[0-9\.]+)\s*mm$'), reportlab.lib.units.mm),
    (re.compile('^(-?[0-9\.]+)\s*px$'), 0.7),
    (re.compile('^(-?[0-9\.]+)\s*$'), 1)
]

def unit_get(size):
    global units
    for unit in units:
        res = unit[0].search(size, 0)
        if res:
            return int(unit[1]*float(res.group(1))*1.3)
    return False

def tuple_int_get(node, attr_name, default=None):
    if not node.get(attr_name):
        return default
    res = [int(x) for x in node.get(attr_name).split(',')]
    return res

def bool_get(value):
    return (str(value)=="1") or (value.lower()=='yes')

def attr_get(node, attrs, dict=None):
    if dict is None:
        dict = {}
    res = {}
    for name in attrs:
        if node.get(name):
            res[name] =  unit_get(node.get(name))
    for key in dict:
        if node.get(key):
            if dict[key]=='str':
                res[key] = str(node.get(key))
            elif dict[key]=='bool':
                res[key] = bool_get(node.get(key))
            elif dict[key]=='int':
                res[key] = int(node.get(key))
    return res
