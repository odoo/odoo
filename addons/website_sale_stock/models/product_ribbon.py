# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductRibbon(models.Model):
    _inherit = 'product.ribbon'

    assign = fields.Selection(
        selection_add=[('out_of_stock', "Out of stock")],
        ondelete={'out_of_stock': 'cascade'},
    )

    def _get_applicable_ribbon(self, product, product_prices):
        """
        Override of `website_sale` to check if the product is eligible for out of stock ribbon.
        """
        for ribbon in self:
            if (
                ribbon.assign == 'out_of_stock'
                and not product.product_tmpl_id.allow_out_of_stock_order
                and product._is_sold_out()
            ):
                return ribbon
        return super()._get_applicable_ribbon(product, product_prices)
