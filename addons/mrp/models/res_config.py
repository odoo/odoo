# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
        'group_mrp_routings': fields.boolean("Manage Work Order Operations and work orders ",
            implied_group='mrp.group_mrp_routings',
            help='Work Order Operations allow you to create and manage the manufacturing operations that should be followed '
                 'within your work centers in order to produce a product. They are attached to bills of materials '
                 'that will define the required raw materials.'),
        'group_mrp_properties': fields.boolean("Allow several bill of materials per products using properties",
            implied_group='product.group_mrp_properties',
            help="""The selection of the right Bill of Material to use will depend on the properties specified on the sales order and the Bill of Material."""),
        'group_rounding_efficiency': fields.boolean("Manage rounding and efficiency of BoM components",
            implied_group='mrp.group_rounding_efficiency',
            help="""Allow to manage product rounding on quantity and product efficiency during production process"""),
    }
