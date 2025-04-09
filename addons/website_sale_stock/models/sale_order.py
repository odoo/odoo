# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _compute_warehouse_id(self):
        website_orders = self.filtered('website_id')
        super(SaleOrder, self - website_orders)._compute_warehouse_id()
        for order in website_orders:
            if order.website_id.warehouse_id:
                order.warehouse_id = order.website_id.warehouse_id
            else:
                super(SaleOrder, order)._compute_warehouse_id()
            if not order.warehouse_id:
                order.warehouse_id = self.env.user._get_default_warehouse_id()

    def _verify_updated_quantity(self, order_line, product_id, new_qty, **kwargs):
        self.ensure_one()
        product = self.env['product.product'].browse(product_id)
        if product.is_storable and not product.allow_out_of_stock_order:
            product_qty_in_cart, available_qty = self._get_cart_and_free_qty(product)

            old_qty = order_line.product_uom_qty if order_line else 0
            added_qty = new_qty - old_qty
            total_cart_qty = product_qty_in_cart + added_qty
            if available_qty < total_cart_qty:
                allowed_line_qty = available_qty - (product_qty_in_cart - old_qty)
                if allowed_line_qty > 0:
                    if order_line:
                        order_line._set_shop_warning_stock(total_cart_qty, available_qty)
                    else:
                        self.shop_warning = self.env._(
                            "You requested %(desired_qty)s products, but only %(available_qty)s are"
                            " available in stock.",
                            desired_qty=total_cart_qty, available_qty=available_qty
                        )
                    returned_warning = order_line.shop_warning or self.shop_warning
                elif order_line:
                    # Line will be deleted
                    self.shop_warning = self.env._(
                        "Some products became unavailable and your cart has been updated. We're"
                        " sorry for the inconvenience."
                    )
                    returned_warning = self.shop_warning
                else:
                    returned_warning = self.env._(
                        "The item has not been added to your cart since it is not available."
                    )
                return allowed_line_qty, returned_warning
        return super()._verify_updated_quantity(order_line, product_id, new_qty, **kwargs)

    def _get_cart_and_free_qty(self, product):
        """Get cart quantity and free quantity for given product.

        Note: self.ensure_one()

        :param product: `product.product` record.
        :returns: cart quantity and available quantity
        :rtype: tuple
        """
        self.ensure_one()
        product.ensure_one()

        return self._get_cart_qty(product.id), self._get_free_qty(product)

    def _get_free_qty(self, product):
        return product.with_context(warehouse_id=self._get_shop_warehouse_id()).free_qty

    def _get_shop_warehouse_id(self):
        """Return the warehouse to use for shop availability checks.

        If no warehouse is specified on the website, all warehouses are considered,
        regardless of the warehouse automatically assigned to the order.

        Note: self.ensure_one()

        :returns: `stock.warehouse` id
        :rtype: int or False
        """
        self.ensure_one()
        return self.website_id.warehouse_id.id

    def _get_cart_qty(self, product_id):
        """Return the quantity of the given product in the current cart, if any.

        :param int product_id: `product.product` id
        :return: product quantity
        :rtype: float
        """
        if not self:
            return 0.0
        return sum(self._get_common_product_lines(product_id).mapped('product_uom_qty'))

    def _get_common_product_lines(self, product_id=None):
        """Get all the lines of the current order with the given product."""
        return self.order_line.filtered(lambda sol: sol.product_id.id == product_id)

    def _is_cart_ready_for_checkout(self):
        """Override of `website_sale` to stop the user if his cart contains a sold out product."""
        if sold_out_order_lines := self._get_sold_out_order_lines():
            self.shop_warning = self.env._(
                "Some of your products are no longer available. Please update your cart. We"
                " apologize for any inconvenience caused."
            )
            sold_out_order_lines.shop_warning = self.env._(
                "This product is no longer available."
            )
            return False
        return super()._is_cart_ready_for_checkout()

    def _is_cart_ready_to_confirm(self):
        """Override of `website_sale` to check that the selected warehouse can fulfill the order."""
        if not self._is_in_stock(self._get_shop_warehouse_id(), update_shop_warning=True):
            self.shop_warning = self._build_stock_warning()
            return False
        return super()._is_cart_ready_to_confirm()

    def _build_stock_warning(self):
        """Hook to build the a stock warning when the source warehouse of the selected delivery
        method is out of stock.

        :rtype: str
        """
        return self.env._(
            "Some products are not available with the selected delivery method. Please update "
            "your choice and try again."
        )

    def _filter_can_send_abandoned_cart_mail(self):
        """Filter sale orders on their product availability."""
        return super()._filter_can_send_abandoned_cart_mail().filtered(
            lambda so: not so._get_sold_out_order_lines()
        )

    def _get_sold_out_order_lines(self):
        self.ensure_one()
        return self.order_line.filtered(lambda sol: sol.product_id._is_sold_out())

    def _is_in_stock(self, wh_id, update_shop_warning=False):
        """ Check whether all storable products of the cart are in stock in the given warehouse.

        :param int wh_id: The warehouse in which to check the stock, as a `stock.warehouse` id.
        :param bool update_shop_warning: Update the order lines' `shop_warning` if unavailable.
        :return: Whether all storable products are in stock.
        :rtype: bool
        """
        return not self._get_unavailable_order_lines(wh_id, update_shop_warning=update_shop_warning)

    def _get_unavailable_order_lines(self, wh_id, update_shop_warning=False):
        """ Return the order lines with unavailable products for the given warehouse.

        :param int wh_id: The warehouse in which to check the stock, as a `stock.warehouse` id.
        :param bool update_shop_warning: Update the order lines' `shop_warning` if unavailable.
        :return: The order lines with unavailable products.
        :rtype: sale.order.line
        """
        unavailable_order_lines = self.env['sale.order.line']
        for ol in self.order_line:
            if ol.is_storable:
                product = ol.product_id
                cart_qty = self._get_cart_qty(product.id)
                free_qty = product.with_context(warehouse_id=wh_id).free_qty
                if cart_qty > free_qty:
                    if update_shop_warning:
                        ol._set_shop_warning_stock(cart_qty, max(free_qty, 0))
                    unavailable_order_lines |= ol
        return unavailable_order_lines
