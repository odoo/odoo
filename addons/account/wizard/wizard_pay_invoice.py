# -*- coding: utf-8 -*-
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
    'amount': {'string': 'Amount paid', 'type':'float', 'required':True},
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

    invoice = pool.get('account.invoice').browse(cr, uid, data['id'], context)
    journal = pool.get('account.journal').browse(cr, uid, data['form']['journal_id'], context)
    if journal.currency and invoice.company_id.currency_id.id<>journal.currency.id:
        ctx = {'date':data['form']['date']}
        amount = cur_obj.compute(cr, uid, journal.currency.id, invoice.company_id.currency_id.id, amount, context=ctx)

    # Take the choosen date
    if form.has_key('comment'):
        context={'date_p':form['date'],'comment':form['comment']}
    else:
        context={'date_p':form['date'],'comment':False}

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
    if invoice.company_id.currency_id.id <> invoice.currency_id.id:
        return 'addendum'
    if journal.currency and (journal.currency.id <> invoice.currency_id.id):
        return 'addendum'
    if pool.get('res.currency').is_zero(cr, uid, invoice.currency_id,
            (data['form']['amount'] - invoice.amount_total)):
        return 'reconcile'
    return 'addendum'

_transaction_add_form = '''<?xml version="1.0"?>
<form string="Information addendum">
    <separator string="Write-Off Move" colspan="4"/>
    <field name="writeoff_acc_id" domain="[('type','&lt;&gt;','view'),('type','&lt;&gt;','consolidation')]"/>
    <field name="writeoff_journal_id"/>
    <field name="comment"/>
</form>'''

_transaction_add_fields = {
    'writeoff_acc_id': {'string':'Write-Off account', 'type':'many2one', 'relation':'account.account', 'required':True},
    'writeoff_journal_id': {'string': 'Write-Off journal', 'type': 'many2one', 'relation':'account.journal', 'required':True},
    'comment': {'string': 'Entry Name', 'type':'char', 'size': 64, 'required':True},
}

def _get_value_addendum(self, cr, uid, data, context={}):
    return {}

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

