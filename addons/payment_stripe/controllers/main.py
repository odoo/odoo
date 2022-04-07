# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import json
import logging
import pprint
from datetime import datetime

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools.misc import file_open

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_stripe import utils as stripe_utils
from odoo.addons.payment_stripe.const import HANDLED_WEBHOOK_EVENTS


_logger = logging.getLogger(__name__)


class StripeController(http.Controller):
    _checkout_return_url = '/payment/stripe/checkout_return'
    _validation_return_url = '/payment/stripe/validation_return'
    _webhook_url = '/payment/stripe/webhook'
    _apple_pay_domain_association_url = '/.well-known/apple-developer-merchantid-domain-association'
    WEBHOOK_AGE_TOLERANCE = 10*60  # seconds

    @http.route(_checkout_return_url, type='http', auth='public', csrf=False)
    def stripe_return_from_checkout(self, **data):
        """ Process the notification data sent by Stripe after redirection from checkout.

        :param dict data: The GET params appended to the URL in `_stripe_create_checkout_session`
        """
        # Retrieve the tx based on the tx reference included in the return url
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'stripe', data
        )

        # Fetch the PaymentIntent, Charge and PaymentMethod objects from Stripe
        payment_intent = tx_sudo.acquirer_id._stripe_make_request(
            f'payment_intents/{tx_sudo.stripe_payment_intent}', method='GET'
        )
        _logger.info("received payment_intents response:\n%s", pprint.pformat(payment_intent))
        self._include_payment_intent_in_notification_data(payment_intent, data)

        # Handle the notification data crafted with Stripe API objects
        tx_sudo._handle_notification_data('stripe', data)

        # Redirect the user to the status page
        return request.redirect('/payment/status')

    @http.route(_validation_return_url, type='http', auth='public', csrf=False)
    def stripe_return_from_validation(self, **data):
        """ Process the notification data sent by Stripe after redirection for validation.

        :param dict data: The GET params appended to the URL in `_stripe_create_checkout_session`
        """
        # Retrieve the transaction based on the tx reference included in the return url
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'stripe', data
        )

        # Fetch the Session, SetupIntent and PaymentMethod objects from Stripe
        checkout_session = tx_sudo.acquirer_id._stripe_make_request(
            f'checkout/sessions/{data.get("checkout_session_id")}',
            payload={'expand[]': 'setup_intent.payment_method'},  # Expand all required objects
            method='GET'
        )
        _logger.info("received checkout/session response:\n%s", pprint.pformat(checkout_session))
        self._include_setup_intent_in_notification_data(
            checkout_session.get('setup_intent', {}), data
        )

        # Handle the notification data crafted with Stripe API objects
        tx_sudo._handle_notification_data('stripe', data)

        # Redirect the user to the status page
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='json', auth='public')
    def stripe_webhook(self):
        """ Process the notification data sent by Stripe to the webhook.

        :return: An empty string to acknowledge the notification
        :rtype: str
        """
        event = json.loads(request.httprequest.data)
        _logger.info("notification received from Stripe with data:\n%s", pprint.pformat(event))
        try:
            if event['type'] in HANDLED_WEBHOOK_EVENTS:
                stripe_object = event['data']['object']  # {Payment,Setup}Intent, Charge, or Refund.

                # Check the integrity of the event.
                data = {
                    'reference': stripe_object.get('description'),
                    'event_type': event['type'],
                    'object_id': stripe_object['id'],
                }
                tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                    'stripe', data
                )
                self._verify_notification_signature(tx_sudo)

                # Handle the notification data.
                if event['type'].startswith('payment_intent'):  # Payment operation.
                    self._include_payment_intent_in_notification_data(stripe_object, data)
                elif event['type'].startswith('setup_intent'):  # Validation operation.
                    # Fetch the missing PaymentMethod object.
                    payment_method = tx_sudo.acquirer_id._stripe_make_request(
                        f'payment_methods/{stripe_object["payment_method"]}', method='GET'
                    )
                    _logger.info(
                        "received payment_methods response:\n%s", pprint.pformat(payment_method)
                    )
                    stripe_object['payment_method'] = payment_method
                    self._include_setup_intent_in_notification_data(stripe_object, data)
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
                        additional_refunds = tx_sudo.acquirer_id._stripe_make_request(
                            'refunds', payload=payload, method='GET'
                        )
                        refunds += additional_refunds['data']
                        has_more = additional_refunds['has_more']

                    # Process the refunds for which a refund transaction has not been created yet.
                    processed_refund_ids = tx_sudo.child_transaction_ids.filtered(
                        lambda tx: tx.operation == 'refund'
                    ).mapped('acquirer_reference')
                    for refund in filter(lambda r: r['id'] not in processed_refund_ids, refunds):
                        refund_tx_sudo = self._create_refund_tx_from_refund(tx_sudo, refund)
                        self._include_refund_in_notification_data(refund, data)
                        refund_tx_sudo._handle_notification_data('stripe', data)
                    return ''  # Don't handle the notification data for the source transaction.
                elif event['type'] == 'charge.refund.updated':  # Refund operation (with update).
                    # A refund was updated by Stripe after it was already processed (possibly to
                    # cancel it). This can happen when the customer's payment method can no longer
                    # be topped up (card expired, account closed...). The `tx_sudo` record is the
                    # refund transaction to update.
                    self._include_refund_in_notification_data(stripe_object, data)

                # Handle the notification data crafted with Stripe API objects
                tx_sudo._handle_notification_data('stripe', data)
        except ValidationError:  # Acknowledge the notification to avoid getting spammed
            _logger.exception("unable to handle the notification data; skipping to acknowledge")
        return ''

    @staticmethod
    def _include_payment_intent_in_notification_data(payment_intent, notification_data):
        notification_data.update({'payment_intent': payment_intent})
        if payment_intent.get('charges', {}).get('total_count', 0) > 0:
            charge = payment_intent['charges']['data'][0]  # Use the latest charge object
            notification_data.update({
                'charge': charge,
                'payment_method': charge.get('payment_method_details'),
            })

    @staticmethod
    def _include_setup_intent_in_notification_data(setup_intent, notification_data):
        notification_data.update({
            'setup_intent': setup_intent,
            'payment_method': setup_intent.get('payment_method'),
        })

    @staticmethod
    def _include_refund_in_notification_data(refund, notification_data):
        notification_data.update(refund=refund)

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
            amount_to_refund, source_tx_sudo.currency_id
        )
        return source_tx_sudo._create_refund_transaction(amount_to_refund=converted_amount)

    def _verify_notification_signature(self, tx_sudo):
        """ Check that the received signature matches the expected one.

        See https://stripe.com/docs/webhooks/signatures#verify-manually.

        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                                  `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the timestamp is too old or if the
                signatures don't match
        """
        webhook_secret = stripe_utils.get_webhook_secret(tx_sudo.acquirer_id)
        if not webhook_secret:
            _logger.warning("ignored webhook event due to undefined webhook secret")
            return

        notification_payload = request.httprequest.data.decode('utf-8')
        signature_entries = request.httprequest.headers['Stripe-Signature'].split(',')
        signature_data = {k: v for k, v in [entry.split('=') for entry in signature_entries]}

        # Retrieve the timestamp from the data
        event_timestamp = int(signature_data.get('t', '0'))
        if not event_timestamp:
            _logger.warning("received notification with missing timestamp")
            raise Forbidden()

        # Check if the timestamp is not too old
        if datetime.utcnow().timestamp() - event_timestamp > self.WEBHOOK_AGE_TOLERANCE:
            _logger.warning("received notification with outdated timestamp: %s", event_timestamp)
            raise Forbidden()

        # Retrieve the received signature from the data
        received_signature = signature_data.get('v1')
        if not received_signature:
            _logger.warning("received notification with missing signature")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the data
        signed_payload = f'{event_timestamp}.{notification_payload}'
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'), signed_payload.encode('utf-8'), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("received notification with invalid signature")
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
        return file_open(
            'payment_stripe/static/files/apple-developer-merchantid-domain-association'
        ).read()
