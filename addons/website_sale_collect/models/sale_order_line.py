# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order.line'

    def _get_shop_warning_stock(self, desired_qty, avl_qty):
        self.ensure_one()
        if self.order_id.carrier_id.delivery_type != 'in_store':
            return super()._get_shop_warning_stock(desired_qty, avl_qty)
        return self.env._(
            "%(avl_qty)g/%(desired_qty)g available at this location.",
            avl_qty=avl_qty,
            desired_qty=desired_qty,
        )
