# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.http import route

from odoo.addons.loyalty.const import LOYALTY_PAYMENT_CODES
from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):
    def _validate_transaction_kwargs(self, kwargs, additional_allowed_keys=()):
        """Override of `payment` to allow passing the card used to pay with a loyalty provider."""
        super()._validate_transaction_kwargs(
            kwargs, additional_allowed_keys=(*additional_allowed_keys, "loyalty_card_id")
        )

    def _create_transaction(
        self, provider_id, *args, loyalty_card_id=None, custom_create_values=None, **kwargs
    ):
        """Override of `payment` to link the transaction to the card used to pay."""
        provider_sudo = self.env["payment.provider"].sudo().browse(provider_id)
        if provider_sudo.code in LOYALTY_PAYMENT_CODES:
            try:
                loyalty_card_id = int(loyalty_card_id)
            except (TypeError, ValueError) as e:
                raise ValidationError(
                    self.env._("Please select the card to use to pay with %s.", provider_sudo.name)
                ) from e
            custom_create_values = {
                **(custom_create_values or {}),
                "loyalty_card_id": loyalty_card_id,
            }
        return super()._create_transaction(
            provider_id, *args, custom_create_values=custom_create_values, **kwargs
        )

    @route("/payment/loyalty/check_card", type="jsonrpc", auth="public")
    def loyalty_check_card(self, provider_id, amount, code=None, currency_id=None, **_kwargs):
        """Check that a gift card can be used to pay and return the amount it can pay.

        :param int provider_id: The loyalty provider, as a `payment.provider` id.
        :param float amount: The amount left to pay.
        :param str code: The code of the gift card.
        :param int currency_id: The currency of the payment, as a `res.currency` id.
        :return: The card's id, code, and the amount it can pay; or an error message.
        :rtype: dict
        """
        try:
            provider_id = int(provider_id)
            currency_id = int(currency_id) if currency_id else None
            amount = float(amount or 0)
        except (TypeError, ValueError):
            return {"error": self.env._("This payment method is not available.")}

        provider_sudo = self.env["payment.provider"].sudo().browse(provider_id).exists()
        if not provider_sudo or provider_sudo.code != "gift_card":
            return {"error": self.env._("This payment method is not available.")}

        code = (code or "").strip()
        card_sudo = code and self.env["loyalty.card"].sudo().search(
            [
                ("code", "=", code),
                ("program_type", "=", provider_sudo.code),
                ("company_id", "in", [False, *provider_sudo.company_id.parent_ids.ids]),
            ],
            limit=1,
        )
        if not card_sudo or not card_sudo._is_usable_for_payment():
            return {"error": self.env._("This gift card code is invalid or expired.")}

        currency = (
            self.env["res.currency"].browse(currency_id).exists()
            if currency_id
            else provider_sudo.company_id.currency_id
        )
        if not currency:
            return {"error": self.env._("This currency is not available.")}
        if amount <= 0:
            return {"error": self.env._("The amount to pay must be positive.")}
        balance = card_sudo._get_payment_balance(currency, provider_sudo.company_id)
        if currency.is_zero(balance):
            return {"error": self.env._("This gift card has already been used.")}
        usable_amount = min(balance, currency.round(amount))
        return {
            "card_id": card_sudo.id,
            "code": card_sudo.code,
            "amount": usable_amount,
            "amount_formatted": currency.format(usable_amount),
            "balance_formatted": currency.format(balance),
        }
