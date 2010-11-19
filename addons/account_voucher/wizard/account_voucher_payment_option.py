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
import decimal_precision as dp

class account_voucher_pay_writeoff(osv.osv_memory):
    """
    Opens the write off amount pay form.
    """
    _name = "account.voucher.pay.writeoff"
    _description = "Pay Voucher"

    def _get_amount(self, cr, uid, context=None):
        voucher_obj = self.pool.get('account.voucher')
        voucher = voucher_obj.browse(cr, uid, context['voucher_id'], context=context)
        amount = 0.0
        for line in voucher.line_ids:
            amount += line.amount_unreconciled
        diff = amount - voucher.amount
        return diff

    _columns = {
        'payment_option':fields.selection([
                                           ('not_reconcile', 'Do not reconcile balance'),
                                           ('close_balance', 'close the balance'),
                                           ], 'Payment Option', required=True),
        'writeoff_amount': fields.float('Writeoff Amount', required=True, digits_compute = dp.get_precision('Account')),
        'writeoff_acc_id': fields.many2one('account.account', 'Write-Off account'),
        'writeoff_journal_id': fields.many2one('account.journal', 'Write-Off journal'),
        'comment': fields.char('Comment', size=64, required=True),
        'analytic_id': fields.many2one('account.analytic.account','Analytic Account'),
    }
    _defaults = {
        'payment_option': 'not_reconcile',
        'comment': 'Write-Off',
        'writeoff_amount': _get_amount
    }

    def pay_and_reconcile_writeoff(self, cr, uid, ids, context=None):
        voucher_obj = self.pool.get('account.voucher')
        data =  self.read(cr, uid, ids, context=context)[0]
        voucher_id = context.get('voucher_id', False)
        if data['payment_option'] == 'close_balance':
            context.update({'write_off':data})
        voucher_obj.action_move_line_create(cr, uid, [voucher_id], context=context)
        return {}

account_voucher_pay_writeoff()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
