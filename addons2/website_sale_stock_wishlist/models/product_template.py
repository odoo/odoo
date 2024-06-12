# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_additionnal_combination_info(self, product_or_template, quantity, date, website):
        res = super()._get_additionnal_combination_info(product_or_template, quantity, date, website)

        if not self.env.context.get('website_sale_stock_wishlist_get_wish'):
            return res

        if product_or_template.is_product_variant:
            product_sudo = product_or_template.sudo()
            res['is_in_wishlist'] = product_sudo._is_in_wishlist()

        return res
