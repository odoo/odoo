# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from odoo.addons.payment import utils as payment_utils
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.exceptions import UserError


class WebsiteSaleDelivery(WebsiteSale):
    _express_checkout_shipping_route = '/shop/express/shipping_address_change'

    @http.route()
    def shop_payment(self, **post):
        order = request.website.sale_get_order()
        carrier_id = post.get('carrier_id')
        keep_carrier = post.get('keep_carrier', False)
        if keep_carrier:
            keep_carrier = bool(int(keep_carrier))
        if carrier_id:
            carrier_id = int(carrier_id)
        if order:
            order._check_carrier_quotation(force_carrier_id=carrier_id, keep_carrier=keep_carrier)
            if carrier_id:
                return request.redirect("/shop/payment")

        return super(WebsiteSaleDelivery, self).shop_payment(**post)

    @http.route(['/shop/update_carrier'], type='json', auth='public', methods=['POST'], website=True, csrf=False)
    def update_eshop_carrier(self, **post):
        order = request.website.sale_get_order()
        carrier_id = int(post['carrier_id'])
        if order and carrier_id != order.carrier_id.id:
            if any(tx.state not in ("cancel", "error", "draft") for tx in order.transaction_ids):
                raise UserError(_('It seems that there is already a transaction for your order, you can not change the delivery method anymore'))
            order._check_carrier_quotation(force_carrier_id=carrier_id)
        return self._update_website_sale_delivery_return(order, **post)

    @http.route(['/shop/carrier_rate_shipment'], type='json', auth='public', methods=['POST'], website=True)
    def cart_carrier_rate_shipment(self, carrier_id, **kw):
        order = request.website.sale_get_order(force_create=True)

        if not int(carrier_id) in order._get_delivery_methods().ids:
            raise UserError(_('It seems that a delivery method is not compatible with your address. Please refresh the page and try again.'))

        Monetary = request.env['ir.qweb.field.monetary']

        res = {'carrier_id': carrier_id}
        carrier = request.env['delivery.carrier'].sudo().browse(int(carrier_id))
        rate = WebsiteSaleDelivery._get_rate(carrier, order)
        if rate.get('success'):
            res['status'] = True
            res['new_amount_delivery'] = Monetary.value_to_html(rate['price'], {'display_currency': order.currency_id})
            res['is_free_delivery'] = not bool(rate['price'])
            res['error_message'] = rate['warning_message']
        else:
            res['status'] = False
            res['new_amount_delivery'] = Monetary.value_to_html(0.0, {'display_currency': order.currency_id})
            res['error_message'] = rate['error_message']
        return res

    @http.route()
    def cart(self, **post):
        order = request.website.sale_get_order()
        if order and order.carrier_id:
            # Express checkout is based on the amout of the sale order. If there is already a
            # delivery line, Express Checkout form will display and compute the price of the
            # delivery two times (One already computed in the total amount of the SO and one added
            # in the form while selecting the delivery carrier)
            order._remove_delivery_line()

        return super().cart(**post)

    @http.route()
    def process_express_checkout(
            self, billing_address, shipping_address=None, shipping_option=None, **kwargs
        ):
        """ Override of `website_sale` to records the shipping information on the order when using
        express checkout flow.

        Depending on whether the partner is registered and logged in, either creates a new partner
        or uses an existing one that matches all received data.

        :param dict billing_address: Billing information sent by the express payment form.
        :param dict shipping_address: Shipping information sent by the express payment form.
        :param dict shipping_option: Carrier information sent by the express payment form.
        :param dict kwargs: Optional data. This parameter is not used here.
        :return int: The order's partner id.
        """
        if not (shipping_address and shipping_option):
            return super().process_express_checkout(billing_address, **kwargs)

        order_sudo = request.website.sale_get_order()

        # Update the partner with all the information
        self._include_country_and_state_in_address(shipping_address)

        # At this point, if the user is a public user, the order will have a partner created by
        # `process_express_checkout_delivery_choice`. No need to check if he is connected or not.

        if order_sudo.partner_shipping_id.name.endswith(order_sudo.name):
            # The existing partner was created by `process_express_checkout_delivery_choice`, it
            # means that the partner is missing information, so we update it.
            order_sudo.partner_shipping_id = self._create_or_edit_partner(
                shipping_address,
                edit=True,
                type='delivery',
                partner_id=order_sudo.partner_shipping_id.id,
            )
        elif any(
            shipping_address[k] != order_sudo.partner_shipping_id[k] for k in shipping_address
        ):
            # The sale order's shipping partner's address is different from the one received. If all
            # the sale order's child partners' address differs from the one received, we create a
            # new partner. The phone isn't always checked because it isn't sent in shipping
            # information with Google Pay.
            child_partner_id = self._find_child_partner(
                order_sudo.partner_id.commercial_partner_id.id, shipping_address
            )
            if child_partner_id:
                order_sudo.partner_shipping_id = child_partner_id
            else:
                order_sudo.partner_shipping_id = self._create_or_edit_partner(
                    shipping_address,
                    type='delivery',
                    parent_id=order_sudo.partner_id.id,
                )

        # Process the delivery carrier
        order_sudo._check_carrier_quotation(force_carrier_id=int(shipping_option['id']))

        return super().process_express_checkout(billing_address, **kwargs)

    @http.route(
        _express_checkout_shipping_route, type='json', auth='public', methods=['POST'],
        website=True, sitemap=False
    )
    def express_checkout_process_shipping_address(self, partial_shipping_address):
        """ Processes shipping address and returns available carriers.

        Depending on whether the partner is registered and logged in or not, creates a new partner
        or uses an existing partner that matches the partial shipping address received.

        :param dict shipping_address: a dictionary containing part of shipping information sent by
                                      the express payment provider.
        :return dict: all available carriers for `shipping_address` sorted by lowest price.
        """
        order_sudo = request.website.sale_get_order()
        public_partner = request.website.partner_id

        self._include_country_and_state_in_address(partial_shipping_address)
        if order_sudo.partner_id == public_partner:
            # The partner_shipping_id and partner_invoice_id will be automatically computed when
            # changing the partner_id of the SO. This allow website_sale to avoid create duplicates.
            order_sudo.partner_id = self._create_or_edit_partner(
                partial_shipping_address,
                type='delivery',
                name=_('Anonymous express checkout partner for order %s', order_sudo.name),
            )
            # Pricelist are recomputed every time the partner is changed. We don't want to recompute
            # the price with another pricelist at this state since the customer has already accepted
            # the amount and validated the payment.
            order_sudo.env.remove_to_compute(
                order_sudo._fields['pricelist_id'], order_sudo
            )
        elif order_sudo.partner_shipping_id.name.endswith(order_sudo.name):
            self._create_or_edit_partner(
                partial_shipping_address,
                edit=True,
                type='delivery',
                partner_id=order_sudo.partner_shipping_id.id,
            )
        elif any(
            partial_shipping_address[k] != order_sudo.partner_shipping_id[k]
            for k in partial_shipping_address
        ):
            # Check if a child partner doesn't already exist with the same informations. The
            # phone isn't always checked because it isn't sent in shipping information with
            # Google Pay.
            child_partner_id = self._find_child_partner(
                order_sudo.partner_id.commercial_partner_id.id, partial_shipping_address
            )
            if child_partner_id:
                order_sudo.partner_shipping_id = child_partner_id
            else:
                order_sudo.partner_shipping_id = self._create_or_edit_partner(
                    partial_shipping_address,
                    type='delivery',
                    parent_id=order_sudo.partner_id.id,
                    name=_('Anonymous express checkout partner for order %s', order_sudo.name),
                )

        # Returns the list of develivery carrier available for the sale order.
        return sorted([{
            'id': carrier.id,
            'name': carrier.name,
            'description': carrier.website_description,
            'minorAmount': payment_utils.to_minor_currency_units(
                WebsiteSaleDelivery._get_rate(carrier, order_sudo, is_express_checkout_flow=True)['price'],
                order_sudo.currency_id,
            ),
        } for carrier in order_sudo._get_delivery_methods()],
        key=lambda carrier: carrier['minorAmount'])

    @staticmethod
    def _get_rate(carrier, order, is_express_checkout_flow=False):
        """ Compute the price of the order shipment and apply the taxes if relevant

        :param recordset carrier: the carrier for which the rate is to be recovered
        :param recordset order: the order for which the rate is to be recovered
        :param boolean is_express_checkout_flow: Whether the flow is express checkout or not
        :return dict: the rate, as returned in `rate_shipment()`
        """
        # Some delivery carriers check if all the required fields are available before computing the
        # rate, even if those fields aren't required for computing the rate (although they are for
        # delivering the goods). If we only have partial information about the delivery address but
        # still want to compute the rate, this context key will ensure that we only check the
        # required fields for a partial delivery address (city, zip, country_code, state_code).
        rate = carrier.rate_shipment(order.with_context(
            express_checkout_partial_delivery_address=is_express_checkout_flow
        ))
        if rate.get('success'):
            tax_ids = carrier.product_id.taxes_id.filtered(
                lambda t: t.company_id == order.company_id
            )
            if tax_ids:
                fpos = order.fiscal_position_id
                tax_ids = fpos.map_tax(tax_ids)
                taxes = tax_ids.compute_all(
                    rate['price'],
                    currency=order.currency_id,
                    quantity=1.0,
                    product=carrier.product_id,
                    partner=order.partner_shipping_id,
                )
                if not is_express_checkout_flow and request.env.user.has_group(
                    'account.group_show_line_subtotals_tax_excluded'
                ):
                    rate['price'] = taxes['total_excluded']
                else:
                    rate['price'] = taxes['total_included']
        return rate

    def order_lines_2_google_api(self, order_lines):
        """ Transforms a list of order lines into a dict for google analytics """
        order_lines_not_delivery = order_lines.filtered(lambda line: not line.is_delivery)
        return super(WebsiteSaleDelivery, self).order_lines_2_google_api(order_lines_not_delivery)

    def order_2_return_dict(self, order):
        """ Returns the tracking_cart dict of the order for Google analytics """
        ret = super(WebsiteSaleDelivery, self).order_2_return_dict(order)
        delivery_line = order.order_line.filtered('is_delivery')
        if delivery_line:
            ret['shipping'] = delivery_line.price_unit
        return ret

    def _get_express_shop_payment_values(self, order, **kwargs):
        values = super(WebsiteSaleDelivery, self)._get_express_shop_payment_values(order, **kwargs)
        values['shipping_info_required'] = not order.only_services
        values['shipping_address_update_route'] = self._express_checkout_shipping_route
        return values

    def _get_shop_payment_values(self, order, **kwargs):
        values = super(WebsiteSaleDelivery, self)._get_shop_payment_values(order, **kwargs)
        has_storable_products = any(line.product_id.type in ['consu', 'product'] for line in order.order_line)

        if not order._get_delivery_methods() and has_storable_products:
            values['errors'].append(
                (_('Sorry, we are unable to ship your order'),
                 _('No shipping method is available for your current order and shipping address. '
                   'Please contact us for more information.')))

        if has_storable_products:
            if order.carrier_id and not order.delivery_rating_success:
                order._remove_delivery_line()

            delivery_carriers = order._get_delivery_methods()
            values['deliveries'] = delivery_carriers.sudo()

        values['delivery_has_storable'] = has_storable_products
        values['delivery_action_id'] = request.env.ref('delivery.action_delivery_carrier_form').id
        return values

    def _update_website_sale_delivery_return(self, order, **post):
        Monetary = request.env['ir.qweb.field.monetary']
        carrier_id = int(post['carrier_id'])
        currency = order.currency_id
        if order:
            return {
                'status': order.delivery_rating_success,
                'error_message': order.delivery_message,
                'carrier_id': carrier_id,
                'is_free_delivery': not bool(order.amount_delivery),
                'new_amount_delivery': Monetary.value_to_html(order.amount_delivery, {'display_currency': currency}),
                'new_amount_untaxed': Monetary.value_to_html(order.amount_untaxed, {'display_currency': currency}),
                'new_amount_tax': Monetary.value_to_html(order.amount_tax, {'display_currency': currency}),
                'new_amount_total': Monetary.value_to_html(order.amount_total, {'display_currency': currency}),
                'new_amount_total_raw': order.amount_total,
            }
        return {}
