# Part of Odoo. See LICENSE file for full copyright and licensing details.
from functools import partial

from odoo.http import request

from odoo.addons.website_sale.controllers.delivery import Delivery


class WebsiteSaleLoyaltyDelivery(Delivery):

    def _order_summary_values(self, order, **post):
        to_html = partial(
            request.env['ir.qweb.field.monetary'].value_to_html,
            options={'display_currency': order.currency_id},
        )
        res = super()._order_summary_values(order, **post)
        free_shipping_lines = order._get_free_shipping_lines()
        shipping_discount = sum(free_shipping_lines.mapped('price_subtotal'))
        if shipping_discount:
            res['amount_delivery_discounted'] = to_html(shipping_discount)
        if order.reward_amount:
            res['amount_order_discounted'] = to_html(order.reward_amount - shipping_discount)
        return res
