# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleDelivery(WebsiteSale):

    @http.route(['/shop/payment'], type='http', auth="public", website=True)
    def payment(self, **post):
        order = request.website.sale_get_order()
        carrier_id = post.get('carrier_id')
        if carrier_id:
            carrier_id = int(carrier_id)
        if order:
            order._check_carrier_quotation(force_carrier_id=carrier_id)
            if carrier_id:
                return request.redirect("/shop/payment")

        return super(WebsiteSaleDelivery, self).payment(**post)

    def order_lines_2_google_api(self, order_lines):
        """ Transforms a list of order lines into a dict for google analytics """
        order_lines_not_delivery = order_lines.filtered(lambda line: not line.is_delivery)
        return super(WebsiteSaleDelivery, self).order_lines_2_google_api(order_lines_not_delivery)

    def order_2_return_dict(self, order):
        """ Returns the tracking_cart dict of the order for Google analytics """
        ret = super(WebsiteSaleDelivery, self).order_2_return_dict(order)
        for line in order.order_line:
            if line.is_delivery:
                ret['transaction']['shipping'] = line.price_unit
        return ret

    def _get_shop_payment_values(self, order, **kwargs):
        values = super(WebsiteSaleDelivery, self)._get_shop_payment_values(order, **kwargs)
        if not order._get_delivery_methods():
            values['errors'].append(
                (_('Sorry, we are unable to ship your order'),
                 _('No shipping method is available for your current order and shipping address. '
                   'Please contact us for more information.')))

        has_stockable_products = any(line.product_id.type in ['consu', 'product'] for line in order.order_line)
        if has_stockable_products:
            if order.carrier_id and not order.delivery_rating_success:
                values['errors'].append(
                    (_("Ouch, you cannot choose this carrier!"),
                     _("%s does not ship to your address, please choose another one.\n(Error: %s)" % (order.carrier_id.name, order.delivery_message))))
                order._remove_delivery_line()

            delivery_carriers = order._get_delivery_methods()
            values['deliveries'] = delivery_carriers.sudo()

        values['delivery_action_id'] = request.env.ref('delivery.action_delivery_carrier_form').id
        return values

    @http.route(['/shop/update_carrier'], type='json', auth='public', methods=['POST'], website=True, csrf=False)
    def update_eshop_carrier(self, **post):
        order = request.website.sale_get_order()
        carrier_id = int(post['carrier_id'])
        if order:
            order._check_carrier_quotation(force_carrier_id=carrier_id)
            return {'status': order.delivery_rating_success,
                    'error_message': order.delivery_message,
                    'carrier_id': carrier_id,
                    'new_amount_delivery': order.currency_id.round(order.delivery_price),
                    'new_amount_untaxed': order.amount_untaxed,
                    'new_amount_tax': order.amount_tax,
                    'new_amount_total': order.amount_total,
            }
