# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _set_shop_warning_stock(self, desired_qty, new_qty):
        """ Override shop_warning to adapt message for rent ok products.
        """
        self.ensure_one()
        if not self.is_rental:
            return super()._set_shop_warning_stock(desired_qty, new_qty)
        # tell user that the desired qty means the MAX number of products rented at the same time
        # during the period
        self.shop_warning = _(
            """
            You asked for %(desired_qty)s %(product_name)s but only %(new_qty)s are available from
            %(rental_period)s.
            """,
            desired_qty=desired_qty, product_name=self.product_id.name, new_qty=new_qty,
            rental_period=self._get_rental_order_line_description()
        )
        return self.shop_warning

    def _get_max_available_qty(self):
        if self.is_rental:
            cart_and_free_quantities = [
                line.order_id._get_cart_and_free_qty(line.product_id, line=line)
                for line in self._get_lines_with_price()
                if line.product_id.is_storable and not line.product_id.allow_out_of_stock_order
            ]
            max_quantities = [
                free_qty - cart_qty for cart_qty, free_qty in cart_and_free_quantities
            ]
            return min(max_quantities, default=None)
        return super()._get_max_available_qty()
