# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductRibbon(models.Model):
    _inherit = 'product.ribbon'

    assign = fields.Selection(
        selection_add=[('out_of_stock', "Out of stock")],
        ondelete={'out_of_stock': 'cascade'},
    )
