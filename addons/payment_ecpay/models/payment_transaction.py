# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, models
from odoo.tools.urls import urljoin

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_ecpay import const
from odoo.addons.payment_ecpay.controllers.main import EcpayController


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    @api.model
    def _compute_reference(self, provider_code, prefix=None, **kwargs):
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
        if provider_code == 'ecpay':
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
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "ecpay":
            return res

        base_url = self.provider_id.get_base_url()
        all_payment_methods = {
            item for sublist in const.PAYMENT_METHODS_MAPPING.values() for item in sublist
        }
        ignore_payment_methods = "#".join(
            all_payment_methods.difference(const.PAYMENT_METHODS_MAPPING[self.payment_method_code])
        )

        if self.sale_order_ids:
            item_details = (
                f"{line.name_short} NT${line.price_unit}X{line.product_uom_qty}"
                for line in self.sale_order_ids.order_line
            )
            item_name = "#".join(item_details)
        elif self.invoice_ids.invoice_line_ids:
            item_details = (
                f"{line.name} NT${line.price_unit}X{line.quantity}"
                for line in self.invoice_ids.invoice_line_ids
            )
            item_name = "#".join(item_details)
        else:
            item_name = f"Payment NT${int(self.amount)}X1"

        rendering_values = {
            "MerchantID": self.provider_id.ecpay_merchant_id,
            "MerchantTradeNo": self.reference,
            "MerchantTradeDate": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "TotalAmount": int(self.amount),
            "TradeDesc": "ECPay from Odoo",
            "ItemName": item_name,
            "ReturnURL": urljoin(base_url, EcpayController._webhook_url),
            "OrderResultURL": urljoin(base_url, EcpayController._return_url),
            "PaymentInfoURL": urljoin(base_url, EcpayController._webhook_url),
            "ChoosePayment": "ALL",
            "IgnorePayment": ignore_payment_methods,
            "Remark": self.invoice_ids.display_name or self.sale_order_ids.display_name or " ",
            "PaymentType": "aio",
            "EncryptType": "1",
        }
        if language_code := const.LANGUAGE_CODES_MAPPING.get(self.env.context.get("lang", "en_US")):
            rendering_values["Language"] = language_code

        rendering_values.update({
            "CheckMacValue": self.provider_id._ecpay_calculate_signature(rendering_values)
        })
        rendering_values.update({"api_url": self.provider_id._ecpay_get_api_url()})
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
        """Override of `payment` to process the transaction based on ECPay data.

        :param dict payment_data: The payment_data data sent by the provider.
        :return: None
        :raise ValidationError: If inconsistent data are received.
        """
        if self.provider_code != "ecpay":
            return super()._apply_updates(payment_data)

        self.provider_reference = payment_data.get("TradeNo")
        return_code = payment_data.get("RtnCode")
        return_message = payment_data.get("RtnMsg")

        if not return_code:
            self._set_error(self.env._("Received data with missing return code."))
        elif return_code in const.SUCCESS_CODE_MAPPING["pending"]:
            self._set_pending()
        elif return_code in const.SUCCESS_CODE_MAPPING["done"]:
            self._set_done()
        else:
            self._set_error(
                self.env._(
                    "An error occurred "
                    "(return code %(return_code)s; return message %(return_message)s).",
                    return_code=return_code,
                    return_message=return_message,
                )
            )
