from odoo import _, models

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_custom.controllers.main import CustomController

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _prepare_redirect_form_values(self, processing_values):
        """Override of payment to return custom-specific rendering values.

        Note: self.check_singleton() from `_prepare_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        if self.provider_code != "custom":
            return super()._prepare_redirect_form_values(processing_values)

        return {
            "api_url": CustomController._process_url,
            "reference": self.reference,
            "access_token": payment_utils.generate_access_token(
                self.reference, self.amount, env=self.env
            ),
        }

    def _get_communication(self):
        """Return the communication the user should use for their transaction.

        This communication might change according to the settings and the accounting localization.

        Note: self.check_singleton()

        :return: The selected communication.
        :rtype: str
        """
        self.check_singleton()
        communication = ""
        if hasattr(self, "invoice_ids") and self.invoice_ids:
            communication = self.invoice_ids[0].payment_reference
        elif hasattr(self, "sale_order_ids") and self.sale_order_ids:
            communication = self.sale_order_ids[0].reference
        return communication or self.reference

    def _get_custom_qr_code(self):
        """Return the QR code image for a pending wire transfer, if enabled and available.

        No-op (returns None) if QR codes are disabled on the provider, no bank account is
        configured on the company, or `account` isn't installed (it provides the bank's
        QR-code builder; `payment_custom` only depends on `payment`).

        :return: The base64-encoded QR code image, or None.
        :rtype: str | None
        """
        self.check_singleton()
        if not self.provider_id.sudo().qr_code:
            return None
        bank = self.company_id.sudo().partner_id.bank_ids[:1]
        if not bank or not hasattr(bank, "prepare_qr_code_base64"):
            return None
        return bank.prepare_qr_code_base64(
            self.amount,
            self._get_communication(),
            None,
            self.currency_id,
            self.partner_id,
        )

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to skip the amount validation for custom flows."""
        if self.provider_code != "custom":
            return super()._extract_amount_data(payment_data)
        return None

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != "custom":
            return super()._apply_updates(payment_data)

        _logger.info(
            "Validated custom payment for transaction %s: set as pending.",
            self.reference,
        )
        self._set_pending()
        return None

    def _log_received_message(self):
        """Override of `payment` to remove custom providers from the recordset.

        :return: None
        """
        other_provider_txs = self.filtered(lambda t: t.provider_code != "custom")
        super(PaymentTransaction, other_provider_txs)._log_received_message()

    def _get_sent_message(self):
        """Override of payment to return a different message.

        :return: The 'transaction sent' message
        :rtype: str
        """
        message = super()._get_sent_message()
        if self.provider_code == "custom":
            message = _(
                "The customer has selected %(provider_name)s to make the payment.",
                provider_name=self.provider_id.name,
            )
        return message
