# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2007 TINY SPRL. (http://tiny.be) All Rights Reserved.
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
#
##############################################################################

import netsvc
import time
from osv import fields, osv

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _description = 'Account Invoice'

    def _amount_residual(self, cr, uid, ids, name, args, context={}):
        res = {}
        data_inv = self.browse(cr, uid, ids)
        for inv in data_inv:
            paid_amt = 0.0
            to_pay = inv.amount_total
            for lines in inv.move_lines:
                paid_amt = paid_amt + lines.credit
            res[inv.id] = to_pay - paid_amt
        return res

    def _get_lines(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for id in ids:
            move_lines = self.move_line_id_payment_get(cr,uid,[id])
            if not move_lines:
                res[id] = []
                continue
            data_lines = self.pool.get('account.move.line').browse(cr,uid,move_lines)
            for line in data_lines:
                ids_line = []
                if line.reconcile_id:
                    ids_line = line.reconcile_id.line_id
                elif line.reconcile_partial_id:
                    ids_line = line.reconcile_partial_id.line_partial_ids
                l = map(lambda x: x.id, ids_line)
                res[id]=[x for x in l if x <> line.id]
        return res

    _columns = {
        'move_lines':fields.function(_get_lines , method=True,type='many2many' , relation='account.move.line',string='Move Lines'),
        'residual': fields.function(_amount_residual, method=True, digits=(16,2),string='Residual', store=True),
                }

account_invoice()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

