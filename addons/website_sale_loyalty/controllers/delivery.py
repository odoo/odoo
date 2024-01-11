# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.website_sale.controllers.delivery import WebsiteSaleDelivery


class WebsiteSaleLoyaltyDelivery(WebsiteSaleDelivery):

    def _update_website_sale_delivery_return(self, order, **post):
        if order:
            order._update_programs_and_rewards()
            order.validate_taxes_on_sales_order()
        result = super()._update_website_sale_delivery_return(order, **post)
        if order:
            free_shipping_lines = order._get_free_shipping_lines()
            if free_shipping_lines:
                Monetary = request.env['ir.qweb.field.monetary']
                currency = order.currency_id
                amount_free_shipping = sum(free_shipping_lines.mapped('price_subtotal'))
                result.update({
                    'new_amount_delivery': Monetary.value_to_html(0.0, {'display_currency': currency}),
                    'new_amount_order_discounted': Monetary.value_to_html(order.reward_amount - amount_free_shipping, {'display_currency': currency}),
                })
        return result

    def _get_price(self, carrier, rate, order, is_express_checkout_flow=False):
        # Avoid computing carrier price delivery is free (coupon). It means if
        # the carrier has error (eg 'delivery only for Belgium') it will show
        # Free until the user clicks on it.
        if order._get_free_shipping_lines():
            return 0.0
        return super()._get_price(carrier, rate, order, is_express_checkout_flow)
