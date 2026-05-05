# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools import urls

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_sslcommerz import const

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_specific_rendering_values(self, processing_values):
        """Override of `payment` to return SSLCOMMERZ-specific rendering values.

        Note: `self.ensure_one()` from :meth:`_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction.
        :return: The provider-specific processing values.
        :rtype: dict
        """
        if self.provider_code != "sslcommerz":
            return super()._get_specific_rendering_values(processing_values)

        payload = self._sslcommerz_prepare_session_payload()
        try:
            session_data = self._send_api_request("POST", "/gwprocess/v4/api.php", data=payload)
        except ValidationError as error:
            self._set_error(str(error))
            return {}

        if self.payment_method_code in const.DIRECT_OPEN_PAYMENT_METHOD_CODES:
            matching_gateway = next(
                (
                    gw
                    for gw in session_data.get("desc", [])
                    if gw.get("gw") == self.payment_method_code
                ),
                None,
            )
            if not matching_gateway:
                self._set_error(self.env._("This payment method is currently unavailable."))
                return {}
            api_url = matching_gateway["redirectGatewayURL"]
        else:
            api_url = session_data["GatewayPageURL"]
        return {
            "api_url": api_url,
            "http_method": "get",
            "url_params": payment_utils.extract_url_params(api_url),
        }

    def _sslcommerz_prepare_session_payload(self):
        """Create the payload for the hosted checkout session request.

        :return: The request payload
        :rtype: dict
        """
        self.ensure_one()
        base_url = self.provider_id.get_base_url()
        return_url = urls.urljoin(base_url, const.PAYMENT_RETURN_ROUTE)
        pm_code = self.payment_method_code
        return {
            "store_id": self.provider_id.sslcommerz_store_id,
            "store_passwd": self.provider_id.sslcommerz_store_password,
            "total_amount": self.amount,
            "currency": self.currency_id.name,
            "tran_id": self.reference,
            "success_url": return_url,
            "fail_url": return_url,
            "cancel_url": return_url,
            "ipn_url": urls.urljoin(base_url, const.IPN_ROUTE),
            "cus_name": self.partner_name or "",
            "cus_email": self.partner_email or "",
            "product_name": "Online Payment",
            "product_category": "general",
            "product_profile": "non-physical-goods",
            "multi_card_name": const.PAYMENT_METHODS_MAPPING.get(pm_code, pm_code),
        }

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != "sslcommerz":
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get("tran_id")

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != "sslcommerz":
            return super()._extract_amount_data(payment_data)

        return {
            "amount": float(payment_data.get("currency_amount")),
            "currency_code": payment_data.get("currency_type"),
        }

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != "sslcommerz":
            return super()._apply_updates(payment_data)

        self.provider_reference = payment_data.get("bank_tran_id")

        card_brand = (payment_data.get("card_brand") or "").lower()
        payment_method = self.provider_id._get_pm_from_code(
            card_brand, mapping=const.PAYMENT_METHODS_RESPONSE_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        status = payment_data.get("status")
        if status in const.PAYMENT_STATUS_MAPPING["done"]:
            self._set_done()
        elif status in const.PAYMENT_STATUS_MAPPING["cancel"]:
            self._set_canceled()
        elif status in const.PAYMENT_STATUS_MAPPING["error"]:
            self._set_error(
                self.env._(
                    "%(code)s: %(explanation)s.", code=status, explanation=payment_data.get("error")
                )
            )
        else:
            _logger.warning(
                "Received data with invalid payment status (%s) for transaction %s.",
                status,
                self.reference,
            )
            self._set_error(self.env._("Unknown payment status: %s", status))
