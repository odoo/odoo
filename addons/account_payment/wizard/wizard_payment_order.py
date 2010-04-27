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
import pooler
from tools.misc import UpdateableStr
import time


FORM = UpdateableStr()

FIELDS = {
    'entries': {'string':'Entries', 'type':'many2many',
        'relation': 'account.move.line',},
}
field_duedate={
    'duedate': {'string':'Due Date', 'type':'date','required':True, 'default': lambda *a: time.strftime('%Y-%m-%d'),},
    }
arch_duedate='''<?xml version="1.0"?>
<form string="Search Payment lines">
    <field name="duedate" />
</form>'''


def search_entries(self, cr, uid, data, context):
    search_due_date=data['form']['duedate']

    pool = pooler.get_pool(cr.dbname)
    order_obj = pool.get('payment.order')
    line_obj = pool.get('account.move.line')

    payment = order_obj.browse(cr, uid, data['id'],
            context=context)
    ctx = ''
    if payment.mode:
        ctx = '''context="{'journal_id': %d}"''' % payment.mode.journal.id

    # Search for move line to pay:
    domain = [('reconcile_id', '=', False),('account_id.type', '=', 'payable'),('amount_to_pay', '>', 0)]
    domain = domain + ['|',('date_maturity','<=',search_due_date),('date_maturity','=',False)]
    line_ids = line_obj.search(cr, uid, domain, context=context)
    FORM.string = '''<?xml version="1.0"?>
<form string="Populate Payment:">
    <field name="entries" colspan="4" height="300" width="800" nolabel="1"
        domain="[('id', 'in', [%s])]" %s/>
</form>''' % (','.join([str(x) for x in line_ids]), ctx)
    return {}

def create_payment(self, cr, uid, data, context):
    line_ids= data['form']['entries'][0][2]
    if not line_ids: return {}

    pool= pooler.get_pool(cr.dbname)
    order_obj = pool.get('payment.order')
    line_obj = pool.get('account.move.line')

    payment = order_obj.browse(cr, uid, data['id'],
            context=context)
    t = payment.mode and payment.mode.type.id or None
    line2bank = pool.get('account.move.line').line2bank(cr, uid,
            line_ids, t, context)

    ## Finally populate the current payment with new lines:
    for line in line_obj.browse(cr, uid, line_ids, context=context):
        if payment.date_prefered == "now":
            #no payment date => immediate payment
            date_to_pay = False
        elif payment.date_prefered == 'due':
            date_to_pay = line.date_maturity
        elif payment.date_prefered == 'fixed':
            date_to_pay = payment.date_planned
        pool.get('payment.line').create(cr,uid,{
            'move_line_id': line.id,
            'amount_currency': line.amount_to_pay,
            'bank_id': line2bank.get(line.id),
            'order_id': payment.id,
            'partner_id': line.partner_id and line.partner_id.id or False,
            'communication': line.ref or '/',
            'date': date_to_pay,
            'currency': line.invoice and line.invoice.currency_id.id or False,
            }, context=context)
    return {}


class wizard_payment_order(wizard.interface):
    """
    Create a payment object with lines corresponding to the account move line
    to pay according to the date and the mode provided by the user.
    Hypothesis:
    - Small number of non-reconcilied move line , payment mode and bank account type,
    - Big number of partner and bank account.

    If a type is given, unsuitable account move lines are ignored.
    """
    states = {

        'init': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': arch_duedate,
                'fields':field_duedate,
                'state': [
                    ('end','_Cancel'),
                    ('search','_Search', '', True)
                ]
            },
         },

        'search': {
            'actions': [search_entries],
            'result': {
                'type': 'form',
                'arch': FORM,
                'fields': FIELDS,
                'state': [
                    ('end','_Cancel'),
                    ('create','_Add to payment order', '', True)
                ]
            },
         },
        'create': {
            'actions': [],
            'result': {
                'type': 'action',
                'action': create_payment,
                'state': 'end'}
            },
        }

wizard_payment_order('populate_payment')



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

