# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.website_sale.controllers.delivery import Delivery


class WebsiteSaleLoyaltyDelivery(Delivery):

<<<<<<< HEAD
    def _order_summary_values(self, order, **post):
||||||| parent of b93def708f2a (temp)
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
                    'delivery_discount_minor_amount': payment_utils.to_minor_currency_units(
                        amount_free_shipping, currency
                    ),
                })
        return result

    @route()
    def cart_carrier_rate_shipment(self, carrier_id, **kw):
=======
    def _update_website_sale_delivery_return(self, order, **post):
        if order:
            order._update_programs_and_rewards()
            order.validate_taxes_on_sales_order()
        result = super()._update_website_sale_delivery_return(order, **post)
        if order:
            free_shipping_lines = order._get_free_shipping_lines()
            Monetary = request.env['ir.qweb.field.monetary']
            currency = order.currency_id
            if free_shipping_lines:
                amount_free_shipping = sum(free_shipping_lines.mapped('price_subtotal'))
                result.update({
                    'new_amount_delivery': Monetary.value_to_html(0.0, {'display_currency': currency}),
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

    @route()
    def cart_carrier_rate_shipment(self, carrier_id, **kw):
>>>>>>> b93def708f2a (temp)
        Monetary = request.env['ir.qweb.field.monetary']
        res = super()._order_summary_values(order, **post)
        free_shipping_lines = order._get_free_shipping_lines()
        if free_shipping_lines:
            res['amount_delivery_discounted'] = Monetary.value_to_html(
                sum(free_shipping_lines.mapped('price_subtotal')),
                {'display_currency': order.currency_id}
            )
        return res
