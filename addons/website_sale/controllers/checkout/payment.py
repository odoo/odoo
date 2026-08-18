# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2.errors import LockNotAvailable

from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.fields import Command
from odoo.http import request, route
from odoo.tools import SQL
from odoo.tools.translate import LazyTranslate

from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.sale.controllers import portal as sale_portal
from odoo.addons.website_sale.const import SHOP_PATH

_lt = LazyTranslate(__name__)


class Payment(payment_portal.PaymentPortal):
    def _validate_transaction_for_order(self, _transaction, _sale_order):
        """
        Perform final checks against the transaction & sale_order.
        Override me to apply payment unrelated checks & processing.
        """
        return

    @route("/shop/payment/transaction/<int:order_id>", type="jsonrpc", auth="public", website=True)
    def shop_payment_transaction(self, order_id, access_token, **kwargs):
        """Create a draft transaction and return its processing values.

        :param int order_id: The sales order to pay, as a `sale.order` id
        :param str access_token: The access token used to authenticate the request
        :param dict kwargs: Locally unused data passed to `_create_transaction`
        :return: The mandatory values for the processing of the transaction
        :rtype: dict
        :raise: UserError if the order has already been paid or has an ongoing transaction
        :raise: ValidationError if the access token is invalid or the order is not in the expected
            state/configuration.
        """
        # Check the order id and the access token
        # Then lock it during the transaction to prevent concurrent payments
        try:
            order_sudo = self._document_check_access("sale.order", order_id, access_token)
            self.env.cr.execute(
                SQL("SELECT 1 FROM sale_order WHERE id = %s FOR NO KEY UPDATE NOWAIT", order_id)
            )
        except MissingError:
            raise
        except AccessError as e:
            raise ValidationError(self.env._("The access token is invalid.")) from e
        except LockNotAvailable as lna:
            raise UserError(self.env._("Payment is already being processed.")) from lna

        if order_sudo.state == "cancel":
            raise ValidationError(self.env._("The order has been cancelled."))

        # Ensure the cart is still valid before proceeding any further.
        if redirect := self.env["website.checkout.step"].validate_checkout_progress(
            "/shop/payment/transaction", order_sudo
        ):
            return {
                "state": "error",
                "state_message": order_sudo._join_alert_messages(),
                "redirect": redirect,
            }

        self._validate_transaction_kwargs(kwargs)
        kwargs.update({
            "partner_id": order_sudo.partner_invoice_id.id,
            "currency_id": order_sudo.currency_id.id,
            "sale_order_id": order_id,  # Include the SO to allow Subscriptions to tokenize the tx
        })
        if not kwargs.get("amount"):
            kwargs["amount"] = order_sudo.amount_total

        compare_amounts = order_sudo.currency_id.compare_amounts
        if compare_amounts(kwargs["amount"], order_sudo.amount_total):
            raise ValidationError(self.env._("The cart has been updated. Please refresh the page."))
        if compare_amounts(order_sudo.amount_paid, order_sudo.amount_total) == 0:
            raise UserError(self.env._("The cart has already been paid. Please refresh the page."))

        if delay_token_charge := kwargs.get("flow") == "token":
            request.update_context(delay_token_charge=True)  # wait until after tx validation
        tx_sudo = self._create_transaction(
            custom_create_values={"sale_order_ids": [Command.set([order_id])]}, **kwargs
        )

        # Store the new transaction into the transaction list and if there's an old one, we remove
        # it until the day the ecommerce supports multiple orders at the same time.
        request.session["__website_sale_last_tx_id"] = tx_sudo.id

        self._validate_transaction_for_order(tx_sudo, order_sudo)
        if delay_token_charge:
            tx_sudo._charge_with_token()

        return tx_sudo._get_processing_values()

    def _get_shop_payment_values(self, order, **_kwargs):
        checkout_page_values = {
            "sale_order": order,
            "website_sale_order": order,
            "cart_has_blocking_alerts": order._has_blocking_alerts(),
            "partner": order.partner_invoice_id,
            "order": order,
            "only_services": order.only_services,
            **self.env.website._get_checkout_step_values("/shop/payment"),
            "payment_tracking_info": (
                order._get_order_tracking_info() if self.env.website.google_analytics_key else {}
            ),
        }
        payment_form_values = {
            **sale_portal.CustomerPortal._get_payment_values(
                self, order, website_id=self.env.website.id
            ),
            "display_submit_button": False,  # The submit button is re-added outside the form.
            "transaction_route": f"/shop/payment/transaction/{order.id}",
            "landing_route": "/shop/payment/validate",
            "sale_order_id": order.id,  # Allow Stripe to check if tokenization is required.
        }
        if checkout_page_values["cart_has_blocking_alerts"]:
            payment_form_values.pop("payment_methods_sudo", "")
            payment_form_values.pop("tokens_sudo", "")
        return checkout_page_values | payment_form_values

    @route(
        "/shop/payment",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        list_as_website_content=_lt("Shop Payment"),
    )
    def shop_payment(self, **post):
        """Payment step. This page proposes several payment means based on available
        payment.provider. State at this point:
         - a draft sales order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.provider website but closed the tab without
           paying / canceling.
        """
        order_sudo = request.cart
        if redirect := self.env["website.checkout.step"].validate_checkout_progress(
            "/shop/payment", order_sudo
        ):
            return request.redirect(redirect)

        # Ensure the prices are up to date and final
        order_sudo._update_cart_taxes_and_prices()
        return request.render(
            "website_sale.payment", self._get_shop_payment_values(order_sudo, **post)
        )

    @route("/shop/payment/validate", type="http", auth="public", website=True, sitemap=False)
    def shop_payment_validate(self, sale_order_id=None, **_post):
        """Server calls this method when receiving an update for a transaction. State at this point:
        - UDPATE ME.
        """
        if sale_order_id is None:
            order_sudo = request.cart
            if not order_sudo and "sale_last_order_id" in request.session:
                # Retrieve the last known order from the session if the session key `sale_order_id`
                # was prematurely cleared. This is done to prevent the user from updating their cart
                # after payment in case they don't return from payment through this route.
                last_order_id = request.session["sale_last_order_id"]
                order_sudo = self.env["sale.order"].sudo().browse(last_order_id).exists()
        else:
            order_sudo = self.env["sale.order"].sudo().browse(sale_order_id)
            assert order_sudo.id == request.session.get("sale_last_order_id")

        if not order_sudo:
            return request.redirect(SHOP_PATH)

        tx_sudo = order_sudo.get_portal_last_transaction()
        if order_sudo.amount_total and not tx_sudo:
            return request.redirect(SHOP_PATH)

        if not order_sudo.amount_total and not tx_sudo and order_sudo.state == "draft":
            # Customer didn't go through /shop/payment/transaction since there is nothing to pay,
            # confirm the order if it is valid.
            if redirect := self.env["website.checkout.step"].validate_checkout_progress(
                "/shop/payment/transaction", order_sudo
            ):
                return request.redirect(redirect)

            order_sudo._validate_order()

        # clean context and session, then redirect to the confirmation page
        self.env.website.sale_reset()
        if tx_sudo and tx_sudo.state == "draft":
            return request.redirect(SHOP_PATH)

        return request.redirect("/shop/confirmation")
