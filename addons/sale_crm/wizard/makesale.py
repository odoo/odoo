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

from mx.DateTime import now

import wizard
import netsvc
import ir
import pooler
from tools.translate import _

sale_form = """<?xml version="1.0"?>
<form string="Convert to Quote">
    <field name="partner_id" required="True"/>
    <field name="shop_id" required="True"/>
    <field name="analytic_account"/>
    <field name="picking_policy" required="True"/>
    <field name="close"/>
    <newline/>
    <field name="products" colspan="4"/>
</form>"""

sale_fields = {
    'shop_id': {'string': 'Shop', 'type': 'many2one', 'relation': 'sale.shop'},
    'partner_id': {'string': 'Customer', 'type': 'many2one',
        'relation': 'res.partner',
        'help': 'Use this partner if there is no partner on the case'},
    'picking_policy': {'string': 'Packing Policy', 'type': 'selection',
        'selection': [('direct', 'Partial Delivery'), ('one', 'Complete Delivery')]},
    'products': {'string': 'Products', 'type': 'many2many',
        'relation': 'product.product'},
    'analytic_account': {'string': 'Analytic Account', 'type': 'many2one',
        'relation': 'account.analytic.account'},
    'close': {'string': 'Close Case', 'type': 'boolean', 'default': lambda *a: 1,
        'help': 'Check this to close the case after having created the sale order.'},
}


class make_sale(wizard.interface):

    def _selectPartner(self, cr, uid, data, context):
        case_obj = pooler.get_pool(cr.dbname).get('crm.case')
        case = case_obj.read(cr, uid, data['ids'], ['partner_id'])
        return {'partner_id': case[0]['partner_id']}

    def _makeOrder(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        case_obj = pool.get('crm.case')
        sale_obj = pool.get('sale.order')
        partner_obj = pool.get('res.partner')
        sale_line_obj = pool.get('sale.order.line')

        default_partner_addr = partner_obj.address_get(cr, uid, [data['form']['partner_id']],
                ['invoice', 'delivery', 'contact'])
        default_pricelist = partner_obj.browse(cr, uid, data['form']['partner_id'],
                    context).property_product_pricelist.id
        fpos_data = partner_obj.browse(cr, uid, data['form']['partner_id'],context).property_account_position
        new_ids = []

        for case in case_obj.browse(cr, uid, data['ids']):
            if case.partner_id and case.partner_id.id:
                partner_id = case.partner_id.id
                fpos = case.partner_id.property_account_position and case.partner_id.property_account_position.id or False
                partner_addr = partner_obj.address_get(cr, uid, [case.partner_id.id],
                        ['invoice', 'delivery', 'contact'])
                pricelist = partner_obj.browse(cr, uid, case.partner_id.id,
                        context).property_product_pricelist.id
            else:
                partner_id = data['form']['partner_id']
                fpos = fpos_data and fpos_data.id or False
                partner_addr = default_partner_addr
                pricelist = default_pricelist

            if False in partner_addr.values():
                raise wizard.except_wizard(_('Data Insufficient!'),_('Customer has no addresses defined!'))

            vals = {
                'origin': 'CRM:%s' % str(case.id),
                'picking_policy': data['form']['picking_policy'],
                'shop_id': data['form']['shop_id'],
                'partner_id': partner_id,
                'pricelist_id': pricelist,
                'partner_invoice_id': partner_addr['invoice'],
                'partner_order_id': partner_addr['contact'],
                'partner_shipping_id': partner_addr['delivery'],
                'order_policy': 'manual',
                'date_order': now(),
                'fiscal_position': fpos,
            }

            if partner_id:
                partner = partner_obj.browse(cr, uid, partner_id, context=context)
                vals['user_id'] = partner.user_id and partner.user_id.id or uid

            if data['form']['analytic_account']:
                vals['project_id'] = data['form']['analytic_account']

            vals.update( sale_obj.onchange_partner_id(cr, uid, [], partner_id).get('value',{}) )
            new_id = sale_obj.create(cr, uid, vals)
            for product_id in data['form']['products'][0][2]:
                value = {
                    'price_unit': 0.0,
                    'product_id': product_id,
                    'order_id': new_id,
                }
                value.update( sale_line_obj.product_id_change(cr, uid, [], pricelist,
                        product_id, qty=1, partner_id=partner_id, fiscal_position=fpos)['value'] )
                value['tax_id'] = [(6,0,value['tax_id'])]
                sale_line_obj.create(cr, uid, value)

            case_obj.write(cr, uid, [case.id], {'ref': 'sale.order,%s' % new_id})
            new_ids.append(new_id)

        if data['form']['close']:
            case_obj.case_close(cr, uid, data['ids'])

        value = {
            'domain': str([('id', 'in', new_ids)]),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
        return value

    states = {
        'init': {
            'actions': [_selectPartner],
            'result': {'type': 'form', 'arch': sale_form, 'fields': sale_fields,
                'state' : [('end', 'Cancel', 'gtk-cancel'),('order', 'Create Quote', 'gtk-go-forward')]}
        },
        'order': {
            'actions': [],
            'result': {'type': 'action', 'action': _makeOrder, 'state': 'end'}
        }
    }

make_sale('crm.case.make_order')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
