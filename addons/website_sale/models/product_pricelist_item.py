# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._invalidate_related_product_prices()
        self.env['product.price']._run_cron_calculate_price_for_pricelist_products()
        return res

    def write(self, vals):
        """Invalidate and recompute the product price when updating a pricelist item."""
        self._invalidate_related_product_prices()
        res = super().write(vals)
        self._invalidate_related_product_prices()
        self.env['product.price']._run_cron_calculate_price_for_pricelist_products()
        return res

    @api.ondelete(at_uninstall=False)
    def _invalidate_product_prices(self):
        """Invalidate and recompute the product price when deleting a pricelist item."""
        self._invalidate_related_product_prices()
        self.env['product.price']._run_cron_calculate_price_for_pricelist_products()

    def _invalidate_related_product_prices(self):
        ProductPrice = self.env['product.price']
        if ProductPrice._is_enabled():
            for item in self:
                domain = Domain('pricelist_id', '=', item.pricelist_id.id)
                chained_items = self.search_fetch(
                    Domain('base_pricelist_id', '=', item.pricelist_id.id)
                )
                if chained_items:
                    domain |= Domain('pricelist_id', 'in', chained_items.pricelist_id.ids)
                if item.applied_on == '2_product_category':
                    domain &= Domain('product_tmpl_id.categ_id', 'in', item.categ_id.id)
                elif item.applied_on == '1_product':
                    domain &= Domain('product_tmpl_id', '=', item.product_tmpl_id.id)
                elif item.applied_on == '0_product_variant':
                    domain &= Domain('product_product_id', '=', item.product_id.id)
                ProductPrice.search(domain)._invalidate()

    def _show_discount_on_shop(self):
        """On ecommerce, formula rules are also expected to show discounts.

        Only for /shop, /product, and configurators, not on the cart or the checkout.
        """
        if not self:
            return False

        self.ensure_one()

        return self.compute_price == 'percentage' or (
            self.compute_price == 'formula'
            and self.price_discount
            and self.base in ('list_price', 'pricelist')
        )
