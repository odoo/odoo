# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.website_sale.controllers.delivery import Delivery


class WebsiteSaleLoyaltyDelivery(Delivery):

    def _order_summary_values(self, order, **post):
        Monetary = request.env['ir.qweb.field.monetary']
        res = super()._order_summary_values(order, **post)
        free_shipping_lines = order._get_free_shipping_lines()
        if free_shipping_lines:
            res['amount_delivery_discounted'] = Monetary.value_to_html(
                sum(free_shipping_lines.mapped('price_subtotal')),
                {'display_currency': order.currency_id}
            )
        return res
