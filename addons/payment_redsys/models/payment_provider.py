# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import hmac

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from odoo import fields, models

from odoo.addons.payment_redsys import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('redsys', "Redsys")], ondelete={'redsys': 'set default'}
    )
    redsys_merchant_code = fields.Char(
        string="Redsys Merchant Code",
        required_if_provider='redsys',
        copy=False,
    )
    redsys_merchant_terminal = fields.Char(
        string="Redsys Merchant Terminal",
        required_if_provider='redsys',
        copy=False,
    )
    redsys_secret_key = fields.Char(
        string="Redsys Secret Key",
        required_if_provider='redsys',
        copy=False,
        groups='base.group_system',
    )

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.code != 'redsys':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS === #

    def _redsys_get_api_url(self):
        if self.state == 'enabled':
            return 'https://sis.redsys.es/sis/realizarPago'
        else:  # 'test'
            return 'https://sis-t.redsys.es:25443/sis/realizarPago'

    def _redsys_calculate_signature(self, merchant_parameters, reference, secret_key):
        """Calculate the signature for the provided data.

        See https://pagosonline.redsys.es/desarrolladores-inicio/documentacion-operativa/firmar-una-operacion.

        :param str merchant_parameters: The Base64-encoded merchant parameters.
        :param str reference: The transaction reference.
        :param str secret_key: The secret SHA-256 key given by the provider.
        :return: The calculated signature.
        :rtype: str
        """
        # 1. Decode the SHA-256 key from Base64.
        decoded_key = base64.b64decode(secret_key)
        # 2. Derive the signature key by 3DES-encrypting the transaction (Ds_Merchant_Order).
        encoded_order = reference.encode().ljust(16, b'\x00')
        cipher = Cipher(
            algorithms.TripleDES(decoded_key), modes.CBC(b'\x00' * 8), backend=default_backend()
        )
        derived_key = cipher.encryptor().update(encoded_order) + cipher.encryptor().finalize()
        # 3. Create HMAC-SHA256 using the derived key and merchant parameters.
        hmac_obj = hmac.new(derived_key, merchant_parameters.encode(), hashlib.sha256)
        # 4. Encode the HMAC result in Base64.
        signature = base64.urlsafe_b64encode(hmac_obj.digest()).decode()
        return signature
