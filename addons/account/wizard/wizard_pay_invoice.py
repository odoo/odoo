# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

import wizard
import netsvc
import pooler
import time
from tools.translate import _
import tools

pay_form = '''<?xml version="1.0"?>
<form string="Pay invoice">
    <field name="amount"/>
    <newline/>
    <field name="name"/>
    <field name="date"/>
    <field name="journal_id"/>
    <field name="period_id"/>
</form>'''

pay_fields = {
    'amount': {'string': 'Amount paid', 'type':'float', 'required':True, 'digits': (16,int(tools.config['price_accuracy']))},
    'name': {'string': 'Entry Name', 'type':'char', 'size': 64, 'required':True},
    'date': {'string': 'Payment date', 'type':'date', 'required':True, 'default':lambda *args: time.strftime('%Y-%m-%d')},
    'journal_id': {'string': 'Journal/Payment Mode', 'type': 'many2one', 'relation':'account.journal', 'required':True, 'domain':[('type','=','cash')]},
    'period_id': {'string': 'Period', 'type': 'many2one', 'relation':'account.period', 'required':True},
}

def _pay_and_reconcile(self, cr, uid, data, context):
    form = data['form']
    period_id = form.get('period_id', False)
    journal_id = form.get('journal_id', False)
    writeoff_account_id = form.get('writeoff_acc_id', False)
    writeoff_journal_id = form.get('writeoff_journal_id', False)
    pool = pooler.get_pool(cr.dbname)
    cur_obj = pool.get('res.currency')
    amount = form['amount']
    context['analytic_id'] = form.get('analytic_id', False)

    invoice = pool.get('account.invoice').browse(cr, uid, data['id'], context)
    journal = pool.get('account.journal').browse(cr, uid, data['form']['journal_id'], context)
    # Compute the amount in company's currency, with the journal currency (which is equal to payment currency) 
    # when it is needed :  If payment currency (according to selected journal.currency) is <> from company currency
    cur_diff = False
    if journal.currency and invoice.company_id.currency_id.id<>journal.currency.id:
        ctx = {'date':data['form']['date']}
        amount = cur_obj.compute(cr, uid, journal.currency.id, invoice.company_id.currency_id.id, amount, context=ctx)
        currency_id = journal.currency.id
        # Put the paid amount in currency, and the currency, in the context if currency is different from company's currency
        context.update({'amount_currency':form['amount'],'currency_id':currency_id,'company_currency_id':invoice.company_id.currency_id.id})
        cur_diff = True
        
    if not journal.currency and invoice.company_id.currency_id.id<>invoice.currency_id.id and (not cur_diff):
        ctx = {'date':data['form']['date']}
        amount = cur_obj.compute(cr, uid, invoice.currency_id.id, invoice.company_id.currency_id.id, amount, context=ctx)
        currency_id = invoice.currency_id.id
        # Put the paid amount in currency, and the currency, in the context if currency is different from company's currency
        context.update({'amount_currency':form['amount'],'currency_id':currency_id,'company_currency_id':invoice.company_id.currency_id.id})

    # Take the chosen date
    if form.has_key('comment'):
        context.update({'date_p':form['date'],'comment':form['comment']})
    else:
        context.update({'date_p':form['date'],'comment':False})      

    acc_id = journal.default_credit_account_id and journal.default_credit_account_id.id
    if not acc_id:
        raise wizard.except_wizard(_('Error !'), _('Your journal must have a default credit and debit account.'))
    pool.get('account.invoice').pay_and_reconcile(cr, uid, [data['id']],
            amount, acc_id, period_id, journal_id, writeoff_account_id,
            period_id, writeoff_journal_id, context, data['form']['name'])
    return {}

def _wo_check(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    invoice = pool.get('account.invoice').browse(cr, uid, data['id'], context)
    journal = pool.get('account.journal').browse(cr, uid, data['form']['journal_id'], context)
    cur_obj = pool.get('res.currency')
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
        ctx = {'date':data['form']['date']}
        amount_paid = cur_obj.compute(cr, uid, journal.currency.id, invoice.company_id.currency_id.id, data['form']['amount'], round=True, context=ctx)
    else:
        amount_paid = data['form']['amount']
    # Get the old payment if there are some
    if invoice.payment_ids:
        debit=credit=0.0
        for payment in invoice.payment_ids:
            debit+=payment.debit
            credit+=payment.credit
        amount_paid+=abs(debit-credit)
        
    # Test if there is a difference according to currency rouding setting
    if pool.get('res.currency').is_zero(cr, uid, invoice.company_id.currency_id,
            (amount_paid - inv_amount_company_currency)):
        return 'reconcile'
    return 'addendum'

_transaction_add_form = '''<?xml version="1.0"?>
<form string="Information addendum">
    <separator string="Write-Off Move" colspan="4"/>
    <field name="writeoff_journal_id"/>
    <field name="writeoff_acc_id" domain="[('type','&lt;&gt;','view'),('type','&lt;&gt;','consolidation')]"/>
    <field name="comment"/>
    <separator string="Analytic" colspan="4"/>
    <field name="analytic_id"/>
</form>'''

_transaction_add_fields = {
    'writeoff_acc_id': {'string':'Write-Off account', 'type':'many2one', 'relation':'account.account', 'required':True},
    'writeoff_journal_id': {'string': 'Write-Off journal', 'type': 'many2one', 'relation':'account.journal', 'required':True},
    'comment': {'string': 'Comment', 'type':'char', 'size': 64 , 'required':True},
    'analytic_id': {'string':'Analytic Account', 'type': 'many2one', 'relation':'account.analytic.account'},
}

def _get_value_addendum(self, cr, uid, data, context={}):
    return {'comment': _('Write-Off')}

def _get_period(self, cr, uid, data, context={}):
    pool = pooler.get_pool(cr.dbname)
    ids = pool.get('account.period').find(cr, uid, context=context)
    period_id = False
    if len(ids):
        period_id = ids[0]
    invoice = pool.get('account.invoice').browse(cr, uid, data['id'], context)
    if invoice.state in ['draft', 'proforma2', 'cancel']:
        raise wizard.except_wizard(_('Error !'), _('Can not pay draft/proforma/cancel invoice.'))
    return {
        'period_id': period_id,
        'amount': invoice.residual,
        'date': time.strftime('%Y-%m-%d')
    }

class wizard_pay_invoice(wizard.interface):
    states = {
        'init': {
            'actions': [_get_period],
            'result': {'type':'form', 'arch':pay_form, 'fields':pay_fields, 'state':[('end','Cancel'),('reconcile','Partial Payment'),('writeoff_check','Full Payment')]}
        },
        'writeoff_check': {
            'actions': [],
            'result' : {'type': 'choice', 'next_state': _wo_check }
        },
        'addendum': {
            'actions': [_get_value_addendum],
            'result': {'type': 'form', 'arch':_transaction_add_form, 'fields':_transaction_add_fields, 'state':[('end','Cancel'),('reconcile','Pay and reconcile')]}
        },
        'reconcile': {
            'actions': [_pay_and_reconcile],
            'result': {'type':'state', 'state':'end'}
        }
    }
wizard_pay_invoice('account.invoice.pay')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
