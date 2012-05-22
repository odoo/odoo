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
        'module_claim_from_delivery': fields.boolean("Allow Claims on Delivery Orders",
            help="""Adds a Claim link to the delivery order.
                This installs the module claim_from_delivery."""),
        'module_stock_invoice_directly': fields.boolean("Invoice Directly from the Picking",
            help="""This allows to automatically launch the invoicing wizard if the delivery is
                to be invoiced when you send or deliver goods.
                This installs the module stock_invoice_directly."""),
        'module_product_expiry': fields.boolean("Expiry Date on Lots",
            help="""Track different dates on products and serial numbers.
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
        'group_uom': fields.boolean("Manage Different Units of Measure for Products",
            implied_group='product.group_uom',
            help="""Allows you to select and maintain different units of measure for products."""),
        'group_uos': fields.boolean("Manage Secondary Unit of Measure (for Sale)",
            implied_group='product.group_uos',
            help="""Allows you to sell units of a product, but invoice based on a different unit of measure.
                For instance, you can sell pieces of meat that you invoice based on their weight."""),
        'group_stock_packaging': fields.boolean("Manage Product Packaging",
            implied_group='product.group_stock_packaging',
            help="""Allows you to create and manage your packaging dimensions and types you want to be maintained in your system."""),
        'group_stock_production_lot': fields.boolean("Serial Numbers on Products",
            implied_group='stock.group_production_lot',
            help="""This allows you to manage products by using serial numbers.
                When you select a lot, you can get the upstream or downstream traceability of the products contained in lot."""),
        'group_stock_tracking_lot': fields.boolean("Serial Numbers on Logistic Units (Pallets)",
            implied_group='stock.group_tracking_lot',
            help="""Allows you to get the upstream or downstream traceability of the products contained in lot."""),
        'group_stock_inventory_valuation': fields.boolean("Generate Accounting Entries per Stock Movement",
            implied_group='stock.group_inventory_valuation',
            help="""This allows to split stock inventory lines according to serial numbers."""),
        'group_stock_multiple_locations': fields.boolean("Manage Multiple Locations and Warehouses",
            implied_group='stock.group_locations',
            help="""This allows to configure and use multiple stock locations and warehouses,
                instead of having a single default one."""),
        'group_product_variant': fields.boolean("Product Variant",
            implied_group='product.group_product_variant',
            help="""This allows to configure and use Product Variant."""),                
        'decimal_precision': fields.integer('Decimal Precision on Weight'),
    }

    def get_default_dp(self, cr, uid, fields, context=None):
        dp = self.pool.get('ir.model.data').get_object(cr, uid, 'product', 'decimal_stock_weight')
        return {'decimal_precision': dp.digits}

    def set_default_dp(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context)
        dp = self.pool.get('ir.model.data').get_object(cr, uid, 'product', 'decimal_stock_weight')
        dp.write({'digits': config.decimal_precision})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
