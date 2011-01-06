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
from osv import fields, osv
from tools.translate import _

form = """<?xml version="1.0"?>
<form string="Advance Payment">
    <field name="product_id"/>
    <newline />
    <field name="qtty"/>
    <field name="amount"/>
    <newline />
</form>
"""
fields = {
        'product_id': {'string':'Product', 'type':'many2one','relation':'product.product','required':True},
        'amount': {'string':'Unit Price', 'type':'float', 'size':(16,2),'required':True},
        'qtty': {'string':'Quantity', 'type':'float', 'size':(16,2),'required':True, 'default': lambda *a: 1},
}

form_msg = """<?xml version="1.0"?>
<form string="Invoices">
   <label string="You invoice has been successfully created !"/>
</form>
"""
fields_msg = {}

def _createInvoices(self, cr, uid, data, context={}):
    list_inv = []
    pool_obj = pooler.get_pool(cr.dbname)
    obj_sale = pool_obj.get('sale.order')
    data_sale = obj_sale.browse(cr,uid,data['ids'])
    obj_lines = pool_obj.get('account.invoice.line')
    for sale in data_sale:
        address_contact = False
        address_invoice = False
        create_ids = []
        ids_inv = []
        if sale.order_policy == 'postpaid':
            raise osv.except_osv(
                _('Error'),
                _("You cannot make an advance on a sale order that is defined as 'Automatic Invoice after delivery'."))
        fpos = sale.fiscal_position and sale.fiscal_position.id or False
        val = obj_lines.product_id_change(cr, uid, [], data['form']['product_id'],uom = False, partner_id = sale.partner_id.id, fposition_id = fpos)
        line_id =obj_lines.create(cr, uid, {
            'name': val['value']['name'],
            'account_id':val['value']['account_id'],
            'price_unit': data['form']['amount'],
            'quantity': data['form']['qtty'],
            'discount': False,
            'uos_id': val['value']['uos_id'],
            'product_id':data['form']['product_id'],
            'invoice_line_tax_id': [(6,0,val['value']['invoice_line_tax_id'])],
            'account_analytic_id': sale.project_id and sale.project_id.id or False,
            'note':'',
        })
        create_ids.append(line_id)
        inv = {
            'name': sale.client_order_ref or sale.name,
            'origin': sale.name,
            'type': 'out_invoice',
            'reference': False,
            'account_id': sale.partner_id.property_account_receivable.id,
            'partner_id': sale.partner_id.id,
            'address_invoice_id':sale.partner_invoice_id.id,
            'address_contact_id':sale.partner_order_id.id,
            'invoice_line': [(6,0,create_ids)],
            'currency_id' :sale.pricelist_id.currency_id.id,
            'comment': '',
            'payment_term':sale.payment_term.id,
            'fiscal_position': fpos or sale.partner_id.property_account_position.id
            }
        inv_obj = pool_obj.get('account.invoice')
        inv_id = inv_obj.create(cr, uid, inv)

        for inv in sale.invoice_ids:
            ids_inv.append(inv.id)
        ids_inv.append(inv_id)
        obj_sale.write(cr,uid,sale.id,{'invoice_ids':[(6,0,ids_inv)]})
        list_inv.append(inv_id)
#
# If invoice on picking: add the cost on the SO
# If not, the advance will be deduced when generating the final invoice
#
        if sale.order_policy=='picking':
            pool_obj.get('sale.order.line').create(cr, uid, {
                'order_id': sale.id,
                'name': val['value']['name'],
                'price_unit': -data['form']['amount'],
                'product_uom_qty': data['form']['qtty'],
                'product_uos_qty': data['form']['qtty'],
                'product_uos': val['value']['uos_id'],
                'product_uom': val['value']['uos_id'],
                'product_id':data['form']['product_id'],
                'discount': False,
                'tax_id': [(6,0,val['value']['invoice_line_tax_id'])],
            }, context)
    return {'invoice_ids':list_inv}

class sale_advance_payment(wizard.interface):
    def _open_invoice(self, cr, uid, data, context):
        pool_obj = pooler.get_pool(cr.dbname)
        model_data_ids = pool_obj.get('ir.model.data').search(cr,uid,[('model','=','ir.ui.view'),('name','=','invoice_form')])
        resource_id = pool_obj.get('ir.model.data').read(cr,uid,model_data_ids,fields=['res_id'])[0]['res_id']
        return {
            'domain': "[('id','in', ["+','.join(map(str,data['form']['invoice_ids']))+"])]",
            'name': 'Invoices',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'views': [(False,'tree'),(resource_id,'form')],
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window'
        }

    states = {
        'init' : {
            'actions' : [],
            'result' : {'type' : 'form' ,   'arch' : form,'fields' : fields,'state' : [('end','Cancel','gtk-cancel'),('create','Create Advance Invoice','gtk-ok')]}
        },
        'create': {
            'actions': [_createInvoices],
            'result': {'type' : 'form' ,'arch' : form_msg,'fields' : fields_msg, 'state':[('end','Close','gtk-close'),('open','Open Advance Invoice','gtk-open')]}
        },
        'open': {
            'actions': [],
            'result': {'type':'action', 'action':_open_invoice, 'state':'end'}
        }
    }

sale_advance_payment("sale.advance_payment_inv")
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

