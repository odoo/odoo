# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields,osv



class showdiff(osv.osv_memory):
    _name = 'wizard.wiki.history.show_diff'
    
    def _get_diff(self, cr, uid, ctx):
        print 'XXXXXXXXXXXXXXXXXX : ', ctx
        history = self.pool.get('wiki.wiki.history')
        res = {}
#        if lan(ids) == 2:
#            diff = history.getDiff(cr, uid, ids[0]. ids[1])
#            res = {
#                ids[0] : diff,
#                ids[1] : diff,
#            }
        return res

    _columns = {
        'diff': fields.function(_get_diff, method=True, type='char', string='Diff'),
    }
    _defaults = {
        'diff': _get_diff
    }
showdiff()

    