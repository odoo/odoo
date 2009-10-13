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
import pooler
from tools.misc import UpdateableStr

FORM = UpdateableStr()

FIELDS = {
    'lines': {'string': 'Payment Lines', 'type': 'many2many',
        'relation': 'payment.line'},
}

def _search_entries(obj, cursor, user, data, context):
    pool = pooler.get_pool(cursor.dbname)
    line_obj = pool.get('payment.line')
    statement_obj = pool.get('account.bank.statement')

    statement = statement_obj.browse(cursor, user, data['id'], context=context)

    line_ids = line_obj.search(cursor, user, [
        ('move_line_id.reconcile_id', '=', False),
        ('order_id.mode.journal.id', '=', statement.journal_id.id)])
    line_ids.extend(line_obj.search(cursor, user, [
        ('move_line_id.reconcile_id', '=', False),
        ('order_id.mode', '=', False)]))

    FORM.string = '''<?xml version="1.0"?>
<form string="Populate Statement:">
    <field name="lines" colspan="4" height="300" width="800" nolabel="1"
        domain="[('id', 'in', [%s])]"/>
</form>''' % (','.join([str(x) for x in line_ids]))
    return {}

def _populate_statement(obj, cursor, user, data, context):
    line_ids = data['form']['lines'][0][2]
    if not line_ids:
        return {}

    pool = pooler.get_pool(cursor.dbname)
    line_obj = pool.get('payment.line')
    statement_obj = pool.get('account.bank.statement')
    statement_line_obj = pool.get('account.bank.statement.line')
    currency_obj = pool.get('res.currency')
    statement_reconcile_obj = pool.get('account.bank.statement.reconcile')

    statement = statement_obj.browse(cursor, user, data['id'], context=context)

    for line in line_obj.browse(cursor, user, line_ids, context=context):
        ctx = context.copy()
        ctx['date'] = line.ml_maturity_date # was value_date earlier,but this field exists no more now
        amount = currency_obj.compute(cursor, user, line.currency.id,
                statement.currency.id, line.amount_currency, context=ctx)

        if line.move_line_id:
            reconcile_id = statement_reconcile_obj.create(cursor, user, {
                'line_ids': [(6, 0, [line.move_line_id.id])]
                }, context=context)
            statement_line_obj.create(cursor, user, {
                'name': line.order_id.reference or '?',
                'amount': - amount,
                'type': 'supplier',
                'partner_id': line.partner_id.id,
                'account_id': line.move_line_id.account_id.id,
                'statement_id': statement.id,
                'ref': line.communication,
                'reconcile_id': reconcile_id,
                }, context=context)
    return {}


class PopulateStatement(wizard.interface):
    """
    Populate the current statement with selected payement lines
    """
    states = {
        'init': {
            'actions': [_search_entries],
            'result': {
                'type': 'form',
                'arch': FORM,
                'fields': FIELDS,
                'state': [
                    ('end', '_Cancel'),
                    ('add', '_Add', '', True)
                ]
            },
        },
        'add': {
            'actions': [],
            'result': {
                'type': 'action',
                'action': _populate_statement,
                'state': 'end'
            },
        },
    }

PopulateStatement('populate_statement')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

