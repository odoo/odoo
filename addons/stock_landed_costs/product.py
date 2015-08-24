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
        'split_method': fields.selection(SPLIT_METHOD, 'Split Method'),
    }

    _defaults = {
        'landed_cost_ok': False,
        'split_method': 'equal',
    }
