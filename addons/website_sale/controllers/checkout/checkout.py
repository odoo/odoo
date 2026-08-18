# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.tools import str2bool
from odoo.tools.translate import LazyTranslate

from odoo.addons.payment.controllers import portal as payment_portal

_lt = LazyTranslate(__name__)


class Checkout(payment_portal.PaymentPortal):
    def _prepare_checkout_page_values(self, order_sudo, **kwargs):
        """Provide the data used to render the /shop/checkout page.

        :param sale.order order_sudo: The current cart.
        :param dict kwargs: unused parameters available for potential overrides.
        :return: The checkout page rendering values.
        :rtype: dict
        """
        partner_sudo = order_sudo.partner_id
        return {
            "order": order_sudo,
            "website_sale_order": order_sudo,  # Compatibility with other templates.
            "use_delivery_as_billing": (
                order_sudo.partner_shipping_id == order_sudo.partner_invoice_id
            ),
            "only_services": order_sudo.only_services,
            **self._prepare_address_data(partner_sudo, order_sudo=order_sudo, **kwargs),
            "address_url": "/shop/address",
        }

    @route(
        "/shop/checkout",
        type="http",
        methods=["GET"],
        auth="public",
        website=True,
        sitemap=False,
        list_as_website_content=_lt("Shop Checkout"),
    )
    def shop_checkout(self, try_skip_step=None, **query_params):
        """Display the checkout page.

        :param str try_skip_step: Whether the user should immediately be redirected to the next step
                                  if no additional information (i.e., address or delivery method) is
                                  required on the checkout page. 'true' or 'false'.
        :param dict query_params: The additional query string parameters.
        :return: The rendered checkout page.
        :rtype: str
        """
        try_skip_step = str2bool(try_skip_step or "false")
        order_sudo = request.cart

        if redirect := self.env["website.checkout.step"].validate_checkout_progress(
            "/shop/checkout", order_sudo
        ):
            return request.redirect(redirect)

        request.session["sale_last_order_id"] = order_sudo.id
        checkout_page_values = self._prepare_checkout_page_values(order_sudo, **query_params)

        can_skip_delivery = True  # Delivery is only needed for deliverable products.
        if order_sudo._has_deliverable_products():
            can_skip_delivery = False
            available_dms = order_sudo._get_delivery_methods()
            checkout_page_values["delivery_methods"] = available_dms
            if delivery_method := order_sudo._get_preferred_delivery_method(available_dms):
                rate = delivery_method.rate_shipment(order_sudo)
                if (
                    not order_sudo.carrier_id
                    or not rate.get("success")
                    or order_sudo.amount_delivery != rate["price"]
                ):
                    order_sudo._set_delivery_method(delivery_method, rate=rate)

        checkout_page_values.update(self.env.website._get_checkout_step_values("/shop/checkout"))
        if try_skip_step and can_skip_delivery:
            return request.redirect(checkout_page_values["next_website_checkout_step_href"])

        return request.render("website_sale.checkout", checkout_page_values)
