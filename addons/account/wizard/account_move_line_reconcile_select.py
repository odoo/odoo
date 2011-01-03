# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import fields, osv
from tools.translate import _

class account_move_line_reconcile_select(osv.osv_memory):
    _name = "account.move.line.reconcile.select"
    _description = "Move line reconcile select"
    _columns = {
       'account_id': fields.many2one('account.account', 'Account', \
                            domain = [('reconcile', '=', 1)], required=True),
    }

    def action_open_window(self, cr, uid, ids, context=None):
        """
        This function Open  account move line window for reconcile on given account id
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: account move line reconcile select’s ID or list of IDs
        @return: dictionary of  Open  account move line window for reconcile on given account id

         """
        data = self.read(cr, uid, ids, context=context)[0]
        return {
            'domain': "[('account_id','=',%d),('reconcile_id','=',False),('state','<>','draft')]" % data['account_id'],
            'name': _('Reconciliation'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'res_model': 'account.move.line',
            'type': 'ir.actions.act_window'
        }

account_move_line_reconcile_select()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: