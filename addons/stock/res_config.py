# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

class stock_config_settings(osv.osv_memory):
    _name = 'stock.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'module_stock_no_autopicking': fields.boolean("Force Picking before Manufactoring Orders",
            help="""This module allows an intermediate picking process to provide raw materials to production orders.
                For example to manage production made by your suppliers (sub-contracting).
                To achieve this, set the assembled product which is sub-contracted to "No Auto-Picking"
                and put the location of the supplier in the routing of the assembly operation.
                This installs the module stock_no_autopicking."""),
        'module_claim_from_delivery': fields.boolean("Track Claims from Delivery",
            help="""Adds a Claim link to the delivery order.
                This installs the module claim_from_delivery."""),
        'module_stock_invoice_directly': fields.boolean("Invoice Picking on Delivery",
            help="""This allows to automatically launch the invoicing wizard if the delivery is
                to be invoiced when you send or deliver goods.
                This installs the module stock_invoice_directly."""),
        'module_product_expiry': fields.boolean("Expiry Date on Lots",
            help="""Track different dates on products and production lots.
                The following dates can be tracked:
                    - end of life
                    - best before date
                    - removal date
                    - alert date.
                This installs the module product_expiry."""),
        'module_stock_location': fields.boolean("Push/Pull Logistic Rules",
            help="""Provide push and pull inventory flows.  Typical uses of this feature are:
                manage product manufacturing chains, manage default locations per product,
                define routes within your warehouse according to business needs, etc.
                This installs the module stock_location."""),
        'group_uom': fields.boolean("Allow Different UoM per Product",
            implied_group='product.group_uom',
            help="""Allows you to select and maintain different unit of measures per product."""),
        'group_uos': fields.boolean("Manage Secondary UoM on Products (for Sale)",
            implied_group='product.group_uos',
            help="""Allows you to sell units of a product, but invoice following a different UoM.
                For instance, you can sell pieces of meat that you invoice per their weight."""),
        'group_stock_packaging': fields.boolean("Manage Product Packaging",
            implied_group='product.group_stock_packaging',
            help="""Allows you to create and manage your packaging dimensions and types you want to be maintained in your system."""),
        'group_stock_production_lot': fields.boolean("Serial Numbers on Products",
            implied_group='stock.group_production_lot',
            help="""This allows you to manage products by using serial numbers.
                When you select a lot, you can get the upstream or downstream traceability of the products contained in lot."""),
        'group_stock_tracking_lot': fields.boolean("Serial Numbers on Palets (Logistic Units)",
            implied_group='stock.group_tracking_lot',
            help="""Allows you to get the upstream or downstream traceability of the products contained in lot."""),
        'group_stock_inventory_valuation': fields.boolean("Accounting Entries per Stock Movement",
            implied_group='stock.group_inventory_valuation',
            help="""This allows to split stock inventory lines according to production lots."""),
        'group_stock_multiple_locations': fields.boolean("Manage Multiple Locations and Warehouses",
            implied_group='stock.group_locations',
            help="""This allows to configure and use multiple stock locations and warehouses,
                instead of having a single default one."""),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
