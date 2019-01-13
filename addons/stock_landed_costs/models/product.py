# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

SPLIT_METHOD = [
    ('equal', 'Equal'),
    ('by_quantity', 'By Quantity'),
    ('by_current_cost_price', 'By Current Cost'),
    ('by_weight', 'By Weight'),
    ('by_volume', 'By Volume'),
]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    landed_cost_ok = fields.Boolean('Is a Landed Cost', help='Indicates whether the product is a landed cost.')
    split_method = fields.Selection(
        selection=SPLIT_METHOD, string='Split Method', default='equal',
        help="Equal : Cost will be equally divided.\n"
             "By Quantity : Cost will be divided according to product's quantity.\n"
             "By Current cost : Cost will be divided according to product's current cost.\n"
             "By Weight : Cost will be divided depending on its weight.\n"
             "By Volume : Cost will be divided depending on its volume.")
