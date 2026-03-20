# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _set_shop_warning_stock(self, desired_qty, new_qty, save=True):
        self.ensure_one()
        warning = self.env._(
            "You ask for %(desired_qty)s %(product_name)s but only %(new_qty)s is available",
            desired_qty=desired_qty, product_name=self.product_id.name, new_qty=new_qty
        )
        if save:
            self.shop_warning = warning
        return warning

    def _get_max_line_qty(self):
        max_quantity = self._get_max_available_qty()
        return self.product_uom_qty + max_quantity if (max_quantity is not None) else None

    def _get_max_available_qty(self):
        """ The max quantity of a combo product is the max quantity of its selected combo item with
        the lowest max quantity. If none of the combo items has a max quantity, then the combo
        product also has no max quantity.
        """
        self.ensure_one()
        cart_and_free_quantities = [
            line.order_id._get_cart_and_free_qty(line.product_id)
            for line in self._get_lines_with_price()
            if line.product_id.is_storable and not line.product_id.allow_out_of_stock_order
        ]
        max_quantities = [
            free_qty - cart_qty for cart_qty, free_qty in cart_and_free_quantities
        ]
        return min(max_quantities, default=None)

    def _check_availability(self):
        self.ensure_one()
        if self.product_id.is_storable and not self.product_id.allow_out_of_stock_order:
            cart_qty, avl_qty = self.order_id._get_cart_and_free_qty(self.product_id)
            if cart_qty > avl_qty:
                self._set_shop_warning_stock(cart_qty, max(avl_qty, 0))
                return False
        return True
