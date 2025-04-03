# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json

from odoo import _, api, fields, models
from odoo.tools.urls import urljoin

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import COUNTRY_NUMERIC_CODES
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_redsys import const
from odoo.addons.payment_redsys.controllers.main import RedsysController


_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model_create_multi
    def create(self, vals_list):
        """Override of `payment` to set the Redsys-specific `provider_reference`."""
        transactions = super().create(vals_list)
        for tx in transactions.filtered(lambda t: t.provider_code == 'redsys'):
            tx.provider_reference = tx.reference
        return transactions

    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """Override of `payment` to ensure that Redsys' requirements for references are satisfied.

        Redsys' requirements for transaction are as follows:
        - References can only be made of alphanumeric characters.
        - References must be minimum 9 characters and at most 12 characters long.

        :param str provider_code: The code of the provider handling the transaction.
        :param str prefix: The custom prefix used to compute the full reference.
        :param str separator: The custom separator used to separate the prefix from the suffix.
        :return: The unique reference for the transaction.
        :rtype: str
        """
        if provider_code != 'redsys':
            return super()._compute_reference(
                provider_code, prefix=prefix, separator=separator, **kwargs
            )

        # Generate the prefix as a part of the current datetime (up to the month). This leaves just
        # enough room for the separator and the suffix in case of collisions.
        prefix = fields.Datetime.now().strftime('%m%d%H%M%S')

        return super()._compute_reference(provider_code, prefix=prefix, separator='S', **kwargs)

    def _get_specific_rendering_values(self, processing_values):
        """Override of `payment` to return Redsys-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`.

        :param dict processing_values: The generic processing values of the transaction.
        :return: The dict of provider-specific rendering values.
        :rtype: dict
        """
        if self.provider_code != 'redsys':
            return super()._get_specific_rendering_values(processing_values)

        encoded_merchant_parameters = self._redsys_prepare_merchant_parameters()
        signature = self.provider_id._redsys_calculate_signature(
            encoded_merchant_parameters, self.reference, self.provider_id.redsys_secret_key
        )
        return {
            'api_url': self.provider_id._redsys_get_api_url(),
            'merchant_parameters': encoded_merchant_parameters,
            'signature': signature,
            'signature_version': 'HMAC_SHA256_V1',
        }

    def _redsys_prepare_merchant_parameters(self):
        """Create the merchant parameters payload based on the transaction values and return it in
        Base64-encoded format.

        :return: The encoded merchant parameters.
        :rtype: str
        """
        converted_amount = payment_utils.to_minor_currency_units(self.amount, self.currency_id)
        base_url = self.provider_id.get_base_url()
        return_url = urljoin(base_url, RedsysController._return_url)
        webhook_url = urljoin(base_url, RedsysController._webhook_url)
        merchant_parameters = {
            'DS_MERCHANT_AMOUNT': str(converted_amount),
            'DS_MERCHANT_CURRENCY': self.currency_id.iso_numeric,
            'DS_MERCHANT_MERCHANTCODE': self.provider_id.redsys_merchant_code,
            'DS_MERCHANT_TERMINAL': self.provider_id.redsys_merchant_terminal,
            'DS_MERCHANT_ORDER': self.reference,
            'DS_MERCHANT_MERCHANTURL': webhook_url,
            'DS_MERCHANT_TRANSACTIONTYPE': '0',  # Authorization
            'DS_MERCHANT_URLOK': return_url,
            'DS_MERCHANT_URLKO': return_url,
            'DS_MERCHANT_PAYMETHODS': const.PAYMENT_METHODS_MAPPING.get(
                self.payment_method_id.code, 'C'
            ),
            'DS_MERCHANT_EMV3DS': {
                'billAddrCity': self.partner_city,
                'billAddrCountry': COUNTRY_NUMERIC_CODES.get(self.partner_country_id.code, ''),
                'billAddrLine1': self.partner_address,
                'billAddrPostCode': self.partner_zip,
                'billAddrState': self.partner_state_id.code,
                'cardholderName': self.partner_name,
                'email': self.partner_email,
            }
        }

        # Encode the parameters in Base64.
        encoded_merchant_parameters = base64.b64encode(
            json.dumps(merchant_parameters).encode()
        ).decode()

        return encoded_merchant_parameters

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != 'redsys':
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get('Ds_Order')

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != 'redsys':
            return super()._extract_amount_data(payment_data)

        amount = payment_utils.to_major_currency_units(
            float(payment_data.get('Ds_Amount', 0)), self.currency_id
        )
        currency = self.env['res.currency'].search([
            ('iso_numeric', '=', payment_data.get('Ds_Currency'))
        ], limit=1).name
        return {
            'amount': amount,
            'currency_code': currency,
        }

    def _apply_updates(self, payment_data):
        """Override of `payment' to update the transaction based on the payment data."""
        if self.provider_code != 'redsys':
            return super()._apply_updates(payment_data)

        # Update the payment method.
        card_brand = payment_data.get('Ds_Card_Brand')
        payment_method = self.env['payment.method']._get_from_code(
            card_brand, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        status_code = payment_data['Ds_Response']
        if status_code in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif status_code in const.PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        elif status_code in const.PAYMENT_STATUS_MAPPING['error']:
            self._set_error(_(
                "An error occurred during the processing of your payment (%s). Please try again.",
                payment_data.get('Ds_ErrorCode'),
            ))
        else:
            _logger.warning("Received invalid payment status (%s).", status_code)
            self._set_error(_("Unknown status code: %s", status_code))
