# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008 Camptocamp SA All Rights Reserved. (JGG)
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import wizard
import pooler
from tools.misc import UpdateableStr
import time

FORM = UpdateableStr()

FIELDS = {
    'lines': {'string': 'Invoices', 'type': 'many2many',
        'relation': 'account.move.line'},
        
}

START_FIELD = {
    'date': {'string': 'Date payment', 'type': 'date','required':True, 'default': lambda *a: time.strftime('%Y-%m-%d')},
    'journal_ids': {'string': 'Journal', 'type': 'many2many', 'relation': 'account.journal', 'domain': '[("type","in",["sale","purchase","cash"])]', 'help': 'This field allow you to choose the accounting journals you want for filtering the invoices. If you left this field empty, it will search on all sale, purchase and cash journals.'},
}

START_FORM = '''<?xml version="1.0"?>
<form string="Import Invoices in Statement">
    <label string="Choose Journal and Payment Date" colspan="4"/>
    <field name="date"/>
    <field name="journal_ids" colspan="4"/>
</form>'''

def _search_invoices(obj, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    line_obj = pool.get('account.move.line')
    statement_obj = pool.get('account.bank.statement')
    journal_obj = pool.get('account.journal')

    statement = statement_obj.browse(cr, uid, data['id'], context=context)
    args_move_line = []
    repeated_move_line_ids = []
    # Creating a group that is unique for importing move lines(move lines, once imported into statement lines, should not appear again)
    for st_line in statement.line_ids:
        args_move_line = []
        args_move_line.append(('name','=', st_line.name))
        args_move_line.append(('ref','=',st_line.ref))
        if st_line.partner_id:
            args_move_line.append(('partner_id','=',st_line.partner_id.id))
        args_move_line.append(('account_id','=',st_line.account_id.id))
        
        move_line_id = line_obj.search(cr, uid, args_move_line,context=context)
        if move_line_id:
            repeated_move_line_ids += move_line_id
        
    journal_ids = data['form']['journal_ids'][0][2]

    if journal_ids == []:
        journal_ids = journal_obj.search(cr, uid, [('type', 'in', ('sale','cash','purchase'))], context=context)
    
    args = [
        ('reconcile_id', '=', False),
        ('journal_id', 'in', journal_ids),
        ('account_id.reconcile', '=', True)]
    
    if repeated_move_line_ids:
        args.append(('id','not in',repeated_move_line_ids))
           
    line_ids = line_obj.search(cr, uid, args,
        #order='date DESC, id DESC', #doesn't work
        context=context)
        
    FORM.string = '''<?xml version="1.0"?>
<form string="Import Entries">
    <field name="lines" colspan="4" height="300" width="800" nolabel="1"
        domain="[('id', 'in', [%s])]"/>
</form>''' % (','.join([str(x) for x in line_ids]))
    return {}

def _populate_statement(obj, cursor, user, data, context):
    line_ids = data['form']['lines'][0][2]
    line_date=data['form']['date']
    if not line_ids:
        return {}

    pool = pooler.get_pool(cursor.dbname)
    line_obj = pool.get('account.move.line')
    statement_obj = pool.get('account.bank.statement')
    statement_line_obj = pool.get('account.bank.statement.line')
    currency_obj = pool.get('res.currency')
    statement_reconcile_obj = pool.get('account.bank.statement.reconcile')

    statement = statement_obj.browse(cursor, user, data['id'], context=context)
    # for each selected move lines
    for line in line_obj.browse(cursor, user, line_ids, context=context):
        ctx = context.copy()
        #  take the date for computation of currency => use payment date
        # if line.date_maturity:
        #     ctx['date'] = line.date_maturity 
        # else:
        ctx['date'] = line_date
        amount = 0.0
        
        if line.debit > 0:
            amount = line.debit
        elif line.credit > 0:
            amount = -line.credit
                
        if line.amount_currency:
            amount = currency_obj.compute(cursor, user, line.currency_id.id,
                statement.currency.id, line.amount_currency, context=ctx)
        elif (line.invoice and line.invoice.currency_id.id <> statement.currency.id):
            amount = currency_obj.compute(cursor, user, line.invoice.currency_id.id,
                statement.currency.id, amount, context=ctx)
            
            
        reconcile_id = statement_reconcile_obj.create(cursor, user, {
            'line_ids': [(6, 0, [line.id])]
            }, context=context)
        if line.journal_id.type == 'sale':
            type = 'customer'
        elif line.journal_id.type == 'purchase':
            type = 'supplier'
        else:
            type = 'general'
        
        statement_line_obj.create(cursor, user, {
            'name': line.name or '?',
            'amount': amount,
            'type': type,
            'partner_id': line.partner_id.id,
            'account_id': line.account_id.id,
            'statement_id': statement.id,
            'ref': line.ref,
            'reconcile_id': reconcile_id,
            'date':line_date, #time.strftime('%Y-%m-%d'), #line.date_maturity or,
            }, context=context)
    return {}
    
    
class PopulateStatementFromInv(wizard.interface):
    """
    Populate the current statement with selected invoices
    """
    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': START_FORM,
                'fields':START_FIELD,
                'state': [
                    ('end', '_Cancel'),
                    ('go', '_Go', '', True),
                ]
            },
        },
        'go': {
            'actions': [_search_invoices],
            'result': {
                'type': 'form',
                'arch': FORM,
                'fields': FIELDS,
                'state': [
                    ('end', '_Cancel','', True),
                    ('finish', 'O_k','', True)
                ]
            },
        },

        'finish': {
        'actions': [],
        'result': {
            'type': 'action',
            'action': _populate_statement,
            'state': 'end'
        },
    },
    }
PopulateStatementFromInv('populate_statement_from_inv')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
