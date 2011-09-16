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

import pooler
import netsvc
import wizard
import time
from tools.translate import _


def _get_journal(self, cr, uid, context):
    pool = pooler.get_pool(cr.dbname)
    obj = pool.get('account.journal')
    ids = obj.search(cr, uid, [('type', '=', 'cash')])
    res = obj.read(cr, uid, ids, ['id', 'name'], context)
    res = [(r['id'], r['name']) for r in res]
    return res


payment_form = """<?xml version="1.0"?>
<form string="Add payment :">
    <field name="amount" />
    <field name="journal"/>
    <field name="payment_id" />
    <field name="payment_date" />
    <field name="payment_nb" />
    <field name="payment_name" />
    <field name="invoice_wanted" />
</form>
"""

payment_fields = {
    'amount': {'string': 'Amount', 'type': 'float', 'required': True},
    'invoice_wanted': {'string': 'Invoice', 'type': 'boolean'},
    'journal': {'string': 'Journal',
            'type': 'selection',
            'selection': _get_journal,
            'required': True,
        },
    'payment_id': {'string': 'Payment Term', 'type': 'many2one', 'relation': 'account.payment.term', 'required': True},
    'payment_date': {'string': 'Payment date', 'type': 'date', 'required': True},
    'payment_name': {'string': 'Payment name', 'type': 'char', 'size': '32'},
    'payment_nb': {'string': 'Piece number', 'type': 'char', 'size': '32'},
    }


def _pre_init(self, cr, uid, data, context):

    def _get_journal(pool, order):
        j_obj = pool.get('account.journal')

        journal_to_fetch = 'DEFAULT'
        if order.amount_total < 0:
            journal_to_fetch = 'GIFT'
        else:
            if order.amount_paid > 0:
                journal_to_fetch = 'REBATE'

        pos_config_journal = pool.get('pos.config.journal')
        ids = pos_config_journal.search(cr, uid, [('code', '=', journal_to_fetch)])
        objs = pos_config_journal.browse(cr, uid, ids)
        journal = None
        if objs:
            journal = objs[0].journal_id.id
        else:
            existing = [payment.journal_id.id for payment in order.payments]
            ids = j_obj.search(cr, uid, [('type', '=', 'cash')])
            for i in ids:
                if i not in existing:
                    journal = i
                    break
            if not journal:
                journal = ids[0]

        return journal

    pool = pooler.get_pool(cr.dbname)
    order = pool.get('pos.order').browse(cr, uid, data['id'], context)

    # get amount to pay:
    amount = order.amount_total - order.amount_paid

    # get journal:
    journal = _get_journal(pool, order)

    # check if an invoice is wanted:
    #invoice_wanted_checked = not not order.partner_id # not not -> boolean
    invoice_wanted_checked = False

    # select the current date
    current_date = time.strftime('%Y-%m-%d')

    return {'journal': journal, 'amount': amount, 'invoice_wanted': invoice_wanted_checked, 'payment_date': current_date}


def _add_pay(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    order_obj = pool.get('pos.order')
    result = data['form']
    invoice_wanted = data['form']['invoice_wanted']
    # add 'invoice_wanted' in 'pos.order'
    order_obj.write(cr, uid, [data['id']], {'invoice_wanted': invoice_wanted})

    order_obj.add_payment(cr, uid, data['id'], result, context=context)
    return {}


def _validate(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    order_obj = pool.get('pos.order')
    order = order_obj.browse(cr, uid, data['id'], context)
#    if not order.amount_total:
#       return 'receipt'
    order_obj.test_order_lines(cr, uid, order, context=context)
    return {}


def _check(self, cr, uid, data, context):
    """Check the order:
    if the order is not paid: continue payment,
    if the order is paid print invoice (if wanted) or ticket.
    """
    pool = pooler.get_pool(cr.dbname)
    order_obj = pool.get('pos.order')
    order = order_obj.browse(cr, uid, data['id'], context)
    action = 'ask_pay'
    if order.state == 'paid':
        if order.partner_id:
            if order.invoice_wanted:
                action = 'invoice'
            else:
                action = 'paid'
        else:
            action = 'receipt'
    return action


def _test_no_line(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    order = pool.get('pos.order').browse(cr, uid, data['id'], context)

    if not order.lines:
        raise wizard.except_wizard(_('Error'), _('No order lines defined for this sale.'))

    return {}


def create_invoice(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    order_obj = pool.get('pos.order')
    order = order_obj.browse(cr, uid, data['id'], context)
    if not order.invoice_id:
        order_obj.invoice_action_done(cr, uid, [data['id']])
    return {}


class pos_payment(wizard.interface):
    states = {
        'init': {
            'actions': [_validate],
            'result': {
                'type': 'choice',
                'next_state': _check,
            }
        },
        'ask_pay': {
            'actions': [_pre_init],
            'result': {
                'type': 'form',
                'arch': payment_form,
                'fields': payment_fields,
                'state': (('end', 'Cancel'), ('add_pay', 'Ma_ke payment', 'gtk-ok', True)
                         )
            }
        },
        'add_pay': {
            'actions': [_add_pay],
            'result': {
                'type': 'state',
                'state': "init",
            }
        },
        'invoice': {
            'actions': [create_invoice],
            'result': {
                'type': 'print',
                'report': 'pos.invoice',
                'state': 'end'
            }
        },
        'receipt': {
            'actions': [],
            'result': {
                'type': 'print',
                'report': 'pos.receipt',
                'state': 'end'
            }
        },
        'paid': {
            'actions': [],
            'result': {
                'type': 'state',
                'state': 'end'
            }
        },

    }

pos_payment('pos.payment')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

