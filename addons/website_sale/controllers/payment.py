# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2.errors import LockNotAvailable

from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.fields import Command
from odoo.http import request, route
from odoo.tools import SQL

from odoo.addons.payment.controllers import portal as payment_portal

# TODO ANVFE part of payment routes ? /shop/payment ? express_checkout ?


class PaymentPortal(payment_portal.PaymentPortal):
    def _validate_transaction_for_order(self, _transaction, _sale_order):
        """
        Perform final checks against the transaction & sale_order.
        Override me to apply payment unrelated checks & processing.
        """
        return

    @route("/shop/payment/transaction/<int:order_id>", type="jsonrpc", auth="public", website=True)
    def shop_payment_transaction(self, order_id, access_token, amount=None, **kwargs):
        """Create a draft transaction and return its processing values.

        :param int order_id: The sales order to pay, as a `sale.order` id
        :param str access_token: The access token used to authenticate the request
        :param str amount: The amount to pay, if different from the order's remaining amount due
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
        currency = order_sudo.currency_id
        kwargs.update({
            "partner_id": order_sudo.partner_invoice_id.id,
            "currency_id": currency.id,
            "sale_order_id": order_id,  # Include the SO to allow Subscriptions to tokenize the tx
        })

        if order_sudo._is_paid_or_pending():
            raise UserError(self.env._("The cart has already been paid. Please refresh the page."))

        amount = self._cast_as_float(amount)
        kwargs["amount"] = order_sudo._get_payment_amount(amount)

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
