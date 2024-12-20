# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.http import request


class ProductRibbon(models.Model):
    _inherit = 'product.ribbon'

    assign = fields.Selection(
        selection_add=[
            ('out_of_stock', "Out of stock"),
        ],
        ondelete={'out_of_stock': 'cascade'}
    )

    def _get_ribbon(self, product, variant, product_prices):
        if product._is_sold_out():
            return self.sudo().search([('assign', '=', 'out_of_stock')], limit=1)
        return super()._get_ribbon(product, variant, product_prices)
