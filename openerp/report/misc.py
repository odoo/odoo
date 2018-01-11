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

from pychart import *

colorline = [color.T(r=((r+3) % 11)/10.0,
                     g=((g+6) % 11)/10.0,
                     b=((b+9) % 11)/10.0)
             for r in range(11) for g in range(11) for b in range(11)]

def choice_colors(n):
    if n:
        return colorline[0:-1:len(colorline)/n]
    return []

if __name__=='__main__':
    print choice_colors(10)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

