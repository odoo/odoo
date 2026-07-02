# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlencode

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools.urls import urljoin

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_qfpay import const

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator="-", **kwargs):
        """Override of `payment` to ensure that QFPay's requirements for references are satisfied.

        QFPay's requirements for transaction are as follows:
        - References must be unique at provider level for a given merchant account.
          This is satisfied by singularizing the prefix with the current datetime. If two
          transactions are created simultaneously, `_compute_reference` ensures the uniqueness of
          references by suffixing a sequence number.
        - References must be at most 128 characters long.

        :param str provider_code: The code of the provider handling the transaction.
        :param str prefix: The custom prefix used to compute the full reference.
        :return: The unique reference for the transaction.
        :rtype: str
        """
        if provider_code != "qfpay":
            return super()._compute_reference(
                provider_code, prefix=prefix, separator=separator, **kwargs
            )

        if not prefix:
            # If no prefix is provided, it could mean that a module has passed a kwarg intended
            # for the `_compute_reference_prefix` method, as it is only called if the prefix is
            # empty. We call it manually here because singularizing the prefix would generate a
            # default value if it was empty, hence preventing the method from ever being called
            # and the transaction from receiving a reference named after the related document.
            prefix = self.sudo()._compute_reference_prefix(separator, **kwargs) or None
        prefix = payment_utils.singularize_reference_prefix(prefix=prefix, max_length=128)

        return super()._compute_reference(provider_code, prefix=prefix, **kwargs)

    def _get_specific_processing_values(self, processing_values):
        """Override `payment` to create and return QFPay payment-intent data."""
        if self.provider_code != "qfpay":
            return super()._get_specific_processing_values(processing_values)

        txamt = str(payment_utils.to_minor_currency_units(self.amount, self.currency_id))
        base_return_url = urljoin(self.provider_id.get_base_url(), const.PAYMENT_RETURN_ROUTE)
        return_url = f"{base_return_url}?{urlencode({'out_trade_no': self.reference})}"

        return {
            "payment_intent": self._qfpay_create_payment_intent(txamt, return_url),
            "out_trade_no": self.reference,
            "txamt": txamt,
            "txcurrcd": self.currency_id.name,
            "return_url": return_url,
        }

    def _qfpay_create_payment_intent(self, txamt, return_url):
        """Create a QFPay payment intent and validate the response status."""
        payload = {
            "txamt": txamt,
            "txcurrcd": self.currency_id.name,
            "pay_type": const.PAYMENT_METHODS_MAPPING.get(self.payment_method_id.code),
            "out_trade_no": self.reference,
            "return_url": return_url,
            "failed_url": return_url,
            "notify_url": urljoin(self.provider_id.get_base_url(), const.WEBHOOK_ROUTE),
        }
        result = self._send_api_request(
            "POST", "/payment_element/v1/create_payment_intent", data=payload
        )

        if result.get("respcd") != "0000":
            raise ValidationError(
                self.env._(
                    "QFPay: Failed to create payment intent: %s",
                    result.get("respmsg") or result.get("resperr") or "Unknown error",
                )
            )
        return result["payment_intent"]

    def _qfpay_query_transaction_data(self):
        """Query QFPay for the latest status of the current transaction."""
        payload = {"out_trade_no": self.reference}
        result = self._send_api_request("POST", "/trade/v1/query", data=payload)
        if result.get("respcd") != "0000":
            return None

        records = result.get("data") or []
        payment_data = records[0] if records else None
        if not payment_data:
            _logger.info("QFPay: No transaction data returned for %s", self.reference)
        return payment_data

    @api.model
    def _extract_reference(self, provider_code, notification_data):
        """Override `payment` to extract the reference from QFPay data."""
        if provider_code != "qfpay":
            return super()._extract_reference(provider_code, notification_data)

        return notification_data.get("out_trade_no")

    def _extract_amount_data(self, notification_data):
        """Override `payment` to extract amount/currency from QFPay data."""
        if self.provider_code != "qfpay":
            return super()._extract_amount_data(notification_data)

        return {
            "amount": payment_utils.to_major_currency_units(
                float(notification_data.get("txamt") or 0), self.currency_id
            ),
            "currency_code": notification_data.get("txcurrcd"),
        }

    def _apply_updates(self, payment_data):
        """Override `payment` to update the transaction from QFPay data."""
        if self.provider_code != "qfpay":
            return super()._apply_updates(payment_data)

        # Update the provider's reference.
        self.provider_reference = payment_data.get("syssn")

        # Update the payment method.
        payment_method_code = payment_data.get("pay_type")
        payment_method = self.provider_id._get_pm_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        response_code = payment_data.get("respcd")
        if response_code in const.PAYMENT_STATUS_MAPPING["done"]:
            self._set_done()
        elif response_code in const.PAYMENT_STATUS_MAPPING["pending"]:
            self._set_pending()
        elif response_code in const.PAYMENT_STATUS_MAPPING["cancel"]:
            self._set_canceled()
        else:
            response_message = (
                payment_data.get("resperr")
                or payment_data.get("respmsg")
                or payment_data.get("errmsg")
            )
            self._set_error(
                self.env._(
                    "QFPay: An error occurred "
                    "(response code %(response_code)s; response message %(response_message)s).",
                    response_code=response_code,
                    response_message=response_message,
                )
            )
