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

def _data_save(self, cr, uid, data, context=None):
    """
    This function close account fiscalyear and create entries in new fiscalyear
    @param cr: the current row, from the database cursor,
    @param uid: the current user’s ID for security checks,
    @param ids: List of Account fiscalyear close state’s IDs

    """
    pool = pooler.get_pool(cr.dbname)
    obj_acc_period = pool.get('account.period')
    obj_acc_fiscalyear = pool.get('account.fiscalyear')
    obj_acc_journal = pool.get('account.journal')
    obj_acc_move = pool.get('account.move')
    obj_acc_move_line = pool.get('account.move.line')
    obj_acc_account = pool.get('account.account')
    obj_acc_journal_period = pool.get('account.journal.period')
    currency_obj = pool.get('res.currency')

    if context is None:
        context = {}
    fy_id = data['form']['fy_id']

    cr.execute("SELECT id FROM account_period WHERE date_stop < (SELECT date_start FROM account_fiscalyear WHERE id = %s)", (str(data['form']['fy2_id']),))
    fy_period_set = ','.join(map(lambda id: str(id[0]), cr.fetchall()))
    cr.execute("SELECT id FROM account_period WHERE date_start > (SELECT date_stop FROM account_fiscalyear WHERE id = %s)", (str(fy_id),))
    fy2_period_set = ','.join(map(lambda id: str(id[0]), cr.fetchall()))

    period = obj_acc_period.browse(cr, uid, data['form']['period_id'], context=context)
    new_fyear = obj_acc_fiscalyear.browse(cr, uid, data['form']['fy2_id'], context=context)
    old_fyear = obj_acc_fiscalyear.browse(cr, uid, data['form']['fy_id'], context=context)

    new_journal = data['form']['journal_id']
    new_journal = obj_acc_journal.browse(cr, uid, new_journal, context=context)

    if not new_journal.default_credit_account_id or not new_journal.default_debit_account_id:
        raise osv.except_osv(_('UserError'),
                _('The journal must have default credit and debit account'))
    if (not new_journal.centralisation) or new_journal.entry_posted:
        raise osv.except_osv(_('UserError'),
                _('The journal must have centralised counterpart without the Skipping draft state option checked!'))

    move_ids = obj_acc_move_line.search(cr, uid, [
        ('journal_id', '=', new_journal.id), ('period_id.fiscalyear_id', '=', new_fyear.id)])

    if move_ids:
        raise wizard.except_wizard(_('UserError'),
                _('The opening journal must not have any entry in the new fiscal year !'))
    #if move_ids:
        #obj_acc_move_line._remove_move_reconcile(cr, uid, move_ids, context=context)
    #    obj_acc_move_line.unlink(cr, uid, move_ids, context=context)

    cr.execute("SELECT id FROM account_fiscalyear WHERE date_stop < %s", (str(new_fyear.date_start),))
    result = cr.dictfetchall()
    fy_ids = ','.join([str(x['id']) for x in result])
    query_line = obj_acc_move_line._query_get(cr, uid,
            obj='account_move_line', context={'fiscalyear': fy_ids})
    #create the opening move
    vals = {
        'name': '/',
        'ref': '',
        'period_id': period.id,
        'journal_id': new_journal.id,
    }
    move_id = obj_acc_move.create(cr, uid, vals, context=context)

    #1. report of the accounts with defferal method == 'unreconciled'
    cr.execute('''
        SELECT a.id 
        FROM account_account a
        LEFT JOIN account_account_type t ON (a.user_type = t.id)
        WHERE a.active 
          AND a.type != 'view'
          AND t.close_method = %s''', ('unreconciled', ))
    account_ids = map(lambda x: x[0], cr.fetchall())

    if account_ids:
        cr.execute('''
            INSERT INTO account_move_line (
                 name, create_uid, create_date, write_uid, write_date,
                 statement_id, journal_id, currency_id, date_maturity,
                 partner_id, blocked, credit, state, debit,
                 ref, account_id, period_id, date, move_id, amount_currency, 
                 quantity, product_id) 
              (SELECT name, create_uid, create_date, write_uid, write_date,
                 statement_id, %s,currency_id, date_maturity, partner_id,
                 blocked, credit, 'draft', debit, ref, account_id,
                 %s, date, %s, amount_currency, quantity,product_id
               FROM account_move_line
               WHERE account_id IN %s 
                 AND ''' + query_line + ''' 
                 AND reconcile_id IS NULL)''', (new_journal.id, period.id, move_id, tuple(account_ids),))


        #We have also to consider all move_lines that were reconciled
        #on another fiscal year, and report them too
        cr.execute('''
            INSERT INTO account_move_line (
                 name, create_uid, create_date, write_uid, write_date,
                 statement_id, journal_id, currency_id, date_maturity,
                 partner_id, blocked, credit, state, debit,
                 ref, account_id, period_id, date, move_id, amount_currency, 
                 quantity, product_id) 
              (SELECT 
                 b.name, b.create_uid, b.create_date, b.write_uid, b.write_date,
                 b.statement_id, %s, b.currency_id, b.date_maturity,
                 b.partner_id, b.blocked, b.credit, 'draft', b.debit,
                 b.ref, b.account_id, %s, b.date, %s, b.amount_currency, 
                 b.quantity, b.product_id
                 FROM account_move_line a, account_move_line b
                 WHERE b.account_id IN %s
                   AND b.reconcile_id IS NOT NULL
                   AND a.reconcile_id = b.reconcile_id
                   AND b.period_id IN ('''+fy_period_set+''')
                   AND a.period_id IN ('''+fy2_period_set+'''))''', (new_journal.id, period.id, move_id, tuple(account_ids),))

    #2. report of the accounts with defferal method == 'detail'
    cr.execute('''
        SELECT a.id 
        FROM account_account a
        LEFT JOIN account_account_type t ON (a.user_type = t.id)
        WHERE a.active 
          AND a.type != 'view'
          AND t.close_method = %s''', ('detail', ))
    account_ids = map(lambda x: x[0], cr.fetchall())

    if account_ids:
        cr.execute('''
            INSERT INTO account_move_line (
                 name, create_uid, create_date, write_uid, write_date,
                 statement_id, journal_id, currency_id, date_maturity,
                 partner_id, blocked, credit, state, debit,
                 ref, account_id, period_id, date, move_id, amount_currency, 
                 quantity, product_id) 
              (SELECT name, create_uid, create_date, write_uid, write_date,
                 statement_id, %s,currency_id, date_maturity, partner_id,
                 blocked, credit, 'draft', debit, ref, account_id,
                 %s, date, %s, amount_currency, quantity,product_id
               FROM account_move_line
               WHERE account_id IN %s 
                 AND ''' + query_line + ''') 
                 ''', (new_journal.id, period.id, move_id, tuple(account_ids),))


    #3. report of the accounts with defferal method == 'balance'
    cr.execute('''
        SELECT a.id 
        FROM account_account a
        LEFT JOIN account_account_type t ON (a.user_type = t.id)
        WHERE a.active 
          AND a.type != 'view'
          AND t.close_method = %s''', ('balance', ))
    account_ids = map(lambda x: x[0], cr.fetchall())

    for account in obj_acc_account.browse(cr, uid, account_ids, context={'fiscalyear': fy_id}):
        accnt_type_data = account.user_type
        if accnt_type_data.close_method == 'balance':
            balance_in_currency = 0.0
            if account.currency_id:
                cr.execute('SELECT sum(amount_currency) as balance_in_currency FROM account_move_line ' \
                        'WHERE account_id = %s ' \
                            'AND ' + query_line + ' ' \
                            'AND currency_id = %s', (account.id, account.currency_id.id)) 
                balance_in_currency = cr.dictfetchone()['balance_in_currency']

            company_currency_id = pool.get('res.users').browse(cr, uid, uid).company_id.currency_id
            if not currency_obj.is_zero(cr, uid, company_currency_id, abs(account.balance)):
                obj_acc_move_line.create(cr, uid, {
                    'debit': account.balance > 0 and account.balance,
                    'credit': account.balance < 0 and -account.balance,
                    'name': data['form']['report_name'],
                    'date': period.date_start,
                    'move_id': move_id,
                    'journal_id': new_journal.id,
                    'period_id': period.id,
                    'account_id': account.id,
                    'currency_id': account.currency_id and account.currency_id.id or False,
                    'amount_currency': balance_in_currency,
                }, {'journal_id': new_journal.id, 'period_id':period.id})

    #validate and centralize the opening move
    obj_acc_move.validate(cr, uid, [move_id], context=context)

    #reconcile all the move.line of the opening move
    ids = obj_acc_move_line.search(cr, uid, [('journal_id','=',new_journal.id),
        ('period_id.fiscalyear_id','=',new_fyear.id)])
    context['fy_closing'] = True
    if ids:
        obj_acc_move_line.reconcile(cr, uid, ids, context=context)

    #create the journal.period object and link it to the old fiscalyear
    new_period = data['form']['period_id']
    ids = obj_acc_journal_period.search(cr, uid, [('journal_id','=',new_journal.id),('period_id','=',new_period)])
    if not ids:
        ids = [obj_acc_journal_period.create(cr, uid, {
               'name': (new_journal.name or '')+':'+(period.code or ''),
               'journal_id': new_journal.id,
               'period_id': period.id
           })]
    cr.execute('UPDATE account_fiscalyear ' \
                'SET end_journal_period_id = %s ' \
                'WHERE id = %s', (ids[0], old_fyear.id))

    return {'type': 'ir.actions.act_window_close'}


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

