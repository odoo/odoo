# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_ecpay import const
from odoo.addons.payment_ecpay.controllers.main import EcpayController


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """ Override of `payment` to ensure that ECPay requirements for references are satisfied.

        ECPay requirements for references are as follows:
        - References must be unique at provider level for a given merchant account.
          This is satisfied by singularizing the prefix with the current datetime. If two
          transactions are created simultaneously, `_compute_reference` ensures the uniqueness of
          references by suffixing a sequence number.
        - References must be at most 35 characters long.

        :param str provider_code: The code of the provider handling the transaction.
        :param str prefix: The custom prefix used to compute the full reference.
        :param str separator: The custom separator used to separate the prefix from the suffix.
        :return: The unique reference for the transaction.
        :rtype: str
        """
        if provider_code != 'ecpay':
            return super()._compute_reference(provider_code, prefix=prefix, **kwargs)

        if not prefix:
            # If no prefix is provided, it could mean that a module has passed a kwarg intended for
            # the `_compute_reference_prefix` method, as it is only called if the prefix is empty.
            # We call it manually here because singularizing the prefix would generate a default
            # value if it was empty, hence preventing the method from ever being called and the
            # transaction from received a reference named after the related document.
            prefix = self.sudo()._compute_reference_prefix(provider_code, separator='', **kwargs) or None
        prefix = payment_utils.singularize_reference_prefix(prefix=prefix, separator='', max_length=20)
        return super()._compute_reference(provider_code, prefix=prefix, **kwargs)

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return ECPay-specific rendering values.

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
        # The lang is taken from the context rather than from the partner because it is not required
        # to be logged in to make a payment, and because the lang is not always set on the partner.
        lang = self._context.get('lang') or 'en_US'
        amount = self.currency_id._convert(self.amount, self.env.ref('base.TWD'), self.company_id, fields.Date.today())
        rendering_values = {
            "MerchantTradeNo": self.reference,
            "MerchantTradeDate": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "TotalAmount": int(amount),
            "TradeDesc": "ECPay from Odoo",
            "ItemName": "#".join(
                ["{} NT${}x{}".format(
                    line.name_short,
                    line.currency_id._convert(line.price_unit, self.env.ref('base.TWD'), self.company_id, fields.Date.today()),
                    line.product_uom_qty,
                ) for line in self.sale_order_ids.mapped('order_line')]
            ),
            "ReturnURL": urls.url_join(base_url, EcpayController._webhook_url),
            "ClientBackURL": urls.url_join(base_url, EcpayController._return_url),
            "PaymentInfoURL": urls.url_join(base_url, EcpayController._webhook_url),
            "ChoosePayment": "ALL",
        }
        if language_code := const.LANGUAGE_CODES_MAPPING.get(lang):
            rendering_values['Language'] = language_code
        rendering_values = self.provider_id._ecpay_calculate_signature(
            rendering_values, incoming=False
        )
        rendering_values.update({
            "api_url": self.provider_id._ecpay_get_api_url(),
        })
        return rendering_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on ECPay data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data are received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != "ecpay" or len(tx) == 1:
            return tx

        reference = notification_data.get("MerchantTradeNo")
        if not reference:
            raise ValidationError(
                "ECPay: " + _("Received data with missing reference %(ref)s.", ref=reference)
            )

        tx = self.search([("reference", "=", reference), ('provider_code', '=', 'ecpay')])
        if not tx:
            raise ValidationError(
                "ECPay: " + _("No transaction found matching reference %s.", reference)
            )

        return tx

    def _process_notification_data(self, notification_data):
        """ Override of `payment' to process the transaction based on ECPay data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If inconsistent data are received.
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'ecpay':
            return

        self.provider_reference = notification_data.get('TradeNo')

        return_code = notification_data.get('RtnCode')
        return_message = notification_data.get('RtnMsg')
        if not return_code:
            raise ValidationError("ECPay: " + _("Received data with missing return code."))

        if return_code in const.SUCCESS_CODE_MAPPING['pending']:
            self._set_pending()
        elif return_code in const.SUCCESS_CODE_MAPPING['done']:
            self._set_done()
        else:
            self._set_error(_(
                "An error occurred during the processing of your payment (return code %s; return "
                "message %s). Please try again.", return_code, return_message
            ))
