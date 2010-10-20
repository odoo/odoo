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
import osv
import pooler
from tools.translate import _

_transaction_form = '''<?xml version="1.0"?>
<form string="Close Fiscal Year with new entries">
    <field name="fy_id"/>
    <field name="fy2_id"/>
    <field name="journal_id"/>
    <field name="period_id"/>
    <field name="report_name" colspan="4"/>

    <separator string="Are you sure you want to create entries?" colspan="4"/>
    <field name="sure"/>
</form>'''

_transaction_fields = {
    'fy_id': {'string':'Fiscal Year to close', 'type':'many2one', 'relation': 'account.fiscalyear','required':True, 'domain':[('state','=','draft')]},
    'journal_id': {'string':'Opening Entries Journal', 'type':'many2one', 'relation': 'account.journal','required':True},
    'period_id': {'string':'Opening Entries Period', 'type':'many2one', 'relation': 'account.period','required':True, 'domain':"[('fiscalyear_id','=',fy2_id)]"},
    'fy2_id': {'string':'New Fiscal Year', 'type':'many2one', 'relation': 'account.fiscalyear', 'domain':[('state','=','draft')], 'required':True},
    'report_name': {'string':'Name of new entries', 'type':'char', 'size': 64, 'required':True},
    'sure': {'string':'Check this box', 'type':'boolean'},
}

def _data_load(self, cr, uid, data, context):
    data['form']['report_name'] = _('End of Fiscal Year Entry')
    return data['form']

