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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class mrp_config_settings(osv.osv_memory):
    _name = 'mrp.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'module_mrp_repair': fields.boolean("Manage repairs of products ",
            help='Allows to manage all product repairs.\n'
                 '* Add/remove products in the reparation\n'
                 '* Impact for stocks\n'
                 '* Invoicing (products and/or services)\n'
                 '* Warranty concept\n'
                 '* Repair quotation report\n'
                 '* Notes for the technician and for the final customer.\n'
                 '-This installs the module mrp_repair.'),
        'module_mrp_operations': fields.boolean("Allow detailed planning of work order",
            help='This allows to add state, date_start,date_stop in production order operation lines (in the "Work Centers" tab).\n'
                 '-This installs the module mrp_operations.'),
        'module_mrp_byproduct': fields.boolean("Produce several products from one manufacturing order",
            help='You can configure by-products in the bill of material.\n'
                 'Without this module: A + B + C -> D.\n'
                 'With this module: A + B + C -> D + E.\n'
                 '-This installs the module mrp_byproduct.'),
        'group_mrp_routings': fields.boolean("Manage routings and work orders ",
            implied_group='mrp.group_mrp_routings',
            help='Routings allow you to create and manage the manufacturing operations that should be followed '
                 'within your work centers in order to produce a product. They are attached to bills of materials '
                 'that will define the required raw materials.'),
        'group_mrp_properties': fields.boolean("Allow several bill of materials per products using properties",
            implied_group='product.group_mrp_properties',
            help="""The selection of the right Bill of Material to use will depend on the properties specified on the sales order and the Bill of Material."""),
        'group_route_line_type': fields.boolean("Manage multi level Bill of Materials",
            implied_group='mrp.group_route_line_type',
            help="""Allow to manage multi level bill of material"""),
        'group_rounding_efficiency': fields.boolean("Manage rounding and efficiency of BoM components",
            implied_group='mrp.group_rounding_efficiency',
            help="""Allow to manage product rounding on quantity and product efficiency during production process"""),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
