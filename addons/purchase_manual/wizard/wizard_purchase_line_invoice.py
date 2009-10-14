# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

import wizard
import netsvc
import ir
import pooler

invoice_form = """<?xml version="1.0"?>
<form string="Control invoices">
    <separator colspan="4" string="Do you want to generate the supplier invoices ?" />
</form>
"""

invoice_fields = {
}

def _makeInvoices(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    res = False
    invoices = {}

    def make_invoice(order, lines):
        a = order.partner_id.property_account_payable.id
        if order.partner_id and order.partner_id.property_payment_term.id:
            pay_term = order.partner_id.property_payment_term.id
        else:
            pay_term = False
        inv = {
            'name': order.name,
            'origin': order.name,
            'type': 'in_invoice',
            'reference': "P%dPO%d" % (order.partner_id.id, order.id),
            'account_id': a,
            'partner_id': order.partner_id.id,
            'address_invoice_id': order.partner_address_id.id,
            'address_contact_id': order.partner_address_id.id,
            'invoice_line': [(6,0,lines)],
            'currency_id' : order.pricelist_id.currency_id.id,
            'comment': order.notes,
            'payment_term': pay_term,
            'fiscal_position': order.partner_id.property_account_position.id
        }
        inv_id = pool.get('account.invoice').create(cr, uid, inv)
        return inv_id

    for line in pool.get('purchase.order.line').browse(cr,uid,data['ids']):
        if (not line.invoiced) and (line.state not in ('draft','cancel')):
            if not line.order_id.id in invoices:
                invoices[line.order_id.id] = []
            if line.product_id:
                a = line.product_id.product_tmpl_id.property_account_expense.id
                if not a:
                    a = line.product_id.categ_id.property_account_expense_categ.id
                if not a:
                    raise osv.except_osv(_('Error !'),
                            _('There is no expense account defined ' \
                                    'for this product: "%s" (id:%d)') % \
                                    (line.product_id.name, line.product_id.id,))
            else:
                a = pool.get('ir.property').get(cr, uid,
                        'property_account_expense_categ', 'product.category',
                        context=context)
            fpos = line.order_id.fiscal_position or False
            a = pool.get('account.fiscal.position').map_account(cr, uid, fpos, a)
            inv_id = pool.get('account.invoice.line').create(cr, uid, {
                'name': line.name,
                'origin': line.order_id.name,
                'account_id': a,
                'price_unit': line.price_unit,
                'quantity': line.product_qty,
                'uos_id': line.product_uom.id,
                'product_id': line.product_id.id or False,
                'invoice_line_tax_id': [(6, 0, [x.id for x in line.taxes_id])],
                'note': line.notes,
                'account_analytic_id': line.account_analytic_id and line.account_analytic_id.id or False,
            })
            cr.execute('insert into purchase_order_line_invoice_rel (order_line_id,invoice_id) values (%s,%s)', (line.id, inv_id))
            pool.get('purchase.order.line').write(cr, uid, [line.id], {'invoiced': True})
            invoices[line.order_id.id].append((line,inv_id))

    res = []
    for result in invoices.values():
        order = result[0][0].order_id
        il = map(lambda x: x[1], result)
        res.append(make_invoice(order, il))
    return {'invoice_ids': res}

    return {
        'domain': "[('id','in', ["+','.join(map(str,res))+"])]",
        'name': _('Supplier Invoices'),
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'account.invoice',
        'view_id': False,
        'context': "{'type':'in_invoice'}",
        'type': 'ir.actions.act_window'
    }

class line_make_invoice(wizard.interface):
    def _open_invoice(self, cr, uid, data, context):
        pool_obj = pooler.get_pool(cr.dbname)
        model_data_ids = pool_obj.get('ir.model.data').search(cr,uid,[('model','=','ir.ui.view'),('name','=','invoice_supplier_form')])
        resource_id = pool_obj.get('ir.model.data').read(cr,uid,model_data_ids,fields=['res_id'])[0]['res_id']
        return {
            'domain': "[('id','in', ["+','.join(map(str,data['form']['invoice_ids']))+"])]",
            'name': 'Invoices',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'views': [(False,'tree'),(resource_id,'form')],
            'context': "{'type':'in_invoice'}",
            'type': 'ir.actions.act_window'
        }

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
            'result' : {'type': 'state', 'state': 'open'}
        },
        'open': {
            'actions': [],
            'result': {'type':'action', 'action':_open_invoice, 'state':'end'}
        }
    }

line_make_invoice("purchase.order.line.make_invoice")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

