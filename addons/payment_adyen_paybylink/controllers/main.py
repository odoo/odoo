# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import binascii
import hashlib
import hmac
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo.exceptions import ValidationError
from odoo.http import request, route

from odoo.addons.payment_adyen.controllers.main import AdyenController

_logger = logging.getLogger(__name__)


class AdyenPayByLinkController(AdyenController):

    @route()
    def adyen_notification(self, **post):
        """ Process the data sent by Adyen to the webhook based on the event code.

        See https://docs.adyen.com/development-resources/webhooks/understand-notifications for the
        exhaustive list of event codes.

        :return: The '[accepted]' string to acknowledge the notification
        :rtype: str
        """
        _logger.info(
            "notification received from Adyen with data:\n%s", pprint.pformat(post)
        )
        try:
            # Check the integrity of the notification
            tx_sudo = request.env['payment.transaction'].sudo()._adyen_form_get_tx_from_data(post)
            self._verify_notification_signature(post, tx_sudo)

            # Check whether the event of the notification succeeded and reshape the notification
            # data for parsing
            event_code = post['eventCode']
            if event_code == 'AUTHORISATION' and post['success'] == 'true':
                post['authResult'] = 'AUTHORISED'

                # Handle the notification data
                request.env['payment.transaction'].sudo().form_feedback(post, 'adyen')
        except ValidationError:  # Acknowledge the notification to avoid getting spammed
            _logger.exception("unable to handle the notification data; skipping to acknowledge")

        return '[accepted]'  # Acknowledge the notification

    @staticmethod
    def _verify_notification_signature(notification_data, tx_sudo):
        """ Check that the received signature matches the expected one.

        :param dict notification_data: The notification payload containing the received signature
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                                  `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the signatures don't match
        """
        # Retrieve the received signature from the payload
        received_signature = notification_data.get('additionalData.hmacSignature')
        if not received_signature:
            _logger.warning("received notification with missing signature")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the payload
        hmac_key = tx_sudo.acquirer_id.adyen_hmac_key
        expected_signature = AdyenPayByLinkController._compute_signature(
            notification_data, hmac_key
        )
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("received notification with invalid signature")
            raise Forbidden()

    @staticmethod
    def _compute_signature(payload, hmac_key):
        """ Compute the signature from the payload.

        See https://docs.adyen.com/development-resources/webhooks/verify-hmac-signatures

        :param dict payload: The notification payload
        :param str hmac_key: The HMAC key of the acquirer handling the transaction
        :return: The computed signature
        :rtype: str
        """
        def _flatten_dict(_value, _path_base='', _separator='.'):
            """ Recursively generate a flat representation of a dict.

            :param Object _value: The value to flatten. A dict or an already flat value
            :param str _path_base: They base path for keys of _value, including preceding separators
            :param str _separator: The string to use as a separator in the key path
            """
            if isinstance(_value, dict):  # The inner value is a dict, flatten it
                _path_base = _path_base if not _path_base else _path_base + _separator
                for _key in _value:
                    yield from _flatten_dict(_value[_key], _path_base + str(_key))
            else:  # The inner value cannot be flattened, yield it
                yield _path_base, _value

        def _to_escaped_string(_value):
            """ Escape payload values that are using illegal symbols and cast them to string.

            String values containing `\\` or `:` are prefixed with `\\`.
            Empty values (`None`) are replaced by an empty string.

            :param Object _value: The value to escape
            :return: The escaped value
            :rtype: string
            """
            if isinstance(_value, str):
                return _value.replace('\\', '\\\\').replace(':', '\\:')
            elif _value is None:
                return ''
            else:
                return str(_value)

        signature_keys = [
            'pspReference', 'originalReference', 'merchantAccountCode', 'merchantReference',
            'value', 'currency', 'eventCode', 'success'
        ]
        # Build the list of signature values as per the list of required signature keys
        signature_values = [payload.get(key) for key in signature_keys]
        # Escape values using forbidden symbols
        escaped_values = [_to_escaped_string(value) for value in signature_values]
        # Concatenate values together with ':' as delimiter
        signing_string = ':'.join(escaped_values)
        # Convert the HMAC key to the binary representation
        binary_hmac_key = binascii.a2b_hex(hmac_key.encode('ascii'))
        # Calculate the HMAC with the binary representation of the signing string with SHA-256
        binary_hmac = hmac.new(binary_hmac_key, signing_string.encode('utf-8'), hashlib.sha256)
        # Calculate the signature by encoding the result with Base64
        return base64.b64encode(binary_hmac.digest()).decode()
