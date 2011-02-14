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
import tools

class auction_pay_sel(osv.osv_memory):
    _name = "auction.pay.sel"
    _description = "Pay Invoice"

    _columns= {
       'amount': fields.float('Amount paid', digits= (16, 2), required=True),
       'dest_account_id':fields.many2one('account.account', 'Payment to Account', required=True, domain= [('type', '=', 'cash')]),
       'journal_id':fields.many2one('account.journal', 'Journal', required=True),
       'period_id':fields.many2one('account.period', 'Period', required=True),
    }

    def pay_and_reconcile(self, cr, uid, ids, context=None):
        """
        Pay and Reconcile
        @param cr: the current row, from the database cursor.
        @param uid: the current user’s ID for security checks.
        @param ids: the ID or list of IDs
        @param context: A standard dictionary
        @return:
        """
        if context is None: 
            context = {}
        lot = self.pool.get('auction.lots').browse(cr, uid, context['active_id'], context=context)
        invoice_obj = self.pool.get('account.invoice')
        for datas in self.read(cr, uid, ids, context=context):
            account_id = datas.get('writeoff_acc_id', False)
            period_id = datas.get('period_id', False)
            journal_id = datas.get('journal_id', False)
            if lot.sel_inv_id:
                p = invoice_obj.pay_and_reconcile(['lot.sel_inv_id.id'], datas['amount'], datas['dest_account_id'], journal_id, account_id, period_id, journal_id, context)
            return {'type': 'ir.actions.act_window_close'}

auction_pay_sel()
