# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import fields, osv
import pooler
from tools.translate import _

class purchase_configuration(osv.osv_memory):
    _inherit = 'res.config.settings'

    _columns = {
        'default_method' : fields.selection(
            [('manual', 'Based on Purchase Order Lines'),
             ('picking', 'Based on Receptions'),
             ('order', 'Pre-Generate Draft Invoices based on Purchase Orders'),
            ], 'Invoicing Control Method', required=True , help="You can set Invoicing Control Method."),
        'module_purchase_analytic_plans': fields.boolean('Purchase Analytic Plan',
                                   help ="""
                                   Allows the user to maintain several analysis plans. These let you split
                                   a line on a supplier purchase order into several accounts and analytic plans.
                                   It installs the purchase_analytic_plans module.
                                   """),
        'module_warning': fields.boolean("Alerts by products or customers",
                                  help="""To trigger warnings in OpenERP objects.
                                  Warning messages can be displayed for objects like sale order, purchase order, picking and invoice. The message is triggered by the form's onchange event.
                                  It installs the warning module."""),
        'module_product_manufacturer': fields.boolean("Define a manufacturer on products",
                        help="""TYou can now define the following for a product:
                            * Manufacturer
                            * Manufacturer Product Name
                            * Manufacturer Product Code
                            * Product Attributes.
                        It installs the product_manufacturer module."""),
        'module_purchase_double_validation': fields.boolean("Configure Limit amount",
                        help="""This allows you double-validation for purchases exceeding minimum amount.
                        It installs the purchase_double_validation module."""),
        'module_purchase_requisition' : fields.boolean("Track the best price with Purchase Requisition",
                                    help="""When a purchase order is created, you now have the opportunity to save the related requisition.
                                    This new object will regroup and will allow you to easily keep track and order all your purchase orders.
                                    It Installs purchase_requisition module."""),
        'tax_policy': fields.selection([
                ('no_tax', 'No Tax'),
                ('global_on_order', 'Global On Order'),
                ('on_order_line', 'On Order Lines'),
            ], 'Taxes', required=True,
            help="""
                If you want to apply global tax on sale order then select 'Global On Order' it will add 'Global On Order' group to employees.
                If you want to apply different taxes for sale order lines then select 'On Order Lines' it will add 'On Order Lines' group to employees.
            """),
        'group_purchase_taxes_global_on_order':fields.boolean("Global on order", group='base.group_user', implied_group='base.group_purchase_taxes_global_on_order'),
        'group_purchase_taxes_on_order_line':fields.boolean("On order line", group='base.group_user', implied_group='base.group_purchase_taxes_on_order_line'),
    }

    _defaults = {
        'default_method': lambda s,c,u,ctx: s.pool.get('purchase.order').default_get(c,u,['invoice_method'],context=ctx)['invoice_method'],
        'tax_policy': 'global_on_order',
    }

    def _check_default_tax(self, cr, uid, context=None):
        ir_values_obj = self.pool.get('ir.values')
        for tax in ir_values_obj.get(cr, uid, 'default', False, ['product.product']):
            if tax[1] == 'taxes_id':
                return tax[2]
        return False

    def set_default_taxes(self, cr, uid, ids, context=None):
        ir_values_obj = self.pool.get('ir.values')
        taxes = self._check_default_tax(cr, uid, context=context)
        if taxes:
            ir_values_obj.set(cr, uid, 'default', False, 'tax_id', ['purchase.order'], taxes[0])
            ir_values_obj.set(cr, uid, 'default', False, 'tax_id', ['purchase.order.line'], taxes)
            ir_values_obj.set(cr, uid, 'default', False, 'taxes_id', ['product.product'], taxes)

    def onchange_tax_policy(self, cr, uid, ids, tax_policy, context=None):
        res = {'value': {}}
        if ids:
            self.set_tax_policy(cr, uid, ids, context=context)
        if tax_policy == 'global_on_order':
            res['value'].update({'group_purchase_taxes_global_on_order': True})
            res['value'].update({'group_purchase_taxes_on_order_line': False})

        elif tax_policy == 'on_order_line':
            res['value'].update({'group_purchase_taxes_on_order_line': True})
            res['value'].update({'group_purchase_taxes_global_on_order': False})
        else:
            res['value'].update({'group_purchase_taxes_on_order_line': False, 'group_purchase_taxes_global_on_order': False})
        return res

purchase_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: