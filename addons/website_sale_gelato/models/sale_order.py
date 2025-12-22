# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _verify_updated_quantity(self, order_line, product_id, new_qty, **kwargs):
        """ Override of `website_sale` to prevent mixing Gelato and non-Gelato products in the cart.

        This check is not redundant with the constraint on `sale.order` in `sale_gelato` because the
        constraint would only be enforced at the end of the checkout for eCommerce carts, and would
        not mention the specific product that caused the issue nor display the warning message in a
        user-friendly way.

        :param sale.order.line order_line: The order line to update.
        :param int product_id: The ID of the product to update.
        :param int new_qty: The new quantity of the product.
        :param kwargs: Additional keyword arguments.
        :return: The new quantity and an optional warning message.
        :rtype: tuple[int, str]
        """
        product = self.env['product.product'].browse(product_id)
        mixing_products = product.type != 'service' and any(
            (product.gelato_product_uid and not line.product_id.gelato_product_uid)
            or (not product.gelato_product_uid and line.product_id.gelato_product_uid)
            for line in self.order_line.filtered(lambda l: l.product_id.type != 'service')
        )  # Whether Gelato and non-Gelato products that require delivery are mixed.
        if mixing_products:
            return 0, _(
                "The product %(product_name)s cannot be added to the cart as it requires separate"
                " shipping. Please place your order for the current cart first.",
                product_name=product.name,
            )
        return super()._verify_updated_quantity(order_line, product_id, new_qty, **kwargs)
