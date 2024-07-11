# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.delivery import WebsiteSaleDelivery
from odoo.addons.payment import utils as payment_utils
from odoo.http import request


class WebsiteSaleLoyaltyDelivery(WebsiteSaleDelivery):

    def _update_website_sale_delivery_return(self, order, **post):
        result = super()._update_website_sale_delivery_return(order, **post)
        if order:
            free_shipping_lines = order._get_free_shipping_lines()
            Monetary = request.env['ir.qweb.field.monetary']
            currency = order.currency_id
            if free_shipping_lines:
                amount_free_shipping = sum(free_shipping_lines.mapped('price_subtotal'))
                result.update({
                    'new_amount_delivery_discount': Monetary.value_to_html(
                        amount_free_shipping, {'display_currency': currency}
                    ),
                    'new_amount_order_discounted': Monetary.value_to_html(order.reward_amount - amount_free_shipping, {'display_currency': currency}),
                    'delivery_discount_minor_amount': payment_utils.to_minor_currency_units(
                        amount_free_shipping, currency
                    ),
                })
            else:
                result.update({'new_amount_order_discounted': Monetary.value_to_html(
                    order.reward_amount, {'display_currency': currency}
                )})
        return result
