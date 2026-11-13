# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.loyalty.const import LOYALTY_PAYMENT_CODES
from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    loyalty_card_id = fields.Many2one(
        string="Gift Card / eWallet",
        comodel_name="loyalty.card",
        readonly=True,
        index="btree_not_null",
        copy=False,
    )

    # === CONSTRAINT METHODS === #

    @api.constrains("loyalty_card_id", "provider_id")
    def _check_loyalty_card(self):
        for tx in self.filtered(lambda t: t.provider_code in LOYALTY_PAYMENT_CODES):
            if not tx.loyalty_card_id:
                raise ValidationError(
                    self.env._("A card is required to pay with %s.", tx.provider_id.name)
                )
            if tx.loyalty_card_id.program_type != tx.provider_code:
                raise ValidationError(
                    self.env._(
                        "The card %(code)s cannot be used to pay with %(provider)s.",
                        code=tx.loyalty_card_id.code,
                        provider=tx.provider_id.name,
                    )
                )
            card_partner = tx.loyalty_card_id.partner_id.commercial_partner_id
            if (
                tx.provider_code == "ewallet"
                and card_partner != tx.partner_id.commercial_partner_id
            ):
                raise ValidationError(self.env._("You cannot pay with this eWallet."))

    # === BUSINESS METHODS - PAYMENT FLOW === #

    def _get_specific_processing_values(self, processing_values):
        """Override of `payment` to immediately process the loyalty transactions.

        The balance of the card is consumed internally, without any external request. The
        transaction is therefore confirmed and post-processed (which creates and posts the payment
        consuming the balance of the card) in the same request as its creation.
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code in LOYALTY_PAYMENT_CODES and self.state == "draft":
            self._process_loyalty_payment()
        return res

    def _process_loyalty_payment(self):
        """Confirm the loyalty transaction and create the payment consuming the card's balance.

        Note: `self.ensure_one()`

        :raise ValidationError: If the card cannot pay the amount of the transaction.
        """
        self.ensure_one()
        card = self.loyalty_card_id.sudo()
        card.lock_for_update()
        card.invalidate_recordset(["points"])
        if not card._is_usable_for_payment():
            raise ValidationError(self.env._("The card %s can no longer be used.", card.code))
        balance = card._get_payment_balance(self.currency_id, self.company_id)
        if self.currency_id.compare_amounts(self.amount, balance) > 0:
            raise ValidationError(
                self.env._(
                    "The balance of the card %(code)s is insufficient to pay %(amount)s.",
                    code=card.code,
                    amount=self.currency_id.format(self.amount),
                )
            )
        self._set_done()
        _logger.info("Confirmed loyalty transaction %s.", self.reference)
        # Post-process right away, without catching errors, to never confirm a payment that did not
        # consume the balance of the card.
        self._post_process_with_lock()

    def _post_process(self):
        """Override of `account_payment` to reconcile the invoices with the loyalty payments.

        When an order is paid with several transactions (e.g., partly with a gift card and partly
        with a card), the invoice may only be created when the last transaction is confirmed. The
        payments of the previous loyalty transactions linked to the invoice are reconciled with it.
        """
        super()._post_process()
        for tx in self.filtered(lambda t: t.state == "done"):
            for invoice in tx.invoice_ids.filtered(lambda inv: inv.state == "posted"):
                loyalty_payments = invoice.transaction_ids.filtered(
                    lambda t: t.loyalty_card_id and t.state == "done"
                ).payment_id.filtered(lambda p: p.state != "canceled" and not p.is_reconciled)
                if not loyalty_payments:
                    continue
                receivable_lines = (loyalty_payments.move_id.line_ids | invoice.line_ids).filtered(
                    lambda line: (
                        line.account_id.account_type == "asset_receivable"
                        and line.account_id.reconcile
                        and not line.reconciled
                        and line.parent_state == "posted"
                    )
                )
                for lines in receivable_lines.grouped("account_id").values():
                    lines.reconcile()

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to skip the amount validation for loyalty transactions."""
        if self.provider_code not in LOYALTY_PAYMENT_CODES:
            return super()._extract_amount_data(payment_data)
        return None

    def _create_payment(self, **extra_create_values):
        """Override of `account_payment` to link the payment to the card it consumes."""
        if self.loyalty_card_id:
            extra_create_values.setdefault("loyalty_card_id", self.loyalty_card_id.id)
        return super()._create_payment(**extra_create_values)

    def _get_sent_message(self):
        """Override of `payment` to mention the card used to pay."""
        message = super()._get_sent_message()
        if self.provider_code in LOYALTY_PAYMENT_CODES and self.loyalty_card_id:
            message = self.env._(
                "The customer has selected %(provider)s %(code)s to pay %(amount)s.",
                provider=self.provider_id.name,
                code=self.loyalty_card_id.code,
                amount=self.currency_id.format(self.amount),
            )
        return message
