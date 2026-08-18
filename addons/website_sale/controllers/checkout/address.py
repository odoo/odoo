# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden

from odoo.http import request, route
from odoo.tools import clean_context, str2bool

from odoo.addons.payment.controllers import portal as payment_portal


class Address(payment_portal.PaymentPortal):
    _express_checkout_route = "/shop/express_checkout"
    _express_checkout_delivery_route = "/shop/express/shipping_address_change"

    def _prepare_address_update(self, order_sudo, partner_id=None, address_type=None):
        """Find the partner whose address to update and return it along with its address type.

        :param sale.order order_sudo: The current cart.
        :param int partner_id: The partner whose address to update, if any, as a `res.partner` id.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :return: The partner whose address to update, if any, and its address type.
        :rtype: tuple[res.partner, str]
        :raise Forbidden: If the customer is not allowed to update the given address.
        """
        PartnerSudo = self.env["res.partner"].with_context(show_address=1).sudo()
        if order_sudo._is_anonymous_cart():
            partner_sudo = PartnerSudo
        else:
            partner_sudo = PartnerSudo.browse(partner_id)
            if partner_sudo and partner_sudo not in {
                order_sudo.partner_id,
                order_sudo.partner_invoice_id,
                order_sudo.partner_shipping_id,
            }:  # The partner is not yet linked to the SO.
                partner_sudo = partner_sudo.exists()

        if partner_sudo and not address_type:  # The desired address type was not specified.
            # Identify the address type based on the cart's billing and delivery partners.
            if partner_id == order_sudo.partner_invoice_id.id:
                address_type = "billing"
            elif partner_id == order_sudo.partner_shipping_id.id:
                address_type = "delivery"
            else:
                address_type = "billing"

        if partner_sudo and not partner_sudo._can_be_edited_by_current_customer(
            order_sudo=order_sudo
        ):
            raise Forbidden

        return partner_sudo, address_type

    def _prepare_address_form_values(self, *args, callback="", order_sudo=False, **kwargs):
        """Prepare the rendering values of the address form.

        :param str callback: The URL to redirect to in case of successful address creation/update.
        :param sale.order order_sudo: The current cart.
        :return: The checkout page values.
        :rtype: dict
        """
        rendering_values = super()._prepare_address_form_values(
            *args, order_sudo=order_sudo, callback=callback, **kwargs
        )
        if not order_sudo:  # Return portal address values if not order
            return rendering_values

        is_anonymous_cart = order_sudo._is_anonymous_cart()
        # Display b2b field is feature is enabled on given website
        rendering_values["display_b2b_fields"] = rendering_values.get(
            "display_b2b_fields", False
        ) or self.env.website.is_view_active("website_sale.address_b2b")

        if rendering_values["commercial_address_update_url"]:
            rendering_values["commercial_address_update_url"] = (
                f"/shop/address?partner_id={order_sudo.partner_id.id}"
            )

        return {
            **rendering_values,
            "is_anonymous_cart": is_anonymous_cart,
            "website_sale_order": order_sudo,
            "only_services": order_sudo.only_services,
            "discard_url": callback or (is_anonymous_cart and "/shop/cart") or "/shop/checkout",
        }

    def _get_default_country(self, order_sudo=False, **kwargs):
        """Override `portal` to return country of customer if customer is not logged in."""
        is_anonymous_cart = order_sudo and order_sudo._is_anonymous_cart()
        if is_anonymous_cart and request.geoip.country_code:
            return (
                self
                .env["res.country"]
                .sudo()
                .search([("code", "=", request.geoip.country_code)], limit=1)
            )
        return super()._get_default_country(order_sudo=order_sudo, **kwargs)

    @route(
        "/shop/address", type="http", methods=["GET"], auth="public", website=True, sitemap=False
    )
    def shop_address(
        self, partner_id=None, address_type="billing", use_delivery_as_billing=None, **query_params
    ):
        """Display the address form.

        A partner and/or an address type can be given through the query string params to specify
        which address to update or create, and its type.

        :param str partner_id: The partner whose address to update with the address form, if any.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param str use_delivery_as_billing: Whether the provided address should be used as both the
                                            delivery and the billing address. 'true' or 'false'.
        :param dict query_params: The additional query string parameters forwarded to
                                  `_prepare_address_form_values`.
        :return: The rendered address form.
        :rtype: str
        """
        use_delivery_as_billing = str2bool(use_delivery_as_billing or "false")
        order_sudo = request.cart

        if redirect := self.env["website.checkout.step"].validate_checkout_progress(
            "/shop/address", order_sudo
        ):
            return request.redirect(redirect)

        # Retrieve the partner whose address to update, if any, and its address type.
        partner_sudo, address_type = self._prepare_address_update(
            order_sudo, partner_id=partner_id and int(partner_id), address_type=address_type
        )

        use_delivery_as_billing = str2bool(use_delivery_as_billing or "false")
        if partner_sudo:  # If editing an existing partner.
            use_delivery_as_billing = (
                partner_sudo == order_sudo.partner_shipping_id == order_sudo.partner_invoice_id
            )

        # Render the address form.
        address_form_values = self._prepare_address_form_values(
            partner_sudo,
            address_type=address_type,
            order_sudo=order_sudo,
            use_delivery_as_billing=use_delivery_as_billing,
            **query_params,
        )
        address_form_values.update(self.env.website._get_checkout_step_values("/shop/address"))
        return request.render("website_sale.address", address_form_values)

    def _complete_address_values(self, address_values, *args, order_sudo=False, **kwargs):
        super()._complete_address_values(address_values, *args, order_sudo=order_sudo, **kwargs)

        if order_sudo and order_sudo._is_anonymous_cart():
            address_values["type"] = "contact"

        if address_values["lang"] not in self.env.website.mapped("language_ids.code"):
            address_values.pop("lang")

        if not order_sudo:
            return
        address_values["company_id"] = (
            order_sudo.website_id.company_id.id or address_values["company_id"]
        )
        address_values["user_id"] = order_sudo.website_id.salesperson_id.id

        if order_sudo.website_id.specific_user_account:
            address_values["website_id"] = order_sudo.website_id.id

    def _create_new_address(
        self, address_values, address_type, use_delivery_as_billing, order_sudo
    ):
        """Create a new partner, must be called after the data has been verified.

        NB: to verify (and preprocess) the data, please call `_parse_form_data` first.

        :param order_sudo: the current cart, as a sudoed `sale.order` recordset
        :param str address_type: 'billing' or 'delivery'
        :param bool use_delivery_as_billing: Whether the address must be used as the billing and the
                                             delivery address.
        :param dict address_values: values to use to create the partner

        :return: The created address, as a sudoed `res.partner` recordset.
        """
        self._complete_address_values(
            address_values, address_type, use_delivery_as_billing, order_sudo=order_sudo
        )
        creation_context = clean_context(self.env.context)
        creation_context.update({
            # 'no_vat_validation': True,  # TODO VCR VAT validation or not ?
        })
        return self.env["res.partner"].sudo().with_context(creation_context).create(address_values)

    @route(
        "/shop/address/submit",
        type="http",
        methods=["POST"],
        auth="public",
        website=True,
        sitemap=False,
    )
    def shop_address_submit(
        self,
        partner_id=None,
        address_type="billing",
        use_delivery_as_billing=None,
        callback=None,
        **form_data,
    ):
        """Create or update an address.

        If it succeeds, it returns the URL to redirect (client-side) to. If it fails (missing or
        invalid information), it highlights the problematic form input with the appropriate error
        message.

        :param str partner_id: The partner whose address to update with the address form, if any.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param str use_delivery_as_billing: Whether the provided address should be used as both the
                                            billing and the delivery address. 'true' or 'false'.
        :param str callback: The URL to redirect to in case of successful address creation/update.
        :param dict form_data: The form data to process as address values.
        :return: A JSON-encoded feedback, with either the success URL or an error message.
        :rtype: str
        """
        order_sudo = request.cart
        redirect_dict = {}
        if redirect := self.env["website.checkout.step"].validate_checkout_progress(
            "/shop/address", order_sudo
        ):
            # Delay the redirection to save the address update
            redirect_dict["redirectUrl"] = redirect

        # Retrieve the partner whose address to update, if any, and its address type.
        partner_sudo, address_type = self._prepare_address_update(
            order_sudo, partner_id=partner_id and int(partner_id), address_type=address_type
        )

        is_new_address = not partner_sudo
        if is_new_address or order_sudo.only_services:
            callback = callback or "/shop/checkout?try_skip_step=true"
        else:
            callback = callback or "/shop/checkout"

        partner_sudo, feedback_dict = self._create_or_update_address(
            partner_sudo,
            address_type=address_type,
            use_delivery_as_billing=use_delivery_as_billing,
            callback=callback,
            order_sudo=order_sudo,
            **form_data,
        )

        if feedback_dict.get("invalid_fields"):
            # Return if error when creating/updating partner.
            return request.make_json_response(feedback_dict)

        is_anonymous_cart = order_sudo._is_anonymous_cart()
        is_main_address = is_anonymous_cart or order_sudo.partner_id.id == partner_sudo.id
        partner_fnames = set()
        if is_main_address:  # Main customer address updated.
            partner_fnames.add("partner_id")  # Force the re-computation of partner-based fields.

        if address_type == "billing":
            partner_fnames.add("partner_invoice_id")
            if is_new_address and order_sudo.only_services:
                # The delivery address is required to make the order.
                partner_fnames.add("partner_shipping_id")
        elif address_type == "delivery":
            partner_fnames.add("partner_shipping_id")
            if use_delivery_as_billing:
                partner_fnames.add("partner_invoice_id")

        order_sudo._update_address(partner_sudo.id, partner_fnames)

        if order_sudo._is_anonymous_cart():
            # Unsubscribe the public partner if the cart was previously anonymous.
            order_sudo.message_unsubscribe(order_sudo.website_id.partner_id.ids)

        if redirect_dict:
            # Redirect after the address is complete and saved
            return request.make_json_response(redirect_dict)

        return request.make_json_response(feedback_dict)

    def _find_child_partner(self, commercial_partner_id, address):
        """Find a child partner for a specified address.

        Compare all keys in the `address` dict with the same keys on the partner object and return
        the id of the first partner that have the same value than in the dict for all the keys.

        :param int commercial_partner_id: The commercial partner whose child to find.
        :param dict address: The address fields.
        :return: The ID of the first child partner that match the criteria, if any.
        :rtype: int
        """
        partners_sudo = (
            self
            .env["res.partner"]
            .with_context(show_address=1)
            .sudo()
            .search([("id", "child_of", commercial_partner_id)])
        )
        for partner_sudo in partners_sudo:
            if self._are_same_addresses(address, partner_sudo):
                return partner_sudo.id
        return False

    def _include_country_and_state_in_address(self, address):
        """Include country_id and state_id in address.

        Fetch country and state and include the records in address. The object is included to
        simplify the comparison of addresses.

        :param dict address: An address with country and state defined in ISO 3166.
        :return None:
        """
        country = self.env["res.country"].search([("code", "=", address.pop("country"))], limit=1)
        state_id = False
        if state_code := address.pop("state", False):
            state_id = country.state_ids.filtered(lambda state: state.code == state_code).id
        address.update(country_id=country.id, state_id=state_id)

    @route(
        _express_checkout_route,
        type="jsonrpc",
        methods=["POST"],
        auth="public",
        website=True,
        sitemap=False,
    )
    def process_express_checkout(
        self, billing_address, shipping_address=None, shipping_option=None, **_kwargs
    ):
        """Record the partner information on the order when using express checkout flow.

        Depending on whether the partner is registered and logged in, either creates a new partner
        or uses an existing one that matches all received data.

        :param dict billing_address: Billing information sent by the express payment form.
        :param dict shipping_address: Shipping information sent by the express payment form.
        :param dict shipping_option: Carrier information sent by the express payment form.
        :param dict kwargs: Optional data. This parameter is not used here.
        :return int: The order's partner id.
        """
        order_sudo = request.cart

        # Update the partner with all the information
        self._include_country_and_state_in_address(billing_address)
        billing_address, _side_values = self._parse_form_data(billing_address)
        if order_sudo._is_anonymous_cart():
            # Pricelist are recomputed every time the partner is changed. We don't want to recompute
            # the price with another pricelist at this state since the customer has already accepted
            # the amount and validated the payment.
            new_partner_sudo = self._create_new_address(
                billing_address,
                address_type="billing",
                use_delivery_as_billing=False,
                order_sudo=order_sudo,
            )
            with self.env.protecting([order_sudo._fields["pricelist_id"]], order_sudo):
                order_sudo.partner_id = new_partner_sudo
        elif not self._are_same_addresses(billing_address, order_sudo.partner_invoice_id):
            # Check if a child partner doesn't already exist with the same informations. The
            # phone isn't always checked because it isn't sent in shipping information with
            # Google Pay.
            child_partner_id = self._find_child_partner(
                order_sudo.partner_id.commercial_partner_id.id, billing_address
            )
            order_sudo.partner_invoice_id = child_partner_id or self._create_new_address(
                billing_address,
                address_type="billing",
                use_delivery_as_billing=False,
                order_sudo=order_sudo,
            )

        # In a non-express flow, `sale_last_order_id` would be added in the session before the
        # payment. As we skip all the steps with the express checkout, `sale_last_order_id` must be
        # assigned to ensure the right behavior from `shop_payment_confirmation()`.
        request.session["sale_last_order_id"] = order_sudo.id

        if shipping_address:
            # in order to not override shippig address, it's checked separately from shipping option
            self._include_country_and_state_in_address(shipping_address)
            shipping_address, _side_values = self._parse_form_data(shipping_address)

            if order_sudo.name in order_sudo.partner_shipping_id.name:
                # The existing partner was created by `process_express_checkout_delivery_choice`, it
                # means that the partner is missing information, so we update it.
                order_sudo.partner_shipping_id.write(shipping_address)
                order_sudo._update_address(
                    order_sudo.partner_shipping_id.id, ["partner_shipping_id"]
                )
            elif not self._are_same_addresses(shipping_address, order_sudo.partner_shipping_id):
                # The sale order's shipping partner's address is different from the one received. If
                # all the sale order's child partners' address differs from the one received, we
                # create a new partner. The phone isn't always checked because it isn't sent in
                # shipping information with Google Pay.
                child_partner_id = self._find_child_partner(
                    order_sudo.partner_id.commercial_partner_id.id, shipping_address
                )
                order_sudo.partner_shipping_id = child_partner_id or self._create_new_address(
                    shipping_address,
                    address_type="delivery",
                    use_delivery_as_billing=False,
                    order_sudo=order_sudo,
                )
            # Process the delivery method.
            if shipping_option:
                dm_id = int(shipping_option["id"])
                available_dms = order_sudo._get_delivery_methods()
                order_sudo._set_delivery_method(available_dms.filtered(lambda dm: dm.id == dm_id))

        return order_sudo.partner_id.id

    @route("/shop/update_address", type="jsonrpc", auth="public", website=True)
    def shop_update_address(
        self, partner_id, address_type="billing", use_delivery_as_billing=False, **_kw
    ):
        partner_id = int(partner_id)

        if not (order_sudo := request.cart):
            return

        ResPartner = self.env["res.partner"].sudo()
        partner_sudo = ResPartner.browse(partner_id).exists()
        children = ResPartner._search([
            ("id", "child_of", order_sudo.partner_id.commercial_partner_id.id),
            ("type", "in", ("invoice", "delivery", "other")),
        ])
        if (
            partner_sudo not in {order_sudo.partner_id, order_sudo.partner_id.commercial_partner_id}
            and partner_sudo.id not in children
        ):
            raise Forbidden

        partner_fnames = set()
        if (
            use_delivery_as_billing or address_type == "billing"
        ) and partner_sudo != order_sudo.partner_invoice_id:
            partner_fnames.add("partner_invoice_id")
        if address_type == "delivery" and partner_sudo != order_sudo.partner_shipping_id:
            partner_fnames.add("partner_shipping_id")

        order_sudo._update_address(partner_id, partner_fnames)
