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
    }

    _defaults = {
        'default_method': lambda s,c,u,ctx: s.pool.get('purchase.order').default_get(c,u,['invoice_method'],context=ctx)['invoice_method'],
    }

purchase_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: