# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _set_shop_warning_stock(self, desired_qty, new_qty):
        self.ensure_one()
        self.shop_warning = _(
            'You ask for %(desired_qty)s %(product_name)s but only %(new_qty)s is available',
            desired_qty=desired_qty, product_name=self.product_id.name, new_qty=new_qty
        )
        return self.shop_warning

    def _get_max_available_qty(self):
        return self.product_id.free_qty - self.product_id._get_cart_qty()
