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

class purchase_config_settings(osv.osv_memory):
    _name = 'purchase.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'default_invoice_method': fields.selection(
            [('manual', 'Based on Purchase Order Lines'),
             ('picking', 'Based on Receptions'),
             ('order', 'Pre-Generate Draft Invoices based on Purchase Orders'),
            ], 'Invoicing Method', required=True, default_model='purchase.order'),
        'module_purchase_analytic_plans': fields.boolean('Purchase analytic plan',
            help ="""Allows the user to maintain several analysis plans. These let you split
                lines on a purchase order between several accounts and analytic plans.
                This installs the module purchase_analytic_plans."""),
        'module_warning': fields.boolean("Alerts by products or supplier",
            help="""To trigger warnings in OpenERP objects.
                Warning messages can be displayed for objects like sale order, purchase order, picking and invoice.
                This installs the module warning."""),
        'module_product_manufacturer': fields.boolean("Define a manufacturer of products",
            help="""This allows you to define the following for a product:
                    * Manufacturer
                    * Manufacturer Product Name
                    * Manufacturer Product Code
                    * Product Attributes.
                This installs the module product_manufacturer."""),
        'module_purchase_double_validation': fields.boolean("Configure limit amount",
            help="""Provide a double validation mechanism for purchases exceeding minimum amount.
                This installs the module purchase_double_validation."""),
        'module_purchase_requisition': fields.boolean("Track the best price with Purchase Requisition",
            help="""When a purchase order is created, you have the opportunity to save the related requisition.
                This object regroups and allows you to keep track and order all your purchase orders.
                This installs the module purchase_requisition."""),
        'tax_policy': fields.selection(
            [('no_tax', 'No Tax'), ('global_on_order', 'Global On Order'), ('on_order_line', 'On Order Lines')],
            'Taxes', required=True,
            help="""Choose between either applying global taxes on a purchase order, or applying different taxes on purchase order lines, or applying no tax at all."""),
        'group_purchase_taxes_global_on_order':fields.boolean("Global on order",
            implied_group='base.group_purchase_taxes_global_on_order'),
        'group_purchase_taxes_on_order_line':fields.boolean("On order line",
            implied_group='base.group_purchase_taxes_on_order_line'),
    }

    def default_get(self, cr, uid, fields, context=None):
        res = super(purchase_config_settings, self).default_get(cr, uid, fields, context)
        res['tax_policy'] = \
            (res.get('group_purchase_taxes_global_on_order') and 'global_on_order') or \
            (res.get('group_purchase_taxes_on_order_line') and 'on_order_line') or \
            'no_tax'
        return res

    _defaults = {
        'tax_policy': 'global_on_order',
    }

    def onchange_tax_policy(self, cr, uid, ids, tax_policy, context=None):
        return {'value': {
            'group_purchase_taxes_global_on_order': tax_policy == 'global_on_order',
            'group_purchase_taxes_on_order_line': tax_policy == 'on_order_line',
        }}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
