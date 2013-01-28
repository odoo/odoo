# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

from reportlab.lib import colors
import re

allcols = colors.getAllNamedColors()

regex_t = re.compile('\(([0-9\.]*),([0-9\.]*),([0-9\.]*)\)')
regex_h = re.compile('#([0-9a-zA-Z][0-9a-zA-Z])([0-9a-zA-Z][0-9a-zA-Z])([0-9a-zA-Z][0-9a-zA-Z])')

def get(col_str):
    if col_str is None:
        col_str = ''
    global allcols
    if col_str in allcols.keys():
        return allcols[col_str]
    res = regex_t.search(col_str, 0)
    if res:
        return float(res.group(1)), float(res.group(2)), float(res.group(3))
    res = regex_h.search(col_str, 0)
    if res:
        return tuple([ float(int(res.group(i),16))/255 for i in range(1,4)])
    return colors.red

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

