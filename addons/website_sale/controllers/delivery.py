from odoo import _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request, route
from odoo.libs.debug_log import DebugLog

from odoo.addons.payment import utils as payment_utils
from odoo.addons.website_sale.controllers.main import WebsiteSale

_debug = DebugLog(__name__)


class Delivery(WebsiteSale):
    _express_checkout_delivery_route = "/shop/express/shipping_address_change"

    @route("/shop/delivery_methods", type="jsonrpc", auth="public", website=True)
    def shop_delivery_methods(self):
        order_sudo = request.cart
        values = {
            "delivery_methods": order_sudo._get_delivery_methods(),
            "selected_dm_id": order_sudo.carrier_id.id,
            "order": order_sudo,
        }
        values |= self._prepare_additional_delivery_context()
        return request.env["ir.ui.view"]._render_template(
            "website_sale.delivery_form", values
        )

    def _prepare_additional_delivery_context(self):
        return {}

    @route("/shop/set_delivery_method", type="jsonrpc", auth="public", website=True)
    def shop_set_delivery_method(self, dm_id=None, **kwargs):
        if not (order_sudo := request.cart):
            return {}

        dm_id = int(dm_id)
        if (
            dm_id in order_sudo._get_delivery_methods().ids
            and dm_id != order_sudo.carrier_id.id
        ):
            for tx_sudo in order_sudo.transaction_ids:
                if tx_sudo.state not in ("draft", "cancel", "error"):
                    _debug.logic(
                        "delivery_change_refused",
                        reason="transaction_in_progress",
                        order=order_sudo.id,
                        transaction=tx_sudo.id,
                    )
                    raise UserError(
                        _(
                            "It seems that there is already a transaction for your order; you can't"
                            " change the delivery method anymore."
                        )
                    )

            delivery_method_sudo = (
                request.env["delivery.carrier"].sudo().browse(dm_id).exists()
            )
            _debug.lifecycle(
                "delivery_method_chosen", order=order_sudo.id, carrier=dm_id
            )
            order_sudo._set_delivery_method(delivery_method_sudo)
        return self._order_summary_values(order_sudo, **kwargs)

    def _order_summary_values(self, order, **kwargs):
        Monetary = request.env["ir.qweb.field.monetary"]
        currency = order.currency_id
        return {
            "success": True,
            "is_free_delivery": not bool(order.amount_delivery),
            "compute_price_after_delivery": order.carrier_id.invoice_policy == "real",
            "amount_delivery": Monetary.value_to_html(
                order.amount_delivery, {"display_currency": currency}
            ),
            "amount_untaxed": Monetary.value_to_html(
                order.amount_untaxed, {"display_currency": currency}
            ),
            "amount_tax": Monetary.value_to_html(
                order.amount_tax, {"display_currency": currency}
            ),
            "amount_total": Monetary.value_to_html(
                order.amount_total, {"display_currency": currency}
            ),
        }

    @route(
        "/shop/get_delivery_rate",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def shop_get_delivery_rate(self, dm_id):
        if not (order_sudo := request.cart):
            _debug.logic("delivery_rate_refused", reason="empty_cart")
            raise ValidationError(_("Your cart is empty."))

        if int(dm_id) not in order_sudo._get_delivery_methods().ids:
            _debug.logic(
                "delivery_rate_refused",
                reason="carrier_not_available",
                order=order_sudo.id,
                carrier=int(dm_id),
            )
            raise UserError(
                _(
                    "It seems that a delivery method is not compatible with your address. Please"
                    " refresh the page and try again."
                )
            )

        Monetary = request.env["ir.qweb.field.monetary"]
        delivery_method = (
            request.env["delivery.carrier"].sudo().browse(int(dm_id)).exists()
        )
        rate = Delivery._get_rate(delivery_method, order_sudo)
        if rate["success"]:
            rate["amount_delivery"] = Monetary.value_to_html(
                rate["price"], {"display_currency": order_sudo.currency_id}
            )
            rate["is_free_delivery"] = not bool(rate["price"])
            rate["compute_price_after_delivery"] = (
                delivery_method.invoice_policy == "real"
            )
        else:
            rate["amount_delivery"] = Monetary.value_to_html(
                0.0, {"display_currency": order_sudo.currency_id}
            )
        return rate

    @route(
        "/website_sale/set_pickup_location", type="jsonrpc", auth="public", website=True
    )
    def website_sale_set_pickup_location(self, pickup_location_data):
        order_sudo = request.cart
        order_sudo._set_pickup_location(pickup_location_data)

    @route(
        "/website_sale/get_pickup_locations",
        type="jsonrpc",
        auth="public",
        website=True,
    )
    def website_sale_get_pickup_locations(self, zip_code=None, **kwargs):
        order_sudo = request.cart
        country = order_sudo.partner_shipping_id.country_id
        return order_sudo._get_pickup_locations(zip_code, country, **kwargs)

    @route(
        _express_checkout_delivery_route, type="jsonrpc", auth="public", website=True
    )
    def express_checkout_process_delivery_address(self, partial_delivery_address):
        if not (order_sudo := request.cart):
            return []

        self._include_country_and_state_in_address(partial_delivery_address)
        partial_delivery_address, _side_values = self._parse_form_data(
            partial_delivery_address
        )
        if order_sudo._is_anonymous_cart():
            partial_delivery_address["name"] = _(
                "Anonymous express checkout partner for order %s",
                order_sudo.name,
            )
            new_partner_sudo = self._create_new_address(
                address_values=partial_delivery_address,
                address_type="delivery",
                use_delivery_as_billing=False,
                order_sudo=order_sudo,
            )
            with request.env.protecting(
                [order_sudo._fields["pricelist_id"]], order_sudo
            ):
                order_sudo.partner_id = new_partner_sudo
        elif order_sudo.name in order_sudo.partner_shipping_id.name:
            order_sudo.partner_shipping_id.write(
                self._resolve_address_phone_values(
                    partial_delivery_address, order_sudo.partner_shipping_id
                )
            )
        elif not self._are_same_addresses(
            partial_delivery_address,
            order_sudo.partner_shipping_id,
        ):
            child_partner_id = self._find_child_partner(
                order_sudo.partner_id.commercial_partner_id.id, partial_delivery_address
            )
            partial_delivery_address["name"] = _(
                "Anonymous express checkout partner for order %s",
                order_sudo.name,
            )
            order_sudo.partner_shipping_id = (
                child_partner_id
                or self._create_new_address(
                    address_values=partial_delivery_address,
                    address_type="delivery",
                    use_delivery_as_billing=False,
                    order_sudo=order_sudo,
                )
            )

        sorted_delivery_methods = sorted(
            [
                {
                    "id": dm.id,
                    "name": dm.name,
                    "description": dm.website_description,
                    "minorAmount": payment_utils.major_to_minor_currency_units(
                        price, order_sudo.currency_id
                    ),
                }
                for dm, price in self._get_delivery_methods_express_checkout(
                    order_sudo
                ).items()
            ],
            key=lambda dm: dm["minorAmount"],
        )

        if (
            sorted_delivery_methods
            and order_sudo.carrier_id.id != sorted_delivery_methods[0]["id"]
            and (
                cheapest_dm := next(
                    (
                        dm
                        for dm in order_sudo._get_delivery_methods()
                        if dm.id == sorted_delivery_methods[0]["id"]
                    ),
                    None,
                )
            )
        ):
            order_sudo._set_delivery_method(cheapest_dm)

        return {"delivery_methods": sorted_delivery_methods}

    @classmethod
    def _get_delivery_methods_express_checkout(cls, order_sudo):
        res = {}
        for dm in order_sudo._get_delivery_methods():
            rate = Delivery._get_rate(dm, order_sudo, is_express_checkout_flow=True)
            if rate["success"]:
                fname = f"{dm.delivery_type}_use_locations"
                if hasattr(dm, fname) and getattr(dm, fname):
                    continue
                res[dm] = rate["price"]
        return res

    @staticmethod
    def _get_rate(delivery_method, order, is_express_checkout_flow=False):
        rate = delivery_method.rate_shipment(
            order.with_context(
                express_checkout_partial_delivery_address=is_express_checkout_flow
            )
        )
        if rate.get("success"):
            tax_ids = delivery_method.product_id.taxes_id.filtered(
                lambda t: order.company_id in t.company_ids
            )
            if tax_ids:
                fpos = order.fiscal_position_id
                tax_ids = fpos.map_tax(tax_ids)
                taxes = tax_ids.compute_all(
                    rate["price"],
                    currency=order.currency_id,
                    quantity=1.0,
                    product=delivery_method.product_id,
                    partner=order.partner_shipping_id,
                )
                if (
                    not is_express_checkout_flow
                    and request.website.show_line_subtotals_tax_selection
                    == "tax_excluded"
                ):
                    rate["price"] = taxes["total_excluded"]
                else:
                    rate["price"] = taxes["total_included"]
        return rate
