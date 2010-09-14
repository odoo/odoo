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
import time
import osv
import pooler
from mx import DateTime as datetime
from tools.translate import _

_transaction_form = '''<?xml version="1.0"?>
<form string="Reconciliation">
    <separator string="Reconciliation transactions" colspan="4"/>
    <field name="trans_nbr"/>
    <newline/>
    <field name="credit"/>
    <field name="debit"/>
    <separator string="Write-Off" colspan="4"/>
    <field name="writeoff"/>
</form>'''

_transaction_fields = {
    'trans_nbr': {'string':'# of Transaction', 'type':'integer', 'readonly':True},
    'credit': {'string':'Credit amount', 'type':'float', 'readonly':True},
    'debit': {'string':'Debit amount', 'type':'float', 'readonly':True},
    'writeoff': {'string':'Write-Off amount', 'type':'float', 'readonly':True},
}

def _trans_rec_get(self, cr, uid, data, context=None):
    pool = pooler.get_pool(cr.dbname)
    account_move_line_obj = pool.get('account.move.line')
    credit = debit = 0
    account_id = False
    count = 0
    for line in account_move_line_obj.browse(cr, uid, data['ids'], context=context):
        if not line.reconcile_id and not line.reconcile_id.id:
            count += 1
            credit += line.credit
            debit += line.debit
            account_id = line.account_id.id
    return {'trans_nbr': count, 'account_id': account_id, 'credit': credit, 'debit': debit, 'writeoff': debit - credit}

def _trans_rec_reconcile_partial(self, cr, uid, data, context=None):
    pool = pooler.get_pool(cr.dbname)
    account_move_line_obj = pool.get('account.move.line')
    account_move_line_obj.reconcile_partial(cr, uid, data['ids'], 'manual', context=context)
    return {}

def _trans_rec_reconcile(self, cr, uid, data, context=None):
    pool = pooler.get_pool(cr.dbname)
    account_move_line_obj = pool.get('account.move.line')

    form = data['form']
    account_id = form.get('writeoff_acc_id', False)
    context['date_p'] = form.get('date_p', False)
    date = False
    if context['date_p']:
        date = datetime.strptime(context['date_p'], '%Y-%m-%d')
    ids = pool.get('account.period').find(cr, uid, dt=date, context=context)
    period_id = False
    if len(ids):
        period_id = ids[0]

    journal_id = form.get('journal_id', False)
    context['comment'] = form.get('comment', False)
    context['analytic_id'] = form.get('analytic_id', False)
    account_move_line_obj.reconcile(cr, uid, data['ids'], 'manual', account_id,
            period_id, journal_id, context=context)
    return {}

def _partial_check(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    currency = pool.get('res.users').browse(cr, uid, uid, context).company_id.currency_id
    writeoff = _trans_rec_get(self,cr, uid, data, context)['writeoff']
    
    if pool.get('res.currency').is_zero(cr, uid, currency, writeoff):
        return 'init_full'
    return 'init_partial'

_transaction_add_form = '''<?xml version="1.0"?>
<form string="Information addendum">
    <separator string="Write-Off Move" colspan="4"/>
    <field name="journal_id"/>
    <field name="writeoff_acc_id" domain="[('type', '&lt;&gt;', 'view')]"/>
    <field name="date_p"/>
    <field name="comment"/>
    <separator string="Analytic" colspan="4"/>
    <field name="analytic_id"/>
</form>'''

_transaction_add_fields = {
    'journal_id': {'string': 'Write-Off Journal', 'type': 'many2one', 'relation':'account.journal', 'required':True},
    'writeoff_acc_id': {'string':'Write-Off account', 'type':'many2one', 'relation':'account.account', 'required':True},
    'date_p': {'string':'Date','type':'date'},
    'comment': {'string':'Comment','type':'char', 'size': 64, 'required':True},
    'analytic_id': {'string':'Analytic Account', 'type': 'many2one', 'relation':'account.analytic.account'},
}

def _trans_rec_addendum(self, cr, uid, data, context={}):
    date_p = time.strftime('%Y-%m-%d')
    return {'date_p':date_p, 'comment': _('Write-Off')}


class wiz_reconcile(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'choice', 'next_state': _partial_check}
        },
        'init_full': {
            'actions': [_trans_rec_get],
            'result': {'type': 'form', 'arch':_transaction_form, 'fields':_transaction_fields, 'state':[('end','Cancel'),('reconcile','Reconcile')]}
        },
        'init_partial': {
            'actions': [_trans_rec_get],
            'result': {'type': 'form', 'arch':_transaction_form, 'fields':_transaction_fields, 'state':[('end','Cancel'),('addendum','Reconcile With Write-Off'),('partial','Partial Reconcile')]}
        },
        'addendum': {
            'actions': [_trans_rec_addendum],
            'result': {'type': 'form', 'arch':_transaction_add_form, 'fields':_transaction_add_fields, 'state':[('end','Cancel'),('reconcile','Reconcile')]}
        },
        'reconcile': {
            'actions': [_trans_rec_reconcile],
            'result': {'type': 'state', 'state':'end'}
        },
        'partial': {
            'actions': [_trans_rec_reconcile_partial],
            'result': {'type': 'state', 'state':'end'}
        }
    }
wiz_reconcile('account.move.line.reconcile')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

