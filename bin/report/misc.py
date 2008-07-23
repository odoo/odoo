# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
###############################################################################
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

