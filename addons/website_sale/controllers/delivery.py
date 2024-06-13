# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request, route

from odoo.addons.payment import utils as payment_utils
from odoo.addons.website_sale.controllers.main import WebsiteSale


class Delivery(WebsiteSale):
    _express_checkout_delivery_route = '/shop/express/shipping_address_change'

    @route('/shop/delivery_methods', type='json', auth='public', website=True)
    def shop_delivery_methods(self):
        """ Fetch available delivery methods and render them in the delivery form.

        :return: The rendered delivery form.
        :rtype: str
        """
        order_sudo = request.website.sale_get_order()
        values = {
            'delivery_methods': order_sudo._get_delivery_methods(),
            'selected_dm_id': order_sudo.carrier_id.id,
        }
        values |= self._get_additional_delivery_context()
        return request.env['ir.ui.view']._render_template('website_sale.delivery_form', values)

    def _get_additional_delivery_context(self):
        """ Hook to update values used for rendering the website_sale.delivery_form template. """
        return {}

    @route('/shop/set_delivery_method', type='json', auth='public', website=True)
    def shop_set_delivery_method(self, dm_id=None, **kwargs):
        """ Set the delivery method on the current order and return the order summary values.

        If the delivery method is already set, the order summary values are returned immediately.

        :param str dm_id: The delivery method to set, as a `delivery.carrier` id.
        :param dict kwargs: The keyword arguments forwarded to `_order_summary_values`.
        :return: The order summary values, if any.
        :rtype: dict
        """
        order_sudo = request.website.sale_get_order()
        if not order_sudo:
            return {}

        dm_id = int(dm_id)
        if dm_id != order_sudo.carrier_id.id:
            for tx_sudo in order_sudo.transaction_ids:
                if tx_sudo.state not in ('draft', 'cancel', 'error'):
                    raise UserError(_(
                        "It seems that there is already a transaction for your order; you can't"
                        " change the delivery method anymore."
                    ))

            delivery_method_sudo = request.env['delivery.carrier'].sudo().browse(dm_id).exists()
            order_sudo._set_delivery_method(delivery_method_sudo)
        return self._order_summary_values(order_sudo, **kwargs)

    def _order_summary_values(self, order, **kwargs):
        """ Return the summary values of the order.

        :param sale.order order: The sales order whose summary values to return.
        :param dict kwargs: The keyword arguments. This parameter is not used here.
        :return: The order summary values.
        :rtype: dict
        """
        Monetary = request.env['ir.qweb.field.monetary']
        currency = order.currency_id
        return {
            'success': True,
            'is_free_delivery': not bool(order.amount_delivery),
            'amount_delivery': Monetary.value_to_html(
                order.amount_delivery, {'display_currency': currency}
            ),
            'amount_untaxed': Monetary.value_to_html(
                order.amount_untaxed, {'display_currency': currency}
            ),
            'amount_tax': Monetary.value_to_html(
                order.amount_tax, {'display_currency': currency}
            ),
            'amount_total': Monetary.value_to_html(
                order.amount_total, {'display_currency': currency}
            ),
        }

    @route('/shop/get_delivery_rate', type='json', auth='public', methods=['POST'], website=True)
    def shop_get_delivery_rate(self, dm_id):
        """ Return the delivery rate data for the given delivery method.

        :param str dm_id: The delivery method whose rate to get, as a `delivery.carrier` id.
        :return: The delivery rate data.
        :rtype: dict
        """
        order = request.website.sale_get_order()
        if not order:
            raise ValidationError(_("Your cart is empty."))

        if int(dm_id) not in order._get_delivery_methods().ids:
            raise UserError(_(
                "It seems that a delivery method is not compatible with your address. Please"
                " refresh the page and try again."
            ))

        Monetary = request.env['ir.qweb.field.monetary']
        delivery_method = request.env['delivery.carrier'].sudo().browse(int(dm_id)).exists()
        rate = Delivery._get_rate(delivery_method, order)
        if rate['success']:
            rate['amount_delivery'] = Monetary.value_to_html(
                rate['price'], {'display_currency': order.currency_id}
            )
            rate['is_free_delivery'] = not bool(rate['price'])
        else:
            rate['amount_delivery'] = Monetary.value_to_html(
                0.0, {'display_currency': order.currency_id}
            )
        return rate

    @route('/shop/get_pickup_location', type='json', auth='public', website=True)
    def shop_get_pickup_location(self):
        """ Return the pickup location that is set on the current order.

        :return: The pickup location set on the current order, if any.
        :rtype: dict|None
        """
        order = request.website.sale_get_order()
        if not order.carrier_id.delivery_type or not order.carrier_id.display_name:
            return {}

        order_location = order.access_point_address
        if not order_location:
            return {}

        address = order_location['address']
        name = order_location['pick_up_point_name']
        return {
            'pickup_address': address,
            'name': name,
            'delivery_name': order.carrier_id.display_name,
        }

    @route('/shop/set_pickup_location', type='json', auth='public', website=True)
    def set_pickup_location(self, pickup_location_data):
        """ Set the pickup location on the current order.

        :param str pickup_location_data: The JSON-formatted pickup location address.
        :return: None
        """
        order = request.website.sale_get_order()
        use_locations_fname = f'{order.carrier_id.delivery_type}_use_locations'
        if hasattr(order.carrier_id, use_locations_fname):
            use_location = getattr(order.carrier_id, use_locations_fname)
            if use_location and pickup_location_data:
                pickup_location = json.loads(pickup_location_data)
            else:
                pickup_location = None
            order.access_point_address = pickup_location

    @route('/shop/get_close_locations', type='json', auth='public', website=True)
    def shop_get_close_locations(self):
        """ Return the pickup locations of the delivery method close to the order delivery address.

        :return: The close pickup location data.
        :rtype: dict
        """
        order = request.website.sale_get_order()
        try:
            error = {'error': _("No pick-up point available for that shipping address")}
            function_name = f'_{order.carrier_id.delivery_type}_get_close_locations'
            if not hasattr(order.carrier_id, function_name):
                return error

            close_locations = getattr(order.carrier_id, function_name)(order.partner_shipping_id)
            partner_address = order.partner_shipping_id
            inline_partner_address = ' '.join((part or '') for part in [
                partner_address.street,
                partner_address.street2,
                partner_address.zip,
                partner_address.country_id.code
            ])
            if not close_locations:
                return error

            for location in close_locations:
                location['address_stringified'] = json.dumps(location)
            return {'close_locations': close_locations, 'partner_address': inline_partner_address}
        except UserError as e:
            return {'error': str(e)}

    @route(_express_checkout_delivery_route, type='json', auth='public', website=True)
    def express_checkout_process_delivery_address(self, partial_delivery_address):
        """ Process the shipping address and return the available delivery methods.

        Depending on whether the partner is registered and logged in, a new partner is created or we
        use an existing partner that matches the partial delivery address received.

        :param dict partial_delivery_address: The delivery information sent by the express payment
                                              provider.
        :return: The available delivery methods, sorted by lowest price.
        :rtype: dict
        """
        order_sudo = request.website.sale_get_order()
        public_partner = request.website.partner_id

        self._include_country_and_state_in_address(partial_delivery_address)
        if order_sudo.partner_id == public_partner:
            # The partner_shipping_id and partner_invoice_id will be automatically computed when
            # changing the partner_id of the SO. This avoids website_sale creating duplicates.
            order_sudo.partner_id = self._create_or_edit_partner(
                partial_delivery_address,
                type='delivery',
                name=_("Anonymous express checkout partner for order %s", order_sudo.name),
            )
            # Pricelists are recomputed every time the partner is changed. We don't want to
            # recompute the price with another pricelist at this state since the customer has
            # already accepted the amount and validated the payment.
            order_sudo.env.remove_to_compute(order_sudo._fields['pricelist_id'], order_sudo)
        elif order_sudo.partner_shipping_id.name.endswith(order_sudo.name):
            self._create_or_edit_partner(
                partial_delivery_address,
                edit=True,
                type='delivery',
                partner_id=order_sudo.partner_shipping_id.id,
            )
        elif any(
            partial_delivery_address[k] != order_sudo.partner_shipping_id[k]
            for k in partial_delivery_address
        ):
            # Check if a child partner doesn't already exist with the same information. The phone
            # isn't always checked because it isn't sent in delivery information with Google Pay.
            child_partner_id = self._find_child_partner(
                order_sudo.partner_id.commercial_partner_id.id, partial_delivery_address
            )
            order_sudo.partner_shipping_id = child_partner_id or self._create_or_edit_partner(
                partial_delivery_address,
                type='delivery',
                parent_id=order_sudo.partner_id.id,
                name=_("Anonymous express checkout partner for order %s", order_sudo.name),
            )

        # Return the list of delivery methods available for the sales order.
        return sorted([{
            'id': dm.id,
            'name': dm.name,
            'description': dm.website_description,
            'minorAmount': payment_utils.to_minor_currency_units(price, order_sudo.currency_id),
        } for dm, price in Delivery._get_delivery_methods_express_checkout(order_sudo).items()
        ], key=lambda dm: dm['minorAmount'])

    @staticmethod
    def _get_delivery_methods_express_checkout(order_sudo):
        """ Return available delivery methods and their prices for the given order.

        :param sale.order order_sudo: The sudoed sales order.
        :rtype: dict
        :return: A dict with a `delivery.carrier` recordset as key, and a rate shipment price as
                 value.
        """
        res = {}
        for dm in order_sudo._get_delivery_methods():
            rate = Delivery._get_rate(dm, order_sudo, is_express_checkout_flow=True)
            if rate['success']:
                fname = f'{dm.delivery_type}_use_locations'
                if hasattr(dm, fname) and getattr(dm, fname):
                    continue  # Express checkout doesn't allow selecting locations.
                res[dm] = rate['price']
        return res

    @staticmethod
    def _get_rate(delivery_method, order, is_express_checkout_flow=False):
        """ Compute the delivery rate and apply the taxes if relevant.

        :param delivery.carrier delivery_method: The delivery method for which the rate must be
                                                 computed.
        :param sale.order order: The current sales order.
        :param boolean is_express_checkout_flow: Whether the flow is express checkout.
        :return: The delivery rate data.
        :rtype: dict
        """
        # Some delivery methods check if all the required fields are available before computing the
        # rate, even if those fields aren't required for the computation (although they are for
        # delivering the goods). If we only have partial information about the delivery address, but
        # still want to compute the rate, this context key will ensure that we only check the
        # required fields for a partial delivery address (city, zip, country_code, state_code).
        rate = delivery_method.rate_shipment(order.with_context(
            express_checkout_partial_delivery_address=is_express_checkout_flow
        ))
        if rate.get('success'):
            tax_ids = delivery_method.product_id.taxes_id.filtered(
                lambda t: t.company_id == order.company_id
            )
            if tax_ids:
                fpos = order.fiscal_position_id
                tax_ids = fpos.map_tax(tax_ids)
                taxes = tax_ids.compute_all(
                    rate['price'],
                    currency=order.currency_id,
                    quantity=1.0,
                    product=delivery_method.product_id,
                    partner=order.partner_shipping_id,
                )
                if (
                    not is_express_checkout_flow
                    and request.website.show_line_subtotals_tax_selection == 'tax_excluded'
                ):
                    rate['price'] = taxes['total_excluded']
                else:
                    rate['price'] = taxes['total_included']
        return rate
