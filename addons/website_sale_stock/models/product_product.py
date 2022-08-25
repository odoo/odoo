# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_cart_qty(self, website=None):
        if not self.allow_out_of_stock_order:
            website = website or self.env['website'].get_current_website()
            cart = website and request and website.sale_get_order() or None
            if cart:
                return sum(
                    cart._get_common_product_lines(product=self).mapped('product_uom_qty')
                )
        return 0

    def _is_sold_out(self):
        combination_info = self.with_context(website_sale_stock_get_quantity=True).product_tmpl_id._get_combination_info(product_id=self.id)
        return combination_info['product_type'] == 'product' and combination_info['free_qty'] <= 0
