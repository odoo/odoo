# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    def rate_shipment(self, order):
        self.ensure_one()
        res = super().rate_shipment(order)
        if res:
            free_shipping = order.order_line.filtered(lambda line: line.reward_id.reward_type == 'shipping')
            if res['success'] and free_shipping:
                res['warning_message'] = _('The shipping is free since the order contains a coupon for free shipping.')
                delivery_price = res['price']
                discount = free_shipping.reward_id.discount_max_amount or delivery_price
                res['price'] = max(0.0, delivery_price - discount)
            return res
