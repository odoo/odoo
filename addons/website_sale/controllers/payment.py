from odoo.exceptions import (
    AccessError,
    LockError,
    MissingError,
    UserError,
    ValidationError,
)
from odoo.fields import Command
from odoo.http import request, route

from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):
    def _check_transaction_for_order(self, transaction, sale_order):
        return

    @route(
        "/shop/payment/transaction/<int:order_id>",
        type="jsonrpc",
        auth="public",
        website=True,
    )
    def shop_payment_transaction(self, order_id, access_token, **kwargs):
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token
            )
            order_sudo.lock_for_update(allow_referencing=True)
        except MissingError:
            raise
        except AccessError as e:
            raise ValidationError(request.env._("The access token is invalid.")) from e
        except LockError as e:
            raise UserError(request.env._("Payment is already being processed.")) from e

        if order_sudo.state == "cancel":
            raise ValidationError(request.env._("The order has been cancelled."))

        order_sudo._check_cart_is_ready_to_be_paid()

        self._check_transaction_kwargs(kwargs)
        kwargs.update(
            {
                "partner_id": order_sudo.partner_invoice_id.id,
                "currency_id": order_sudo.currency_id.id,
                "sale_order_id": order_id,
            }
        )
        if not kwargs.get("amount"):
            kwargs["amount"] = order_sudo.amount_total

        compare_amounts = order_sudo.currency_id.compare_amounts
        if compare_amounts(kwargs["amount"], order_sudo.amount_total):
            raise ValidationError(
                request.env._("The cart has been updated. Please refresh the page.")
            )
        if compare_amounts(order_sudo.amount_paid, order_sudo.amount_total) == 0:
            raise UserError(
                request.env._(
                    "The cart has already been paid. Please refresh the page."
                )
            )

        if delay_token_charge := kwargs.get("flow") == "token":
            request.update_context(delay_token_charge=True)
        tx_sudo = self._create_transaction(
            custom_create_values={"sale_order_ids": [Command.set([order_id])]},
            **kwargs,
        )

        request.session["__website_sale_last_tx_id"] = tx_sudo.id

        self._check_transaction_for_order(tx_sudo, order_sudo)
        if delay_token_charge:
            tx_sudo._charge_with_token()

        return tx_sudo._prepare_processing_values()