def _data_save(self, cr, uid, data, context):
    if not data['form']['sure']:
        raise wizard.except_wizard(_('UserError'), _('Closing of fiscal year cancelled, please check the box !'))
    pool = pooler.get_pool(cr.dbname)

    fy_id = data['form']['fy_id']
    period_ids = pool.get('account.period').search(cr, uid, [('fiscalyear_id', '=', fy_id)])
    cr.execute("SELECT id FROM account_period WHERE date_stop < (SELECT date_start FROM account_fiscalyear WHERE id = %s)" , (str(data['form']['fy2_id']),))
    fy_period_set = ','.join(map(lambda id: str(id[0]), cr.fetchall()))
    cr.execute("SELECT id FROM account_period WHERE date_start > (SELECT date_stop FROM account_fiscalyear WHERE id = %s)" , (str(fy_id),))
    fy2_period_set = ','.join(map(lambda id: str(id[0]), cr.fetchall()))
    period = pool.get('account.period').browse(cr, uid, data['form']['period_id'], context=context)
    new_fyear = pool.get('account.fiscalyear').browse(cr, uid, data['form']['fy2_id'], context=context)
    old_fyear = pool.get('account.fiscalyear').browse(cr, uid, data['form']['fy_id'], context=context)
    
    new_journal = data['form']['journal_id']
    new_journal = pool.get('account.journal').browse(cr, uid, new_journal, context=context)

    if not new_journal.default_credit_account_id or not new_journal.default_debit_account_id:
        raise wizard.except_wizard(_('UserError'),
                _('The journal must have default credit and debit account'))
    if (not new_journal.centralisation) or new_journal.entry_posted:
        raise wizard.except_wizard(_('UserError'),
                _('The journal must have centralised counterpart without the Skipping draft state option checked!'))

    move_ids = pool.get('account.move.line').search(cr, uid, [
        ('journal_id','=',new_journal.id),('period_id.fiscalyear_id','=',new_fyear.id)])
    if move_ids:
        raise wizard.except_wizard(_('UserError'),
                _('The opening journal must not have any entry in the new fiscal year !'))
    cr.execute("SELECT id FROM account_fiscalyear WHERE date_stop < %s", (str(new_fyear.date_start),))
    result = cr.dictfetchall()
    fy_ids = ','.join([str(x['id']) for x in result])
    query_line = pool.get('account.move.line')._query_get(cr, uid,
            obj='account_move_line', context={'fiscalyear': fy_ids})
    cr.execute('select id from account_account WHERE active')
    ids = map(lambda x: x[0], cr.fetchall())
    for account in pool.get('account.account').browse(cr, uid, ids,
        context={'fiscalyear': fy_id}):
        
        accnt_type_data = account.user_type
        if not accnt_type_data:
            continue
        if accnt_type_data.close_method=='none' or account.type == 'view':
            continue
        if accnt_type_data.close_method=='balance':
            if abs(account.balance)>0.0001:
                pool.get('account.move.line').create(cr, uid, {
                    'debit': account.balance>0 and account.balance,
                    'credit': account.balance<0 and -account.balance,
                    'name': data['form']['report_name'],
                    'date': period.date_start,
                    'journal_id': new_journal.id,
                    'period_id': period.id,
                    'account_id': account.id
                }, {'journal_id': new_journal.id, 'period_id':period.id})
        if accnt_type_data.close_method == 'unreconciled':
            offset = 0
            limit = 100
            while True:
                cr.execute('SELECT id, name, quantity, debit, credit, account_id, ref, ' \
                            'amount_currency, currency_id, blocked, partner_id, ' \
                            'date_maturity, date_created ' \
                        'FROM account_move_line ' \
                        'WHERE account_id = %s ' \
                            'AND ' + query_line + ' ' \
                            'AND reconcile_id is NULL ' \
                        'ORDER BY id ' \
                        'LIMIT %s OFFSET %s', (account.id, limit, offset))
                result = cr.dictfetchall()
                if not result:
                    break
                for move in result:
                    move.pop('id')
                    move.update({
                        'date': period.date_start,
                        'journal_id': new_journal.id,
                        'period_id': period.id,
                    })
                    pool.get('account.move.line').create(cr, uid, move, {
                        'journal_id': new_journal.id,
                        'period_id': period.id,
                        })
                offset += limit

            #We have also to consider all move_lines that were reconciled 
            #on another fiscal year, and report them too
            offset = 0
            limit = 100
            while True:
                cr.execute('SELECT DISTINCT b.id, b.name, b.quantity, b.debit, b.credit, b.account_id, b.ref, ' \
                            'b.amount_currency, b.currency_id, b.blocked, b.partner_id, ' \
                            'b.date_maturity, b.date_created ' \
                        'FROM account_move_line a, account_move_line b ' \
                        'WHERE b.account_id = %s ' \
                            'AND b.reconcile_id is NOT NULL ' \
                            'AND a.reconcile_id = b.reconcile_id ' \
                            'AND b.period_id IN ('+fy_period_set+') ' \
                            'AND a.period_id IN ('+fy2_period_set+') ' \
                        'ORDER BY id ' \
                        'LIMIT %s OFFSET %s', (account.id, limit, offset))
                result = cr.dictfetchall()
                if not result:
                    break
                for move in result:
                    move.pop('id')
                    move.update({
                        'date': period.date_start,
                        'journal_id': new_journal.id,
                        'period_id': period.id,
                    })
                    pool.get('account.move.line').create(cr, uid, move, {
                        'journal_id': new_journal.id,
                        'period_id': period.id,
                        })
                offset += limit
        if accnt_type_data.close_method=='detail':
            offset = 0
            limit = 100
            while True:
                cr.execute('SELECT id, name, quantity, debit, credit, account_id, ref, ' \
                            'amount_currency, currency_id, blocked, partner_id, ' \
                            'date_maturity, date_created ' \
                        'FROM account_move_line ' \
                        'WHERE account_id = %s ' \
                            'AND ' + query_line + ' ' \
                        'ORDER BY id ' \
                        'LIMIT %s OFFSET %s', (account.id, limit, offset))
                
                result = cr.dictfetchall()
                if not result:
                    break
                for move in result:
                    move.pop('id')
                    move.update({
                        'date': period.date_start,
                        'journal_id': new_journal.id,
                        'period_id': period.id,
                    })
                    pool.get('account.move.line').create(cr, uid, move)
                offset += limit
    ids = pool.get('account.move.line').search(cr, uid, [('journal_id','=',new_journal.id),
        ('period_id.fiscalyear_id','=',new_fyear.id)])
    context['fy_closing'] = True

    if ids:
        pool.get('account.move.line').reconcile(cr, uid, ids, context=context)
    new_period = data['form']['period_id']
    ids = pool.get('account.journal.period').search(cr, uid, [('journal_id','=',new_journal.id),('period_id','=',new_period)])
    if not ids:
        ids = [pool.get('account.journal.period').create(cr, uid, {
               'name': (new_journal.name or '')+':'+(period.code or ''),
               'journal_id': new_journal.id,
               'period_id': period.id
           })]
    cr.execute('UPDATE account_fiscalyear ' \
                'SET end_journal_period_id = %s ' \
                'WHERE id = %s', (ids[0], old_fyear.id))

    return {}

class wiz_journal_close(wizard.interface):
    states = {
        'init': {
            'actions': [_data_load],
            'result': {'type': 'form', 'arch':_transaction_form, 'fields':_transaction_fields, 'state':[('end','Cancel'),('close','Create entries')]}
        },
        'close': {
            'actions': [_data_save],
            'result': {'type': 'state', 'state':'end'}
        }
    }
wiz_journal_close('account.fiscalyear.close')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

