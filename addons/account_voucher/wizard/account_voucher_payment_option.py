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

class account_voucher_pay_writeoff(osv.osv_memory):
    """
    Opens the write off amount pay form.
    """
    _name = "account.voucher.pay.writeoff"
    _description = "Pay Voucher"
    _columns = {
        'payment_option':fields.selection([
                                           ('not_reconcile', 'Do not reconcile balance'),
                                           ('close_balance', 'close the balance'),
                                           ], 'Payment Option', required=True),
        'writeoff_acc_id': fields.many2one('account.account', 'Write-Off account'),
        'writeoff_journal_id': fields.many2one('account.journal', 'Write-Off journal'),
        'comment': fields.char('Comment', size=64, required=True),
        'analytic_id': fields.many2one('account.analytic.account','Analytic Account'),
    }
    _defaults = {
        'payment_option': 'not_reconcile',
        'comment': 'Write-Off',
    }

    def pay_and_reconcile_writeoff(self, cr, uid, ids, context=None):
        voucher_obj = self.pool.get('account.voucher')
        data =  self.read(cr, uid, ids,context=context)[0]
        voucher_id = context.get('voucher_id', False)
        if data['payment_option'] == 'not_reconcile':
            voucher_obj.action_move_line_create(cr, uid, [voucher_id], context=context)
            return {}
        context.update({'write_off':data})
        self.pool.get('account.voucher.pay').pay_and_reconcile(cr, uid, [voucher_id], context=context)
        return {}

account_voucher_pay_writeoff()

class account_voucher_pay(osv.osv_memory):
    """
    Generate pay invoice wizard, user can make partial or full payment for invoice.
    """
    _name = "account.voucher.pay"
    _description = "Pay Voucher"

    def pay_and_reconcile(self, cr, uid, ids, context=None):
        cur_obj = self.pool.get('res.currency')
        voucher_obj = self.pool.get('account.voucher')
        if context is None:
            context = {}
        voucher = voucher_obj.browse(cr, uid, [ids[0]], context=context)[0]
        writeoff_account_id = False
        writeoff_journal_id = False
        comment = False

        if 'write_off' in context and context['write_off'] :
            writeoff_account_id = context['write_off']['writeoff_acc_id']
            writeoff_journal_id = context['write_off']['writeoff_journal_id']
            comment = context['write_off']['comment']

        amount = voucher.amount
        journal = voucher.journal_id
        # Compute the amount in company's currency, with the journal currency (which is equal to payment currency)
        # when it is needed :  If payment currency (according to selected journal.currency) is <> from company currency
        if journal.currency and voucher.company_id.currency_id.id<>journal.currency.id:
            ctx = {'date': voucher.date}
            amount = cur_obj.compute(cr, uid, journal.currency.id, voucher.company_id.currency_id.id, amount, context=ctx)
            currency_id = journal.currency.id
            # Put the paid amount in currency, and the currency, in the context if currency is different from company's currency
            context.update({'amount_currency': voucher.amount, 'currency_id': currency_id})

        if voucher.company_id.currency_id.id<>voucher.currency_id.id:
            ctx = {'date':voucher.date}
            amount = cur_obj.compute(cr, uid, voucher.currency_id.id, voucher.company_id.currency_id.id, amount, context=ctx)
            currency_id = voucher.currency_id.id
            # Put the paid amount in currency, and the currency, in the context if currency is different from company's currency
            context.update({'amount_currency':voucher.amount,'currency_id':currency_id})

        # Take the choosen date
        if comment:
            context.update({'date_p':voucher.date, 'comment':comment})
        else:
            context.update({'date_p':voucher.date, 'comment':False})

        acc_id = journal.default_credit_account_id and journal.default_credit_account_id.id
        if not acc_id:
            raise osv.except_osv(_('Error !'), _('Your journal must have a default credit and debit account.'))

        voucher_obj.pay_and_reconcile(cr, uid, ids,
                amount, acc_id, voucher.period_id.id, journal.id, writeoff_account_id,
                voucher.period_id, writeoff_journal_id, context, voucher.name)
        return {}

account_voucher_pay()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
