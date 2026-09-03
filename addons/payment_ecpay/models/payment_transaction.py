# Part of Odoo. See LICENSE file for full copyright and licensing details.

from zoneinfo import ZoneInfo

from odoo import api, models
from odoo.tools.urls import urljoin

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_ecpay import const


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator="-", **kwargs):
        """Override of `payment` to ensure that ECPay requirements for references are satisfied.

        ECPay requirements for references are as follows:
        - References must be unique at provider level for a given merchant account.
          This is satisfied by singularizing the prefix with the current datetime. If two
          transactions are created simultaneously, `_compute_reference` ensures the uniqueness of
          references by suffixing a sequence number.
        - References must be at most 20 characters long.
        - References must consist of a combination of letters and numbers in Chinese and English.
        - Special characters (e.g., #, @, &) are not permitted.

        :param str provider_code: The code of the provider handling the transaction.
        :param str prefix: The custom prefix used to compute the full reference.
        :param str separator: The custom separator used to separate the prefix from the suffix.
        :return: The unique reference for the transaction.
        :rtype: str
        """
        if provider_code != "ecpay":
            return super()._compute_reference(
                provider_code, prefix=prefix, separator=separator, **kwargs
            )

        prefix = payment_utils.singularize_reference_prefix(separator="", max_length=20)
        return super()._compute_reference(provider_code, prefix=prefix, separator="", **kwargs)

    def _get_specific_rendering_values(self, processing_values):
        """Override of `payment` to return ECPay-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`.

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        if self.provider_code != "ecpay":
            return super()._get_specific_rendering_values(processing_values)

        base_url = self.provider_id.get_base_url()
        all_payment_methods = {
            item for sublist in const.PAYMENT_METHODS_MAPPING.values() for item in sublist
        }
        ignored_payment_methods = "#".join(
            all_payment_methods.difference(const.PAYMENT_METHODS_MAPPING[self.payment_method_code])
        )

        rendering_values = {
            "MerchantID": self.provider_id.ecpay_merchant_id,
            "MerchantTradeNo": self.reference,
            "MerchantTradeDate": (
                self.create_date
                .replace(tzinfo=ZoneInfo("UTC"))
                .astimezone(ZoneInfo("Asia/Taipei"))
                .strftime("%Y/%m/%d %H:%M:%S")
            ),
            "PaymentType": "aio",
            "TotalAmount": int(self.amount),
            "TradeDesc": "ECPay from Odoo",
            "ItemName": self.reference,
            "ReturnURL": urljoin(base_url, const.WEBHOOK_ROUTE),
            "ChoosePayment": "ALL",
            "EncryptType": "1",
            "ClientBackURL": urljoin(base_url, const.PAYMENT_RETURN_ROUTE),
            "OrderResultURL": urljoin(base_url, const.PAYMENT_RETURN_ROUTE),
            "IgnorePayment": ignored_payment_methods,
        }
        # Find the language code based on the user lang; ECPay defaults to zh_TW if omitted
        language_code = payment_utils.get_language_code(
            self.env.context.get("lang", "en_US"), const.LANGUAGE_CODES_MAPPING, fallback=None
        )
        if language_code:
            rendering_values["Language"] = language_code
        rendering_values.update({
            "CheckMacValue": self.provider_id._ecpay_calculate_signature(rendering_values),
            "api_url": self.provider_id._ecpay_get_api_url(),
        })
        return rendering_values

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != "ecpay":
            return super()._extract_reference(provider_code, payment_data)

        return payment_data.get("MerchantTradeNo")

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != "ecpay":
            return super()._extract_amount_data(payment_data)

        amount = float(payment_data.get("TradeAmt"))
        return {"amount": amount, "currency_code": self.currency_id.name}

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != "ecpay":
            return super()._apply_updates(payment_data)

        # Update the provider's reference.
        self.provider_reference = payment_data.get("TradeNo")

        # Update the payment method.
        payment_method_code = payment_data.get("PaymentType")
        payment_method = self.env["payment.method"]._get_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_RESPONSE_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        return_code = payment_data.get("RtnCode")
        if not return_code:
            self._set_error(self.env._("Received data with missing return code."))
        elif return_code in const.SUCCESS_CODE_MAPPING["done"]:
            self._set_done()
        else:
            return_message = payment_data.get("RtnMsg")
            self._set_error(
                self.env._(
                    "An error occurred (return code %(return_code)s; return message"
                    " %(return_message)s).",
                    return_code=return_code,
                    return_message=return_message,
                )
            )
