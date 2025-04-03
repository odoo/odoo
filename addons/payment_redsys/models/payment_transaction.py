# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import hmac
import json
import logging
import time
from werkzeug import urls

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from odoo import _, api, models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import COUNTRY_3166_MAPPING, CURRENCY_4217_MAPPING
from odoo.addons.payment_redsys import const
from odoo.addons.payment_redsys.controllers.main import RedsysController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """ Override of the payment method to compute a unique reference prefix to send to Redsys.

        Redsys requires references to be maximum 12 characters long and alphanumeric only.
        This implementation uses base36 encoding of the current timestamp.
        Prefix format of max 10 characters: "A1B2C3D4E5" and R being the separator.


        :param str provider_code: The code of the provider handling the transaction.
        :return: Call to super with prefix and separator specific to Redsys.
        :rtype: str
        """
        if provider_code != 'redsys':
            return super()._compute_reference(
                provider_code, prefix=prefix, separator=separator, **kwargs
            )

        now = int(time.time() * 1e6)  # Microseconds for higher precision
        base36 = ''
        chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

        while now > 0:
            now, i = divmod(now, 36)
            base36 = chars[i] + base36  # Prepend the character at index 'i' to the result

        prefix = base36[:10]
        return super()._compute_reference(provider_code, prefix=prefix, separator='R', **kwargs)

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return Redsys-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`.

        :param dict processing_values: The generic processing values of the transaction.
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'redsys':
            return res

        merchant_parameters = self._prepare_merchant_parameters()
        signature = self._redsys_calculate_signature(
            merchant_parameters,
            self.reference,
            self.provider_id.redsys_secret_key,
        )
        return {
            'api_url': self.provider_id._redsys_get_api_url(),
            'signature_version': 'HMAC_SHA256_V1',
            'merchant_parameters': merchant_parameters,
            'signature': signature,
        }

    def _prepare_merchant_parameters(self):
        """ Create the merchant parameters for the request to the Redsys API.

        :return: The encoded merchant parameters.
        :rtype: str
        """
        # All parameters are of type string, the amount is expressed in cents
        amount = str(int(self.amount * 100))
        base_url = self.provider_id.get_base_url()
        return_url = urls.url_join(base_url, RedsysController._return_url)

        merchant_parameters = {
            'DS_MERCHANT_AMOUNT': amount,
            'DS_MERCHANT_CURRENCY': CURRENCY_4217_MAPPING[self.currency_id.name],
            'DS_MERCHANT_MERCHANTCODE': self.provider_id.redsys_merchant_code,
            'DS_MERCHANT_MERCHANTURL': urls.url_join(base_url, RedsysController._webhook_url),
            'DS_MERCHANT_ORDER': self.reference,
            'DS_MERCHANT_TERMINAL': self.provider_id.redsys_merchant_terminal,
            'DS_MERCHANT_TRANSACTIONTYPE': '0',  # Authorization
            'DS_MERCHANT_URLKO': return_url,
            'DS_MERCHANT_URLOK': return_url,
            'DS_MERCHANT_PAYMETHODS': const.PAYMENT_METHODS_MAPPING.get(
                self.payment_method_id.code, 'C'
            ),
            'DS_MERCHANT_EMV3DS': {
                'billAddrCity': self.partner_city,
                'billAddrCountry': COUNTRY_3166_MAPPING.get(self.partner_country_id.code, ''),
                'billAddrLine1': self.partner_address,
                'billAddrPostCode': self.partner_zip,
                'billAddrState': self.partner_state_id.code,
                'cardholderName': self.partner_name,
                'email': self.partner_email,
            }
        }

        # Convert parameters to JSON and encode in BASE64
        encoded_merchant_parameters = base64.b64encode(
            json.dumps(merchant_parameters).encode()
        ).decode()

        return encoded_merchant_parameters

    def _redsys_calculate_signature(self, merchant_parameters, order_number, key):
        """Calculate the Redsys signature

        See Ds_Signature:
        https://pagosonline.redsys.es/desarrolladores-inicio/documentacion-tipos-de-integracion/desarrolladores-redireccion/

        :param str merchant_parameters: The encoded merchant parameters (base64)
        :param str order_number: The DS_MERCHANT_ORDER (reference)
        :param str key: The secret SHA-256 key provided by the provider
        :return: The calculated signature
        :rtype: str
        """
        # 1. Decode the SHA-256 key from Base64
        decoded_key = base64.b64decode(key)
        # 2. Derive the signature key by 3DES-encrypting order_number (Ds_Merchant_Order)
        encoded_order = order_number.encode().ljust(16, b'\x00')
        cipher = Cipher(
            algorithms.TripleDES(decoded_key),
            modes.CBC(b'\x00' * 8),
            backend=default_backend()
        )
        derived_key = cipher.encryptor().update(encoded_order) + cipher.encryptor().finalize()
        # 3. Create HMAC-SHA256 using the derived key and merchant parameters
        hmac_obj = hmac.new(derived_key, merchant_parameters.encode(), hashlib.sha256)
        # 4. Encode the HMAC result in Base64
        signature = base64.urlsafe_b64encode(hmac_obj.digest()).decode()

        return signature

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on Redsys data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data are received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'redsys' or len(tx) == 1:
            return tx

        reference = notification_data.get('Ds_Order')
        if not reference:
            raise ValidationError(
                "Redsys: " + _("Received data with missing reference %(ref)s.", ref=reference)
            )
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'redsys')])
        if not tx:
            raise ValidationError(
                "Redsys: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _compare_notification_data(self, notification_data):
        """ Override of `payment` to compare the transaction based on Redsys data.

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If the transaction's amount and currency don't match the
            notification data.
        """
        if self.provider_code != 'redsys':
            return super()._compare_notification_data(notification_data)

        amount = int(notification_data.get('Ds_Amount')) / 100
        currency = payment_utils.get_currency_alphabetic_code_from_numeric_code(
            notification_data.get('Ds_Currency')
        )
        self._validate_amount_and_currency(amount, currency)

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the transaction based on Redsys data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'redsys':
            return

        # Update the payment state.
        status_code = notification_data.get('Ds_Response')
        if status_code in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif status_code in const.PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        elif status_code in const.PAYMENT_STATUS_MAPPING['error']:
            self._set_error(_("Received data with code %s.", notification_data.get('Ds_ErrorCode')))
        else:
            _logger.warning(
                "Received data with invalid payment status (%s) for transaction with reference %s",
                status_code, self.reference
            )
            self._set_error("Redsys: " + _("Unknown status code: %s", status_code))
