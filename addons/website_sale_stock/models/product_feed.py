# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductFeed(models.Model):
    _inherit = 'product.feed'

    def _prepare_gmc_stock_info(self, product):
        """Override of `website_sale` to check the stock level if the current product cannot be out
        of stock."""
        stock_info = super()._prepare_gmc_stock_info(product)
        if product._is_sold_out():
            stock_info['availability'] = 'out_of_stock'
        return stock_info
