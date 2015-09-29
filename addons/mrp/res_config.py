# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _

class mrp_config_settings(osv.osv_memory):
    _name = 'mrp.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'group_product_variant': fields.selection([
            (0, "No variants on products"),
            (1, 'Products can have several attributes, defining variants (Example: size, color,...)')
            ], "Product Variants",
            help='Work with product variant allows you to define some variant of the same products, an ease the product management in the ecommerce for example',
            implied_group='product.group_product_variant'),
        'module_mrp_operations': fields.selection([
            (0, "Do not use a planning for the work orders "),
            (1, "Allow detailed planning of work orders")
            ], "Work Order Planning",
            help='This allows to add state, date_start,date_stop in production order operation lines (in the "Work Centers" tab).\n'
                 '-This installs the module mrp_operations.'),
        'module_mrp_byproduct': fields.selection([
            (0, "No by-products in bills of materials (A + B --> C)"),
            (1, "Bills of materials may produce residual products (A + B --> C + D)")
            ], "By-Products",
            help='You can configure by-products in the bill of material.\n'
                 'Without this module: A + B + C -> D.\n'
                 'With this module: A + B + C -> D + E.\n'
                 '-This installs the module mrp_byproduct.'),
        'group_mrp_routings': fields.selection([
            (0, "Manage production by manufacturing orders"),
            (1, "Manage production by work orders")
            ], "Routings",
            implied_group='mrp.group_mrp_routings',
            help='Work Order Operations allow you to create and manage the manufacturing operations that should be followed '
                 'within your work centers in order to produce a product. They are attached to bills of materials '
                 'that will define the required raw materials.'),
        'group_rounding_efficiency': fields.selection([
            (0, "No rounding and efficiency on bills of materials"),
            (1, "Manage rounding and efficiency of bills of materials components")
            ], "Rounding efficiency",
            implied_group='mrp.group_rounding_efficiency',
            help="""Allow to manage product rounding on quantity and product efficiency during production process"""),
    }
