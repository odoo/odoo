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
import ir
import pooler
from tools.translate import _

invoice_form = """<?xml version="1.0"?>
<form string="Create invoices">
    <separator colspan="4" string="Do you really want to create the invoice(s) ?" />
</form>
"""

invoice_fields = {}

def _makeInvoices(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    res = False
    invoices = {}

    #TODO: merge with sale.py/make_invoice
    def make_invoice(order, lines):
        a = order.partner_id.property_account_receivable.id
        if order.partner_id and order.partner_id.property_payment_term.id:
            pay_term = order.partner_id.property_payment_term.id
        else:
            pay_term = False
        inv = {
            'name': order.name,
            'origin': order.name,
            'type': 'out_invoice',
            'reference': "P%dSO%d" % (order.partner_id.id, order.id),
            'account_id': a,
            'partner_id': order.partner_id.id,
            'address_invoice_id': order.partner_invoice_id.id,
            'address_contact_id': order.partner_invoice_id.id,
            'invoice_line': [(6,0,lines)],
            'currency_id' : order.pricelist_id.currency_id.id,
            'comment': order.note,
            'payment_term': pay_term,
            'fiscal_position': order.fiscal_position.id or order.partner_id.property_account_position.id
        }
        inv_id = pool.get('account.invoice').create(cr, uid, inv)
        return inv_id

    for line in pool.get('sale.order.line').browse(cr,uid,data['ids']):
        if (not line.invoiced) and (line.state not in ('draft','cancel')):
            if not line.order_id.id in invoices:
                invoices[line.order_id.id] = []
            line_id = pool.get('sale.order.line').invoice_line_create(cr, uid,
                    [line.id])
            for lid in line_id:
                invoices[line.order_id.id].append((line, lid))
            pool.get('sale.order.line').write(cr, uid, [line.id],
                    {'invoiced': True})
        flag = True
        data_sale = pool.get('sale.order').browse(cr,uid,line.order_id.id)
        for line in data_sale.order_line:
            if not line.invoiced:
                flag = False
                break
        if flag:
            wf_service = netsvc.LocalService('workflow')
            wf_service.trg_validate(uid, 'sale.order', line.order_id.id, 'all_lines', cr)
            pool.get('sale.order').write(cr,uid,[line.order_id.id],{'state' : 'progress'})
    
    if not invoices:
         raise wizard.except_wizard(_('Warning'),_('Invoice cannot be created for this Sale Order Line due to one of the following reasons:\n1.The state of this sale order line is either "draft" or "cancel"!\n2.The Sale Order Line is Invoiced!'))
    
    for result in invoices.values():
        order = result[0][0].order_id
        il = map(lambda x: x[1], result)
        res = make_invoice(order, il)
        cr.execute('INSERT INTO sale_order_invoice_rel \
                (order_id,invoice_id) values (%s,%s)', (order.id, res))
    return {}


class line_make_invoice(wizard.interface):
    states = {
        'init' : {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': invoice_form,
                'fields': invoice_fields,
                'state': [
                    ('end', 'Cancel'),
                    ('invoice', 'Create invoices')
                ]
            }
        },
        'invoice' : {
            'actions' : [_makeInvoices],
            'result' : {'type': 'state', 'state': 'end'}
        },
    }

line_make_invoice("sale.order.line.make_invoice")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

