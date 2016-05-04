# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv

SPLIT_METHOD = [
    ('equal', 'Equal'),
    ('by_quantity', 'By Quantity'),
    ('by_current_cost_price', 'By Current Cost'),
    ('by_weight', 'By Weight'),
    ('by_volume', 'By Volume'),
]

class product_template(osv.osv):
    _inherit = "product.template"

    _columns = {
        'landed_cost_ok': fields.boolean('Landed Costs'),
        'split_method': fields.selection(SPLIT_METHOD, 'Split Method', help="Equal : Cost will be equally divided.\n"\
            "By Quantity : Cost will be divided according to product's quantity.\n"\
            "By Current cost : Cost will be divided according to product's current cost.\n"\
            "By Weight : Cost will be divided depending on its weight.\n"\
            "By Volume : Cost will be divided depending on its volume."),
    }

    _defaults = {
        'landed_cost_ok': False,
        'split_method': 'equal',
    }
