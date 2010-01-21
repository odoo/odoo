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
from decimal import Decimal


def _get_journal(self, cr, uid, context):
    pool = pooler.get_pool(cr.dbname)
    obj = pool.get('account.journal')
    c=pool.get('res.users').browse(cr,uid,uid).company_id.id
    ids = obj.search(cr, uid, [('type', '=', 'cash'), ('company_id', '=', c)])
    res = obj.read(cr, uid, ids, ['id', 'name'], context)
    res = [(r['id'], r['name']) for r in res]
    return res


payment_form = """<?xml version="1.0"?>
<form string="Add payment :">
<group colspan="4" label="Payment">
    <field name="amount" />
    <field name="journal"/>
    <field name="payment_date" />
    <field name="payment_name" />
    <field name="invoice_wanted" />
    <field name="num_sale" />
    <field name="is_acc" />
    <group attrs="{'readonly':[('is_acc','=',False)]}" colspan="4" cols="2">
    <field name="product_id" attrs="{'required':[('is_acc', '=', True)]}" domain="[('type','=','service')]"/>
    </group>
    </group>
</form>
"""

payment_fields = {
    'amount': {'string': 'Amount', 'type': 'float', 'required': True},
    'is_acc': {'string': 'Accompte', 'type': 'boolean'},
    'invoice_wanted': {'string': 'Invoice', 'type': 'boolean'},
    'journal': {'string': 'Journal',
                'type': 'selection',
                'selection': _get_journal,
                'required': True,
               },
    'payment_date': {'string': 'Payment date', 'type': 'date', 'required': True},
    'payment_name': {'string': 'Payment name', 'type': 'char', 'size': '32', 'required':True, 'default':'Payment'},
    'num_sale': {'string': 'Num.File', 'type': 'char', 'size': '32'},
    'product_id': {'string':'Acompte','type': 'many2one', 'relation': 'product.product'},
    }


def _pre_init(self, cr, uid, data, context):
    def _get_journal(pool, order):
        j_obj = pool.get('account.journal')
        c = pool.get('res.users').browse(cr,uid,uid).company_id.id
        journal = j_obj.search(cr, uid, [('type', '=', 'cash'), ('company_id', '=', c)])
        if journal:
            journal = journal[0]
        else:
            journal = None
        return journal

    wf_service = netsvc.LocalService("workflow")
   # wf_service.trg_validate(uid, 'pos.order', data['id'], 'start_payment', cr)

    pool = pooler.get_pool(cr.dbname)
    order = pool.get('pos.order').browse(cr, uid, data['id'], context)
    #get amount to pay
    #amount = Decimal(str(order.amount_total)) - Decimal(str(order.amount_paid))
    amount = order.amount_total - order.amount_paid

    if amount<=0:
        context.update({'flag':True})
        pool.get('pos.order').action_paid(cr,uid,data['ids'],context)
    elif order.amount_paid > 0:
        pool.get('pos.order').write(cr, uid, data['id'],{'state':'advance'})


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
    jrnl_obj = pool.get('account.journal')
    result = data['form']
    invoice_wanted = data['form']['invoice_wanted']
    jrnl_used=False
    if data['form'] and data['form'].get('journal',False):
        jrnl_used=jrnl_obj.browse(cr,uid,data['form']['journal'])

    # add 'invoice_wanted' in 'pos.order'
    order_obj.write(cr, uid, [data['id']], {'invoice_wanted': invoice_wanted})

    order_obj.add_payment(cr, uid, data['id'], result, context=context)
    return {}


def _check(self, cr, uid, data, context):
    """Check the order:
    if the order is not paid: continue payment,
    if the order is paid print invoice (if wanted) or ticket.
    """
    pool = pooler.get_pool(cr.dbname)
    order_obj = pool.get('pos.order')
    order = order_obj.browse(cr, uid, data['id'], context)
    amount = order.amount_total - order.amount_paid
    if amount<=0:
        context.update({'flag':True})
        pool.get('pos.order').action_paid(cr,uid,data['ids'],context)

    action = 'ask_pay'
    if order_obj.test_paid(cr, uid, [data['id']]):
        if order.partner_id:
            if order.invoice_wanted:
                action = 'invoice'
            else:
                action = 'paid'
        elif order.date_payment:
            action = 'receipt'
        else:
            action = 'paid'
    return action


def create_invoice(self, cr, uid, data, context):
    wf_service = netsvc.LocalService("workflow")
    for i in data['ids']:
        wf_service.trg_validate(uid, 'pos.order', i, 'invoice', cr)
    return {}

def _trigger_wkf(self, cr, uid, data, context):
    wf_service = netsvc.LocalService("workflow")
    wf_service.trg_validate(uid, 'pos.order', data['id'], 'payment', cr)
    return {}



class pos_payment(wizard.interface):
    states = {
        'init': {
            'actions': [],
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
                'state': (('end', 'Cancel'), ('finish', 'Finish'), ('add_pay', 'Ma_ke payment', 'gtk-ok', True))
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
                'state': 'finish'
            }
        },
        'receipt': {
            'actions': [],
            'result': {
                'type': 'print',
                'report': 'pos.receipt',
                'state': 'finish'
            }
        },
        'paid': {
            'actions': [],
            'result': {
                'type': 'print',
                'report': 'pos.receipt',
                'state': 'finish'
            }
        },
        'finish': {
            'actions': [_trigger_wkf],
            'result': {
                'type': 'state',
                'state': 'end'
            }
        },

    }

pos_payment('pos.payment')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

