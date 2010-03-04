# -*- coding: utf-8 -*-
#
# Copyright P. Christeas <p_christ@hol.gr> 2008,2009
#
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

__export_bis = {}
import sys

def __init_ebis():
    global __export_bis

    _evars = [ 'abs', 'all', 'any', 'basestring' , 'bool',
        'chr', 'cmp','complex', 'dict', 'divmod', 'enumerate',
        'float', 'frozenset', 'getattr', 'hasattr', 'hash',
        'hex', 'id','int', 'iter', 'len', 'list', 'long', 'map', 'max',
        'min', 'oct', 'ord','pow', 'range', 'reduce', 'repr',
        'reversed', 'round', 'set', 'setattr', 'slice','sorted', 'str',
        'sum', 'tuple','type', 'unichr','unicode', 'xrange',
        'True','False', 'None', 'NotImplemented', 'Ellipsis', ]

    if sys.version_info[0:2] >= (2,6):
        _evars.extend(['bin', 'format', 'next'])
    for v in _evars:
        __export_bis[v] = __builtins__[v]


__init_ebis()


def safe_eval(expr,sglobals,slocals = None):
    """ A little safer version of eval().
        This one, will use fewer builtin functions, so that only
        arithmetic and logic expressions can really work """

    global __export_bis

    if not sglobals.has_key('__builtins__'):
        # we copy, because we wouldn't want successive calls to safe_eval
        # to be able to alter the builtins.
        sglobals['__builtins__'] = __export_bis.copy()

    return eval(expr,sglobals,slocals)

#eof
