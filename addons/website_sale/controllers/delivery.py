# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
            'order': order_sudo,  # Needed for accessing default values for pickup points.
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
        if dm_id in order_sudo._get_delivery_methods().ids and dm_id != order_sudo.carrier_id.id:
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
            'compute_price_after_delivery': order.carrier_id.invoice_policy == 'real',
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
            rate['compute_price_after_delivery'] = delivery_method.invoice_policy == 'real'
        else:
            rate['amount_delivery'] = Monetary.value_to_html(
                0.0, {'display_currency': order.currency_id}
            )
        return rate

    @route('/website_sale/set_pickup_location', type='json', auth='public', website=True)
    def website_sale_set_pickup_location(self, pickup_location_data):
        """ Fetch the order from the request and set the pickup location on the current order.

        :param str pickup_location_data: The JSON-formatted pickup location address.
        :return: None
        """
        order_sudo = request.website.sale_get_order()
        order_sudo._set_pickup_location(pickup_location_data)

    @route('/website_sale/get_pickup_locations', type='json', auth='public', website=True)
    def website_sale_get_pickup_locations(self, zip_code=None, **kwargs):
        """ Fetch the order from the request and return the pickup locations close to the zip code.

        Determine the country based on GeoIP or fallback on the order's delivery address' country.

        :param int zip_code: The zip code to look up to.
        :return: The close pickup locations data.
        :rtype: dict
        """
        order_sudo = request.website.sale_get_order()
        country = order_sudo.partner_shipping_id.country_id
        return order_sudo._get_pickup_locations(zip_code, country, **kwargs)

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
        if not order_sudo:
            return []

        self._include_country_and_state_in_address(partial_delivery_address)
        partial_delivery_address, _side_values = self._parse_form_data(partial_delivery_address)
        if order_sudo._is_anonymous_cart():
            # The partner_shipping_id and partner_invoice_id will be automatically computed when
            # changing the partner_id of the SO. This allows website_sale to avoid creating
            # duplicates.
            partial_delivery_address['name'] = _(
                'Anonymous express checkout partner for order %s',
                order_sudo.name,
            )
            new_partner_sudo = self._create_new_address(
                address_values=partial_delivery_address,
                address_type='delivery',
                use_delivery_as_billing=False,
                order_sudo=order_sudo,
            )
            # Pricelists are recomputed every time the partner is changed. We don't want to
            # recompute the price with another pricelist at this state since the customer has
            # already accepted the amount and validated the payment.
            with request.env.protecting([order_sudo._fields['pricelist_id']], order_sudo):
                order_sudo.partner_id = new_partner_sudo
        elif order_sudo.name in order_sudo.partner_shipping_id.name:
            order_sudo.partner_shipping_id.write(partial_delivery_address)
            # TODO VFE TODO VCR do we want to trigger cart recomputation here ?
            # order_sudo._update_address(
            #     order_sudo.partner_shipping_id.id, ['partner_shipping_id']
            # )
        elif not self._are_same_addresses(
            partial_delivery_address,
            order_sudo.partner_shipping_id,
        ):
            # Check if a child partner doesn't already exist with the same information. The phone
            # isn't always checked because it isn't sent in delivery information with Google Pay.
            child_partner_id = self._find_child_partner(
                order_sudo.partner_id.commercial_partner_id.id, partial_delivery_address
            )
            partial_delivery_address['name'] = _(
                'Anonymous express checkout partner for order %s',
                order_sudo.name,
            )
            order_sudo.partner_shipping_id = child_partner_id or self._create_new_address(
                address_values=partial_delivery_address,
                address_type='delivery',
                use_delivery_as_billing=False,
                order_sudo=order_sudo,
            )

        sorted_delivery_methods = sorted([{
            'id': dm.id,
            'name': dm.name,
            'description': dm.website_description,
            'minorAmount': payment_utils.to_minor_currency_units(price, order_sudo.currency_id),
        } for dm, price in self._get_delivery_methods_express_checkout(order_sudo).items()
        ], key=lambda dm: dm['minorAmount'])

        # Preselect the cheapest method imitating the behavior of the express checkout form.
        if (
            sorted_delivery_methods
            and order_sudo.carrier_id.id != sorted_delivery_methods[0]['id']
            and (cheapest_dm := next((
                dm for dm in order_sudo._get_delivery_methods()
                if dm.id == sorted_delivery_methods[0]['id']), None
            ))
        ):
            order_sudo._set_delivery_method(cheapest_dm)

        # Return the list of delivery methods available for the sales order.
        return {'delivery_methods': sorted_delivery_methods}

    @classmethod
    def _get_delivery_methods_express_checkout(cls, order_sudo):
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
