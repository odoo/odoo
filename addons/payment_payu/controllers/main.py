# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import pprint

from werkzeug.exceptions import Forbidden

from odoo.http import Controller, request, route

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_payu import const as payu_consts
from odoo.addons.payment_payu import utils as payu_utils

_logger = get_payment_logger(__name__)


class PayUController(Controller):

    @route(payu_consts.RETURN_URL, type='http', auth='public', methods=['GET'])
    def payu_return_from_checkout(self, **payload):
        """Handle PayU redirect after checkout completion.

        After the user completes a payment on PayU's hosted page, they are redirected
        back to this endpoint. This route does **not** process the transaction because
        PayU sends the authoritative transaction details to the webhook endpoint.
        It simply acknowledges the redirect and forwards the user to the payment status page.

        :param dict payload: The query parameters received from PayU upon redirection,
                        usually containing `txnid`, `status`, and other fields.
        :return: A redirection response to the payment status page.
        :rtype: werkzeug.wrappers.Response
        """
        _logger.info('PayU return redirect received with payload:\n%s', pprint.pformat(payload))
        # No processing needed — main payload is received via the webhook
        return request.redirect('/payment/status')

    @route(payu_consts.WEBHOOK_URL, type='http', auth='public', methods=['POST'], csrf=False)
    def payu_webhook(self, **payload):
        """Process a PayU webhook notification and update the corresponding payment transaction.

        PayU sends asynchronous notifications (payment success, failure, or refund) to this
        webhook endpoint. The notification is verified, matched to an existing transaction,
        and processed accordingly.

        :param dict payload: The payment notification payload received from PayU.
                            It typically includes fields such as `mihpayid`, `status`,
                            `udf1`, and signature-related parameters.
        :return: An empty JSON response acknowledging receipt of the webhook.
        :rtype: str
        :raise ValidationError: If the signature verification or transaction processing fails.
        """
        if request.httprequest.content_type == 'application/json':
            payload = request.httprequest.get_json(silent=True)

        _logger.info('Notification received from PayU with payload:\n%s', pprint.pformat(payload))

        # Identify the event type and extract the received signature.
        is_refund = 'action' in payload and (payload.get('action') or '').strip() == 'refund'
        received_signature = (
            (payload.get('key') or '').strip() if is_refund else (payload.get('hash') or '').strip()
        )
        # Find the corresponding payment transaction
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference('payu', payload)
        if not tx_sudo:
            _logger.warning('No matching PayU transaction found for payload: %s', payload.get('mihpayid'))
            return request.make_json_response('')

        # Verify payload signature before processing
        try:
            PayUController._verify_signature(payload, received_signature, tx_sudo, is_refund=is_refund)
        except Forbidden:
            _logger.warning('PayU signature verification failed')
            return request.make_json_response('')

        # Process the verified transaction
        try:
            tx_sudo._process('payu', payload)
            _logger.info('PayU transaction processed successfully (Ref: %s)', tx_sudo.reference)
        except Exception:
            _logger.exception('Failed to process PayU transaction')
            return request.make_json_response('')

        # Always return empty string as acknowledgment
        return request.make_json_response('')

    @staticmethod
    def _verify_signature(payment_data, received_signature, tx_sudo, is_refund=False):
        """Check that the received signature matches the expected one.

        :param dict payment_data: The payment data.
        :param str received_signature: The signature to compare with the expected signature.
        :param recordset tx_sudo: The related `payment.transaction` record (in sudo mode),
                                used to access the merchant's `payu_merchant_key` and `payu_merchant_salt`.
        :param bool is_refund: Whether the payment data is from a refund webhook.
        :return: None
        :raise werkzeug.exceptions.Forbidden: If the signatures don't match.
        """
        if not received_signature:
            _logger.warning('Received payment data with missing signature.')
            raise Forbidden()

        if is_refund:
            expected_signature = tx_sudo.provider_id.payu_merchant_key
        else:
            hash_input = {
                **payment_data,
                'salt': tx_sudo.provider_id.payu_merchant_salt,
                'key': tx_sudo.provider_id.payu_merchant_key,
            }
            expected_signature = payu_utils.generate_payu_hash(
                hash_input, payu_consts.PAYU_HASH_SEQUENCE.get('PAYMENT_WEBHOOK'),
            )

        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning('Received payment data with invalid signature.')
            raise Forbidden()
