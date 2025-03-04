# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _set_shop_warning_stock(self, desired_qty, new_qty):
        self.ensure_one()
        self.shop_warning = self.env._(
            "You ask for %(desired_qty)s %(product_name)s but only %(new_qty)s is available",
            desired_qty=desired_qty, product_name=self.product_id.name, new_qty=new_qty
        )

    def _get_max_available_qty(self):
        self.ensure_one()
        cart_qty, free_qty = self.order_id._get_cart_and_free_qty(self.product_id)
        return free_qty - cart_qty

    def _check_availability(self):
        self.ensure_one()
        if self.product_id.is_storable and not self.product_id.allow_out_of_stock_order:
            cart_qty, avl_qty = self.order_id._get_cart_and_free_qty(self.product_id)
            if cart_qty > avl_qty:
                self._set_shop_warning_stock(cart_qty, max(avl_qty, 0))
                return False
        return True
