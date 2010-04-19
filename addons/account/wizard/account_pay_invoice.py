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
import time

from osv import fields, osv
from tools.translate import _
import decimal_precision as dp

class account_invoice_pay_writeoff(osv.osv_memory):
    """
    Opens the write off amount pay form.
    """
    _name = "account.invoice.pay.writeoff"
    _description = "Pay Invoice  "
    _columns = {
        'writeoff_acc_id': fields.many2one('account.account', 'Write-Off account', required=True),
        'writeoff_journal_id': fields.many2one('account.journal', 'Write-Off journal', required=True),
        'comment': fields.char('Comment', size=64, required=True),
        'analytic_id': fields.many2one('account.analytic.account','Analytic Account'),
        }
    _defaults = {
        'comment': 'Write-Off',
        }

    def pay_and_reconcile_writeoff(self, cr, uid, ids, context=None):
        data =  self.read(cr, uid, ids,context=context)[0]
        context.update({'write_off':data})
        self.pool.get('account.invoice.pay').pay_and_reconcile(cr, uid, ids, context=context)
        return {}

account_invoice_pay_writeoff()

class account_invoice_pay(osv.osv_memory):
    """
    Generate pay invoice wizard, user can make partial or full payment for invoice.
    """
    _name = "account.invoice.pay"
    _description = "Pay Invoice  "
    _columns = {
        'amount': fields.float('Amount paid', required=True, digits_compute = dp.get_precision('Account')),
        'name': fields.char('Entry Name', size=64, required=True),
        'date': fields.date('Date payment', required=True),
        'journal_id': fields.many2one('account.journal', 'Journal/Payment Mode', required=True),
        'period_id': fields.many2one('account.period', 'Period', required=True),
        }

    def view_init(self, cr, uid, ids, context=None):
        invoice = self.pool.get('account.invoice').browse(cr, uid, context['active_id'], context=context)
        if invoice.state in ['draft', 'proforma2', 'cancel']:
            raise osv.except_osv(_('Error !'), _('Can not pay draft/proforma/cancel invoice.'))
        pass

    def _get_period(self, cr, uid, context=None):
        ids = self.pool.get('account.period').find(cr, uid, context=context)
        period_id = False
        if len(ids):
            period_id = ids[0]
        return period_id

    def _get_amount(self, cr, uid, context=None):
        return self.pool.get('account.invoice').browse(cr, uid, context['active_id'], context=context).residual

    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'period_id': _get_period,
        'amount': _get_amount,
        }

    def wo_check(self, cr, uid, ids, context=None):
        cur_obj = self.pool.get('res.currency')
        mod_obj = self.pool.get('ir.model.data')
        if context is None:
            context = {}
        data =  self.read(cr, uid, ids,context=context)[0]
        invoice = self.pool.get('account.invoice').browse(cr, uid, context['active_id'], context)
        journal = self.pool.get('account.journal').browse(cr, uid, data['journal_id'], context)

       # Here we need that:
        #    The invoice total amount in company's currency <> paid amount in company currency
        #    (according to the correct day rate, invoicing rate and payment rate are may be different)
        #    => Ask to a write-off of the difference. This could happen even if both amount are equal,
        #    because if the currency rate
        # Get the amount in company currency for the invoice (according to move lines)
        inv_amount_company_currency = 0
        for aml in invoice.move_id.line_id:
            if aml.account_id.id == invoice.account_id.id or aml.account_id.type in ('receivable', 'payable'):
                inv_amount_company_currency += aml.debit
                inv_amount_company_currency -= aml.credit
        inv_amount_company_currency = abs(inv_amount_company_currency)

        # Get the current amount paid in company currency
        if journal.currency and invoice.company_id.currency_id.id<>journal.currency.id:
            ctx = {'date':data['date']}
            amount_paid = cur_obj.compute(cr, uid, journal.currency.id, invoice.company_id.currency_id.id, data['amount'], round=True, context=ctx)
        else:
            amount_paid = data['amount']
        # Get the old payment if there are some
        if invoice.payment_ids:
            debit=credit=0.0
            for payment in invoice.payment_ids:
                debit+=payment.debit
                credit+=payment.credit
            amount_paid+=abs(debit-credit)

        # Test if there is a difference according to currency rouding setting
        if self.pool.get('res.currency').is_zero(cr, uid, invoice.company_id.currency_id,
                (amount_paid - inv_amount_company_currency)):
            return self.pay_and_reconcile(cr, uid, ids, context=context)
        else:
            model_data_ids = mod_obj.search(cr, uid,[('model','=','ir.ui.view'),('name','=','view_account_invoice_pay_writeoff')], context=context)
            resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
            return {
                'name': _('Information addendum'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.invoice.pay.writeoff',
                'views': [(resource_id,'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
            }

    def pay_and_reconcile(self, cr, uid, ids, context=None):
        cur_obj = self.pool.get('res.currency')
        if context is None:
            context = {}
        data =  self.read(cr, uid, ids,context=context)[0]
        writeoff_account_id = False
        writeoff_journal_id = False
        comment = False

        if 'write_off' in context and context['write_off'] :
            writeoff_account_id = context['write_off']['writeoff_acc_id']
            writeoff_journal_id = context['write_off']['writeoff_journal_id']
            comment = context['write_off']['comment']

        amount = data['amount']

        invoice = self.pool.get('account.invoice').browse(cr, uid, context['active_id'], context)
        journal = self.pool.get('account.journal').browse(cr, uid, data['journal_id'], context)
        # Compute the amount in company's currency, with the journal currency (which is equal to payment currency)
        # when it is needed :  If payment currency (according to selected journal.currency) is <> from company currency
        if journal.currency and invoice.company_id.currency_id.id<>journal.currency.id:
            ctx = {'date':data['date']}
            amount = cur_obj.compute(cr, uid, journal.currency.id, invoice.company_id.currency_id.id, amount, context=ctx)
            currency_id = journal.currency.id
            # Put the paid amount in currency, and the currency, in the context if currency is different from company's currency
            context.update({'amount_currency':data['amount'],'currency_id':currency_id})

        if invoice.company_id.currency_id.id<>invoice.currency_id.id:
            ctx = {'date':data['date']}
            amount = cur_obj.compute(cr, uid, invoice.currency_id.id, invoice.company_id.currency_id.id, amount, context=ctx)
            currency_id = invoice.currency_id.id
            # Put the paid amount in currency, and the currency, in the context if currency is different from company's currency
            context.update({'amount_currency':data['amount'],'currency_id':currency_id})

        # Take the choosen date
        if comment:
            context.update({'date_p':data['date'],'comment':comment})
        else:
            context.update({'date_p':data['date'],'comment':False})

        acc_id = journal.default_credit_account_id and journal.default_credit_account_id.id
        if not acc_id:
            raise osv.except_osv(_('Error !'), _('Your journal must have a default credit and debit account.'))
        self.pool.get('account.invoice').pay_and_reconcile(cr, uid, [context['active_id']],
                amount, acc_id, data['period_id'], data['journal_id'], writeoff_account_id,
                data['period_id'], writeoff_journal_id, context, data['name'])
        return {}

account_invoice_pay()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: