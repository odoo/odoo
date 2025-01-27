# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial

from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.website_sale.controllers.delivery import Delivery


class WebsiteSaleLoyaltyDelivery(Delivery):

    def _order_summary_values(self, order, **post):
        to_html = partial(
            request.env['ir.qweb.field.monetary'].value_to_html,
            options={'display_currency': order.currency_id},
        )
        res = super()._order_summary_values(order, **post)
        free_shipping_lines = order._get_free_shipping_lines()
        if free_shipping_lines:
            shipping_discount = sum(free_shipping_lines.mapped('price_subtotal'))
            res['amount_delivery_discounted'] = to_html(shipping_discount)
            res['delivery_discount_minor_amount'] = payment_utils.to_minor_currency_units(
                shipping_discount, order.currency_id
            )
        res['discount_reward_amounts'] = [
            to_html(sum(lines.mapped('price_subtotal')))
            for reward, lines in order.order_line.grouped('reward_id').items()
            if reward.reward_type == 'discount'
        ]
        return res
