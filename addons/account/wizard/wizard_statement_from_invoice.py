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
        
}
START_FORM = '''<?xml version="1.0"?>
<form string="Import invoices in statement">
    <label string="Choose invoice type and payment date" colspan="4"/>
    <field name="date"/>
</form>'''

def _search_customer_invoices(obj, cursor, user, data, context):
    pool = pooler.get_pool(cursor.dbname)
    line_obj = pool.get('account.move.line')
    statement_obj = pool.get('account.bank.statement')

    statement = statement_obj.browse(cursor, user, data['id'], context=context)
    line_ids = line_obj.search(cursor, user, [
        ('reconcile_id', '=', False),
        ('account_id.type', '=', 'receivable')],
        order='date DESC, id DESC', context=context)

    FORM.string = '''<?xml version="1.0"?>
<form string="Import entries from customer invoice">
    <field name="lines" colspan="4" height="300" width="800" nolabel="1"
        domain="[('id', 'in', [%s])]"/>
</form>''' % (','.join([str(x) for x in line_ids]))
    return {'type':'customer'}
    # return {'lines': line_ids,'type':'customer'}

def _search_supplier_invoices(obj, cursor, user, data, context):
    pool = pooler.get_pool(cursor.dbname)
    line_obj = pool.get('account.move.line')
    statement_obj = pool.get('account.bank.statement')

    statement = statement_obj.browse(cursor, user, data['id'], context=context)
    line_ids = line_obj.search(cursor, user, [
        ('reconcile_id', '=', False),
        ('account_id.type', '=', 'payable')],
        order='date DESC, id DESC', context=context)

    FORM.string = '''<?xml version="1.0"?>
<form string="Import entries from supplier invoice">
    <field name="lines" colspan="4" height="300" width="800" nolabel="1"
        domain="[('id', 'in', [%s])]"/>
</form>''' % (','.join([str(x) for x in line_ids]))
    return {'type':'supplier'}
    # return {'lines': line_ids,'type':'supplier'}
    

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
        if line.amount_currency:
            amount = currency_obj.compute(cursor, user, line.currency_id.id,
                statement.currency.id, line.amount_currency, context=ctx)
        else:
            if line.debit > 0:
                amount=line.debit
            elif line.credit > 0:
                amount=-line.credit
        reconcile_id = statement_reconcile_obj.create(cursor, user, {
            'line_ids': [(6, 0, [line.id])]
            }, context=context)
        statement_line_obj.create(cursor, user, {
            'name': line.name or '?',
            'amount': amount,
            'type': data['form']['type'],
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
                    ('customer', 'C_ustomer invoices', '', True),
                    ('supplier', '_Supplier invoices', '', True)
                ]
            },
        },
        'customer': {
            'actions': [_search_customer_invoices],
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
        'supplier': {
            'actions': [_search_supplier_invoices],
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
PopulateStatementFromInv('populate_payment_from_inv')
