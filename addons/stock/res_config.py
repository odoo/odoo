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

class warehouse_configuration(osv.osv_memory):
    _name = 'warehouse.configuration'
    _inherit = 'res.config.settings'

    _columns = {
        'module_stock_no_autopicking': fields.boolean("Allow an intermediate picking process to provide raw materials to production orders",
                        help="""This module allows an intermediate picking process to provide raw materials to production orders.
                        For example to manage production made by your
                        suppliers (sub-contracting). To achieve this, set the assembled product
                        which is sub-contracted to "No Auto-Picking" and put the location of the
                        supplier in the routing of the assembly operation.
                        It installs the stock_no_autopicking module."""),
        'module_claim_from_delivery': fields.boolean("Track claim issue from delivery ",
                        help="""Adds a Claim link to the delivery order.
                        It installs the claim_from_delivery module."""),
        'module_stock_invoice_directly': fields.boolean("Invoice picking right after delivery",
                        help="""This allows to automatically launch
                        the invoicing wizard if the delivery is to be invoiced When you send or deliver goods.
                        It installs the stock_invoice_directly module."""),
        'module_product_expiry': fields.boolean("Allow to manage expiry date on product ",
                        help="""Track different dates on products and production lots.
                        Following dates can be tracked:
                        - end of life
                        - best before date
                        - removal date
                        - alert date
                        It installs the product_expiry module."""),
        'group_stock_production_lot':fields.boolean("Track production lot",group='base.group_user', implied_group='base.group_stock_production_lot',
                           help="""This allows you to manage products produced by you using production lots (serial numbers).
                            When you select a lot, you can get the upstream or downstream traceability of the products contained in lot.
                           It assigns the "Production Lots" group to employee."""),
        'group_stock_tracking_lot':fields.boolean("Track lot of your incoming and outgoing products ",group='base.group_user', implied_group='base.group_stock_tracking_lot',
                           help="""Allows you to get the upstream or downstream traceability of the products contained in lot.
                           It assigns the "Tracking lots" group to employee."""),
        'group_stock_inventory_valuation':fields.boolean("Track inventory valuation by products ",group='base.group_user', implied_group='base.group_stock_inventory_valuation',
                           help="""
                           It assigns the "Inventory valuation" group to employee."""),
        'group_stock_counterpart_location':fields.boolean("Manage your stock counterpart by products",group='base.group_user', implied_group='base.group_stock_counterpart_location',
                           help="""
                           It assigns the "Counter-Part Locations" group to employee."""),
        'group_stock_inventory_properties':fields.boolean("Define stock locations",group='base.group_user', implied_group='base.group_stock_inventory_properties',
                           help=""".
                           It assigns the "" group to employee."""),
    }

warehouse_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: