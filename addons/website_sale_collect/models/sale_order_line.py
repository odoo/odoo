# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_shop_warning_stock(self, desired_quantity, available_quantity):
        self.ensure_one()
        if self.order_id.carrier_id.delivery_type != 'in_store':
            return super()._get_shop_warning_stock(desired_quantity, available_quantity)
        return self.env._(
            "%(available)g/%(desired)g available at this location.",
            avl_qty=available_quantity,
            desired=desired_quantity,
        )
