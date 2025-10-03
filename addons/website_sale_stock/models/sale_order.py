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

    def _verify_updated_quantity(self, order_line, product_id, new_qty, uom_id, **kwargs):
        self.ensure_one()
        product = self.env['product.product'].browse(product_id)
        if product.is_storable and not product.allow_out_of_stock_order:
            uom = self.env['uom.uom'].browse(uom_id)
            product_uom = product.uom_id

            product_qty_in_cart, available_qty = self._get_cart_and_free_qty(product)

            # Convert cart and available quantities to the requested uom
            product_qty_in_cart = product_uom._compute_quantity(product_qty_in_cart, uom)
            available_qty = product_uom._compute_quantity(available_qty, uom)

            old_qty = order_line.product_uom_qty if order_line else 0
            added_qty = new_qty - old_qty
            total_cart_qty = product_qty_in_cart + added_qty
            if available_qty < total_cart_qty:
                allowed_line_qty = available_qty - (product_qty_in_cart - old_qty)
                if allowed_line_qty > 0:
                    def format_qty(qty):
                        return int(qty) if float(qty).is_integer() else qty
                    if order_line:
                        warning = order_line._get_shop_warning_stock(
                            format_qty(total_cart_qty),
                            format_qty(available_qty),
                        )
                    else:
                        warning = self.env._(
                            "You requested %(desired_qty)s products, but only %(available_qty)s are"
                            " available in stock.",
                            desired_qty=format_qty(total_cart_qty),
                            available_qty=format_qty(available_qty),
                        )
                elif order_line:
                    # Line will be deleted
                    warning = self.env._(
                        "Some products became unavailable and your cart has been updated. We're"
                        " sorry for the inconvenience."
                    )
                else:
                    warning = self.env._(
                        "%(product_name)s has not been added to your cart since it is not available.",
                        product_name=product.name,
                    )
                return allowed_line_qty, warning
        return super()._verify_updated_quantity(order_line, product_id, new_qty, uom_id, **kwargs)

    def _get_cart_and_free_qty(self, product):
        """Get cart quantity and free quantity for given product.

        Note: self.ensure_one()

        :param product: `product.product` record.
        :returns: cart quantity and available quantity in the product uom
        :rtype: tuple
        """
        self.ensure_one()
        product.ensure_one()

        return self._get_cart_qty(product.id), self._get_free_qty(product)

    def _get_free_qty(self, product):
        return self.website_id._get_product_available_qty(product)

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
        :return: product quantity in the product uom
        :rtype: float
        """
        if not self:
            return 0.0
        order_lines = self._get_common_product_lines(product_id)
        return sum(
            order_lines.mapped(
                lambda sol: sol.product_uom_id._compute_quantity(
                    sol.product_uom_qty, sol.product_id.uom_id,
                )
            )
        )

    def _get_common_product_lines(self, product_id=None):
        """Get all the lines of the current order with the given product."""
        return self.order_line.filtered(lambda sol: sol.product_id.id == product_id)

    def _is_cart_ready_for_checkout(self):
        """Override of `website_sale` to prevent the user from proceeding if there is not enough
        stock for some order lines."""
        if self._has_deliverable_products() and not self._all_product_available():
            self.shop_warning = self.env._(
                "Unfortunately, there is no longer enough stock to fulfill your order.\n"
                "Please update your cart. We apologize for any inconvenience caused."
            )
            return False
        return super()._is_cart_ready_for_checkout()

    def _all_product_available(self):
        """Whether all the order lines are available on the current website."""
        self.ensure_one()
        # Uses list comprehension to ensure all the shop warnings are updated.
        return all([sol._check_availability() for sol in self.order_line])  # noqa: C419

    def _filter_can_send_abandoned_cart_mail(self):
        """Filter sale orders on their product availability."""
        return super()._filter_can_send_abandoned_cart_mail().filtered(
            lambda so: so._all_product_available()
        )
