# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2.errors import LockNotAvailable

from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.fields import Command
from odoo.http import request, route
from odoo.tools import SQL

from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.sale.controllers import portal as sale_portal

# TODO ANVFE part of payment routes ? /shop/payment ? express_checkout ?


class PaymentPortal(payment_portal.PaymentPortal):
    def _validate_transaction_for_order(self, _transaction, _sale_order):
        """
        Perform final checks against the transaction & sale_order.
        Override me to apply payment unrelated checks & processing.
        """
        return

    def _check_shop_payment_option(self, order_sudo, amount, **kwargs):
        """Check that the payment option of the customer is available for the order.

        Express checkout pays with the "unknown" payment method of the provider, which is not in the
        payment options. For express checkout, only the provider is checked, against the providers
        that allow express checkout.

        :param sale.order order_sudo: The sales order to pay.
        :param float amount: The amount of the transaction.
        :param dict kwargs: The transaction route values.
        :return: None
        :raise ValidationError: If the payment option is not available.
        """
        payment_options_context = sale_portal.CustomerPortal._get_order_payment_options_context(
            self, order_sudo, amount
        )
        payment_method_sudo = (
            self.env["payment.method"].sudo().browse(kwargs.get("payment_method_id")).exists()
        )
        if kwargs.get("flow") == "direct" and payment_method_sudo.code == "unknown":  # Express
            providers_sudo = self._get_available_payment_options(
                **payment_options_context, is_express_checkout=True
            )["providers_sudo"]
            if kwargs.get("provider_id") not in providers_sudo.ids:
                raise ValidationError(self.env._("This payment option is not available."))
        else:
            self._check_payment_option(payment_options_context, **kwargs)

    @route("/shop/payment/transaction/<int:order_id>", type="jsonrpc", auth="public", website=True)
    def shop_payment_transaction(self, order_id, access_token, amount=None, **kwargs):
        """Create a draft transaction and return its processing values.

        :param int order_id: The sales order to pay, as a `sale.order` id
        :param str access_token: The access token used to authenticate the request
        :param str amount: The amount to pay, which can be chosen by the user
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

        currency = order_sudo.currency_id
        remaining_amount = currency.round(max(0, order_sudo.amount_total - order_sudo.amount_paid))

        self._validate_transaction_kwargs(kwargs)
        kwargs.update({
            "partner_id": order_sudo.partner_invoice_id.id,
            "currency_id": currency.id,
            "sale_order_id": order_id,  # Include the SO to allow Subscriptions to tokenize the tx
        })
        amount = amount or remaining_amount  # Express checkout doesn't forward the amount

        if currency.compare_amounts(amount, remaining_amount) > 0:
            raise ValidationError(self.env._("The cart has been updated. Please refresh the page."))

        if order_sudo._is_paid():
            raise UserError(self.env._("The cart has already been paid. Please refresh the page."))

        self._check_shop_payment_option(order_sudo, amount, **kwargs)

        if delay_token_charge := kwargs.get("flow") == "token":
            request.update_context(delay_token_charge=True)  # wait until after tx validation
        tx_sudo = self._create_transaction(
            amount=amount,
            custom_create_values={"sale_order_ids": [Command.set([order_id])]},
            **kwargs,
        )

        # Store the new transaction into the transaction list and if there's an old one, we remove
        # it until the day the ecommerce supports multiple orders at the same time.
        request.session["__website_sale_last_tx_id"] = tx_sudo.id

        self._validate_transaction_for_order(tx_sudo, order_sudo)
        if delay_token_charge:
            tx_sudo._charge_with_token()

        return tx_sudo._get_processing_values()
