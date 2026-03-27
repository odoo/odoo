# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import pprint
from datetime import datetime

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import file_open, mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_stripe import const
from odoo.addons.payment_stripe import utils as stripe_utils

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class StripeController(http.Controller):
    _return_url = '/payment/stripe/return'
    _webhook_url = '/payment/stripe/webhook'
    _apple_pay_domain_association_url = '/.well-known/apple-developer-merchantid-domain-association'
    WEBHOOK_AGE_TOLERANCE = 10*60  # seconds

    @http.route(_return_url, type='http', methods=['GET'], auth='public')
    def stripe_return(self, **data):
        """Process the payment data sent by Stripe after redirection from payment.

        Customers go through this route regardless of whether the payment was direct or with
        redirection to Stripe or to an external service (e.g., for strong authentication).

        :param dict data: The payment data, including the reference appended to the URL in
                          `_get_specific_processing_values`.
        """
        # Retrieve the transaction based on the reference included in the return url.
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference('stripe', data)
        endpoint = (
            f'payment_intents/{data.get("payment_intent")}'  # Fetch the PaymentIntent.
            if tx_sudo.operation != 'validation'
            else f'setup_intents/{data.get("setup_intent")}'  # Fetch the SetupIntent.
        )
        try:
            response_content = tx_sudo._send_api_request(
                'GET',
                endpoint,
                data={'expand[]': 'payment_method'},  # Expand all required objects.
            )
        except ValidationError:
            _logger.error("Failed to process the return from Stripe.")
        else:
            if tx_sudo.operation != 'validation':
                self._include_payment_intent_in_payment_data(response_content, data)
            else:
                self._include_setup_intent_in_payment_data(response_content, data)
            # Process the payment data crafted with Stripe API's objects.
            tx_sudo._process('stripe', data)

        # Redirect the user to the status page.
        with mute_logger('werkzeug'):  # avoid logging secret URL params
            return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def stripe_webhook(self):
        """Process the payment data sent by Stripe to the webhook.

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        event = request.get_json_data()
        _logger.info("Notification received from Stripe with data:\n%s", pprint.pformat(event))
        try:
            if event['type'] in const.HANDLED_WEBHOOK_EVENTS:
                stripe_object = event['data']['object']  # {Payment,Setup}Intent, Charge, or Refund.

                # Check the integrity of the event.
                data = {
                    'reference': stripe_object.get('description'),
                    'event_type': event['type'],
                    'object_id': stripe_object['id'],
                }
                tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
                    'stripe', data
                )

                if not tx_sudo:
                    return request.make_json_response('')

                self._verify_signature(tx_sudo)

                if event['type'].startswith('payment_intent'):  # Payment operation.
                    if tx_sudo.tokenize:
                        payment_method = tx_sudo._send_api_request(
                            'GET', f'payment_methods/{stripe_object["payment_method"]}'
                        )
                        stripe_object['payment_method'] = payment_method
                    self._include_payment_intent_in_payment_data(stripe_object, data)
                elif event['type'].startswith('setup_intent'):  # Validation operation.
                    # Fetch the missing PaymentMethod object.
                    payment_method = tx_sudo._send_api_request(
                        'GET', f'payment_methods/{stripe_object["payment_method"]}'
                    )
                    stripe_object['payment_method'] = payment_method
                    self._include_setup_intent_in_payment_data(stripe_object, data)
                elif event['type'] == 'charge.refunded':  # Refund operation (refund creation).
                    refunds = stripe_object['refunds']['data']

                    # The refunds linked to this charge are paginated, fetch the remaining refunds.
                    has_more = stripe_object['refunds']['has_more']
                    while has_more:
                        payload = {
                            'charge': stripe_object['id'],
                            'starting_after': refunds[-1]['id'],
                            'limit': 100,
                        }
                        additional_refunds = tx_sudo._send_api_request(
                            'GET', 'refunds', data=payload
                        )
                        refunds += additional_refunds['data']
                        has_more = additional_refunds['has_more']

                    # Process the refunds for which a refund transaction has not been created yet.
                    processed_refund_ids = tx_sudo.child_transaction_ids.filtered(
                        lambda tx: tx.operation == 'refund'
                    ).mapped('provider_reference')
                    for refund in filter(lambda r: r['id'] not in processed_refund_ids, refunds):
                        refund_tx_sudo = self._create_refund_tx_from_refund(tx_sudo, refund)
                        self._include_refund_in_payment_data(refund, data)
                        refund_tx_sudo._process('stripe', data)
                    # Don't process the payment data for the source transaction.
                    return request.make_json_response('')
                elif event['type'] == 'charge.refund.updated':  # Refund operation (with update).
                    # A refund was updated by Stripe after it was already processed (possibly to
                    # cancel it). This can happen when the customer's payment method can no longer
                    # be topped up (card expired, account closed...). The `tx_sudo` record is the
                    # refund transaction to update.
                    self._include_refund_in_payment_data(stripe_object, data)

                # Process the payment data crafted with Stripe API objects
                tx_sudo._process('stripe', data)
        except ValidationError:  # Acknowledge the notification to avoid getting spammed
            _logger.exception("Unable to process the payment data; skipping to acknowledge")
        return request.make_json_response('')

    @staticmethod
    def _include_payment_intent_in_payment_data(payment_intent, payment_data):
        payment_data.update({
            'payment_intent': payment_intent,
            'payment_method': payment_intent.get('payment_method'),
        })

    @staticmethod
    def _include_setup_intent_in_payment_data(setup_intent, payment_data):
        payment_data.update({
            'setup_intent': setup_intent,
            'payment_method': setup_intent.get('payment_method'),
        })

    @staticmethod
    def _include_refund_in_payment_data(refund, payment_data):
        payment_data.update(refund=refund)

    @staticmethod
    def _create_refund_tx_from_refund(source_tx_sudo, refund_object):
        """ Create a refund transaction based on Stripe data.

        :param recordset source_tx_sudo: The source transaction for which a refund is initiated, as
                                         a sudoed `payment.transaction` record.
        :param dict refund_object: The Stripe refund object to create the refund from.
        :return: The created refund transaction.
        :rtype: recordset of `payment.transaction`
        """
        amount_to_refund = refund_object['amount']
        converted_amount = payment_utils.to_major_currency_units(
            amount_to_refund,
            source_tx_sudo.currency_id,
            arbitrary_decimal_number=const.CURRENCY_DECIMALS.get(source_tx_sudo.currency_id.name),
        )
        return source_tx_sudo._create_child_transaction(converted_amount, is_refund=True)

    def _verify_signature(self, tx_sudo):
        """Check that the received signature matches the expected one.

        See https://stripe.com/docs/webhooks/signatures#verify-manually.

        :param payment.transaction tx_sudo: The sudoed transaction referenced by the payment data.
        :return: None
        :raise Forbidden: If the timestamp is too old or if the signatures don't match.
        """
        webhook_secret = stripe_utils.get_webhook_secret(tx_sudo.provider_id)
        if not webhook_secret:
            _logger.warning("ignored webhook event due to undefined webhook secret")
            return

        notification_payload = request.httprequest.data.decode('utf-8')
        signature_entries = request.httprequest.headers['Stripe-Signature'].split(',')
        signature_data = {k: v for k, v in [entry.split('=') for entry in signature_entries]}

        # Retrieve the timestamp from the data
        event_timestamp = int(signature_data.get('t', '0'))
        if not event_timestamp:
            _logger.warning("Received payment data with missing timestamp")
            raise Forbidden()

        # Check if the timestamp is not too old
        if datetime.utcnow().timestamp() - event_timestamp > self.WEBHOOK_AGE_TOLERANCE:
            _logger.warning("Received payment data with outdated timestamp: %s", event_timestamp)
            raise Forbidden()

        # Retrieve the received signature from the data
        received_signature = signature_data.get('v1')
        if not received_signature:
            _logger.warning("Received payment data with missing signature")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the data
        signed_payload = f'{event_timestamp}.{notification_payload}'
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'), signed_payload.encode('utf-8'), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received payment data with invalid signature")
            raise Forbidden()

    @http.route(_apple_pay_domain_association_url, type='http', auth='public', csrf=False)
    def stripe_apple_pay_get_domain_association_file(self):
        """ Get the domain association file for Stripe's Apple Pay.

        Stripe handles the process of "merchant validation" described in Apple's documentation for
        Apple Pay on the Web. Stripe and Apple will access this route to check the content of the
        file and verify that the web domain is registered.

        See https://stripe.com/docs/stripe-js/elements/payment-request-button#verifying-your-domain-with-apple-pay.

        :return: The content of the domain association file.
        :rtype: str
        """
        with file_open(
            'payment_stripe/static/files/apple-developer-merchantid-domain-association'
        ) as f:
            return f.read()
