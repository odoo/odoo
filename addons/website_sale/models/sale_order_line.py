# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    shop_warning = fields.Char(string="Warning")

    #=== BUSINESS METHODS ===#

    def get_description_following_lines(self):
        return self.name.splitlines()

    def _get_pricelist_price_before_discount(self):
        """On ecommerce orders, the base price must always be the sales price."""
        self.ensure_one()
        self.product_id.ensure_one()

        if self.order_id.website_id:
            return self.env['product.pricelist.item']._compute_price_before_discount(
                product=self.product_id.with_context(**self._get_product_price_context()),
                quantity=self.product_uom_qty or 1.0,
                uom=self.product_uom,
                date=self.order_id.date_order,
                currency=self.currency_id,
            )

        return super()._get_pricelist_price_before_discount()

    def _get_shop_warning(self, clear=True):
        self.ensure_one()
        warn = self.shop_warning
        if clear:
            self.shop_warning = ''
        return warn

    def _get_displayed_unit_price(self):
        show_tax = self.order_id.website_id.show_line_subtotals_tax_selection
        tax_display = 'total_excluded' if show_tax == 'tax_excluded' else 'total_included'

        return self.tax_id.compute_all(
            self.price_unit, self.currency_id, 1, self.product_id, self.order_partner_id,
        )[tax_display]

    def _show_in_cart(self):
        self.ensure_one()
        # Exclude delivery & section/note lines from showing up in the cart
        return not self.is_delivery and not bool(self.display_type)

    def _is_reorder_allowed(self):
        self.ensure_one()
        return self.product_id._is_add_to_cart_allowed()
