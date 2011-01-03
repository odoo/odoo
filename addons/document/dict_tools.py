# -*- encoding: utf-8 -*-
# Copyright P. Christeas <p_christ@hol.gr> 2008-2010
# Copyright 2010 OpenERP SA. http://www.openerp.com
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
###############################################################################


def dict_merge(*dicts):
    """ Return a dict with all values of dicts
    """
    res = {}
    for d in dicts:
        res.update(d)
    return res

def dict_merge2(*dicts):
    """ Return a dict with all values of dicts.
        If some key appears twice and contains iterable objects, the values
        are merged (instead of overwritten).
    """
    res = {}
    for d in dicts:
        for k in d.keys():
            if k in res and isinstance(res[k], (list, tuple)):
                res[k] = res[k] + d[k]
            elif k in res and isinstance(res[k], dict):
                res[k].update(d[k])
            else:
                res[k] = d[k]
    return res

def dict_filter(srcdic, keys, res=None):
    ''' Return a copy of srcdic that has only keys set.
    If any of keys are missing from srcdic, the result won't have them, 
    either.
    @param res If given, result will be updated there, instead of a new dict.
    '''
    if res is None:
        res = {}
    for k in keys:
        if k in srcdic:
            res[k] = srcdic[k]
    return res

#eof
