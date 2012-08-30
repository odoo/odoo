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
import pooler
from tools.translate import _

class mrp_config_settings(osv.osv_memory):
    _name = 'mrp.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'module_stock_planning': fields.boolean('manage master production shedule',
            help ="""This allows to create a manual procurement plan apart of the normal MRP scheduling,
                which works automatically based on minimum stock rules.
                This installs the module stock_planning."""),
        'module_mrp_repair': fields.boolean("manage repairs of products ",
            help="""Allows to manage all product repairs.
                    * Add/remove products in the reparation
                    * Impact for stocks
                    * Invoicing (products and/or services)
                    * Warranty concept
                    * Repair quotation report
                    * Notes for the technician and for the final customer.
                This installs the module mrp_repair."""),
        'module_mrp_operations': fields.boolean("allow detailed planning of work order",
            help="""This allows to add state, date_start,date_stop in production order operation lines (in the "Work Centers" tab).
                This installs the module mrp_operations."""),
        'module_mrp_subproduct': fields.boolean("produce several products from one manufacturing order",
            help="""You can configure sub-products in the bill of material.
                Without this module: A + B + C -> D.
                With this module: A + B + C -> D + E.
                This installs the module mrp_subproduct."""),
        'module_mrp_jit': fields.boolean("generate procurement in real time",
            help="""This allows Just In Time computation of procurement orders.
                All procurement orders will be processed immediately, which could in some
                cases entail a small performance impact.
                This installs the module mrp_jit."""),
        'module_stock_no_autopicking': fields.boolean("manage manual picking to fulfill manufacturing orders ",
            help="""This module allows an intermediate picking process to provide raw materials to production orders.
                For example to manage production made by your suppliers (sub-contracting).
                To achieve this, set the assembled product which is sub-contracted to "No Auto-Picking"
                and put the location of the supplier in the routing of the assembly operation.
                This installs the module stock_no_autopicking."""),
        'group_mrp_routings': fields.boolean("manage routings and work orders ",
            implied_group='mrp.group_mrp_routings',
            help="""Routings allow you to create and manage the manufacturing operations that should be followed
                within your work centers in order to produce a product. They are attached to bills of materials
                that will define the required raw materials."""),
        'group_mrp_properties': fields.boolean("allow several bill of materials per products using properties",
            implied_group='product.group_mrp_properties',
            help="""The selection of the right Bill of Material to use will depend on the  properties specified on the sale order and the Bill of Material."""),
        'module_product_manufacturer': fields.boolean("define manufacturers on products ",
            help="""This allows you to define the following for a product:
                    * Manufacturer
                    * Manufacturer Product Name
                    * Manufacturer Product Code
                    * Product Attributes.
                This installs the module product_manufacturer."""),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
