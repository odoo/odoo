# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

from odoo.exceptions import ValidationError


class ProductRibbon(models.Model):
    _inherit = 'product.ribbon'

    assign = fields.Selection(
        selection_add=[
            ('out_of_stock', "Out of stock"),
        ],
        ondelete={'out_of_stock': 'cascade'}
    )

    def _get_automatic_assigns(self):
        return super()._get_automatic_assigns() + ['out_of_stock']

    def _match_assign(self, product, product_prices):
        is_assign_out_of_stock = (
            self.assign == 'out_of_stock'
            and product._is_sold_out()
        )
        return  is_assign_out_of_stock or super()._match_assign(product, product_prices)
