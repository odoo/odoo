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
        'group_purchase_pricelist':fields.boolean("Pricelist per Supplier",
            implied_group='product.group_purchase_pricelist',
            help="""Allows to manage different prices based on rules per category of Supplier.
                Example: 10% for retailers, promotion of 5 EUR on this product, etc."""),
        'group_uom':fields.boolean("Allow different UoM per product",
            implied_group='product.group_uom',
            help="""Allows you to select and maintain different unit of measures per product."""),
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
    }

    _defaults = {
        'default_invoice_method': 'manual',
    }



class account_config_settings(osv.osv_memory):
    _inherit = 'account.config.settings'
    _columns = {
        'group_analytic_account_for_purchases': fields.boolean('Analytic Accounting for Purchases',
            implied_group='purchase.group_analytic_accounting',
            help="Allows you to specify an analytic account on purchase orders."),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
