# coding: utf-8


from datetime import datetime
from hashlib import sha256
import hmac
import logging
import requests
import pprint
from requests.exceptions import HTTPError
from werkzeug import urls


from odoo import api, fields, models, _
from odoo.http import request
from odoo.tools.float_utils import float_round
from odoo.tools import consteq
from odoo.addons.payment.models.payment_acquirer import ValidationError

_logger = logging.getLogger(__name__)

# The following currencies are integer only, see https://stripe.com/docs/currencies#zero-decimal
INT_CURRENCIES = [
    u'BIF', u'XAF', u'XPF', u'CLP', u'KMF', u'DJF', u'GNF', u'JPY', u'MGA', u'PYG', u'RWF', u'KRW',
    u'VUV', u'VND', u'XOF'
]
STRIPE_SIGNATURE_AGE_TOLERANCE = 600  # in seconds


class PaymentAcquirerStripeCheckoutWH(models.Model):
    _inherit = 'payment.acquirer'

    stripe_webhook_secret = fields.Char(
        string='Stripe Webhook Secret', groups='base.group_system',
        help="If you enable webhooks, this secret is used to verify the electronic "
             "signature of events sent by Stripe to Odoo. Failing to set this field in Odoo "
             "will disable the webhook system for this acquirer entirely.")

    def _handle_stripe_webhook(self, data):
        """Process a webhook payload from Stripe.

        Post-process a webhook payload to act upon the matching payment.transaction
        record in Odoo.
        """
        wh_type = data.get('type')
        if wh_type != 'checkout.session.completed':
            _logger.info('unsupported webhook type %s, ignored', wh_type)
            return False

        _logger.info('handling %s webhook event from stripe', wh_type)

        stripe_object = data.get('data', {}).get('object')
        if not stripe_object:
            raise ValidationError(_('Stripe Webhook data does not conform to the expected API.'))
        if wh_type == 'checkout.session.completed':
            return self._handle_checkout_webhook(stripe_object)
        return False

    def _verify_stripe_signature(self):
        """
        :return: true if and only if signature matches hash of payload calculated with secret
        :raises ValidationError: if signature doesn't match
        """
        if not self.stripe_webhook_secret:
            raise ValidationError('webhook event received but webhook secret is not configured')
        signature = request.httprequest.headers.get('Stripe-Signature')
        body = request.httprequest.data

        sign_data = {k: v for (k, v) in [s.split('=') for s in signature.split(',')]}
        event_timestamp = int(sign_data['t'])
        if datetime.utcnow().timestamp() - event_timestamp > STRIPE_SIGNATURE_AGE_TOLERANCE:
            _logger.error('stripe event is too old, event is discarded')
            raise ValidationError('event timestamp older than tolerance')

        signed_payload = "%s.%s" % (event_timestamp, body.decode('utf-8'))

        actual_signature = sign_data['v1']
        expected_signature = hmac.new(self.stripe_webhook_secret.encode('utf-8'),
                                      signed_payload.encode('utf-8'),
                                      sha256).hexdigest()

        if not consteq(expected_signature, actual_signature):
            _logger.error(
                'incorrect webhook signature from Stripe, check if the webhook signature '
                'in Odoo matches to one in the Stripe dashboard')
            raise ValidationError('incorrect webhook signature')

        return True

    def _handle_checkout_webhook(self, checkout_object):
        """
        Process a checkout.session.completed Stripe web hook event,
        mark related payment successful

        :param checkout_object: provided in the request body
        :return: True if and only if handling went well, False otherwise
        :raises ValidationError: if input isn't usable
        """
        tx_reference = checkout_object.get('client_reference_id')
        data = {'metadata': {'reference': tx_reference}}
        try:
            odoo_tx = self.env['payment.transaction']._stripe_form_get_tx_from_data(data)
        except ValidationError as e:
            _logger.info('Received notification for tx %s. Skipped it because of %s', tx_reference, e)
            return False

        PaymentAcquirerStripeCheckoutWH._verify_stripe_signature(odoo_tx.acquirer_id)

        url = 'payment_intents/%s' % odoo_tx.stripe_payment_intent
        stripe_tx = odoo_tx.acquirer_id._stripe_request(url)

        if 'error' in stripe_tx:
            error = stripe_tx['error']
            raise ValidationError("Could not fetch Stripe payment intent related to %s because of %s; see %s" % (
                odoo_tx, error['message'], error['doc_url']))

        if stripe_tx.get('charges') and stripe_tx.get('charges').get('total_count'):
            charge = stripe_tx.get('charges').get('data')[0]
            data.update(charge)
            data['metadata']['reference'] = tx_reference

        return odoo_tx.form_feedback(data, 'stripe')

    def _stripe_request(self, url, data=False, method='POST'):
        self.ensure_one()
        url = urls.url_join(self._get_stripe_api_url(), url)
        headers = {
            'AUTHORIZATION': 'Bearer %s' % self.sudo().stripe_secret_key,
            'Stripe-Version': '2019-05-16', # SetupIntent need a specific version
            }
        TIMEOUT = 10
        resp = requests.request(method, url, data=data, headers=headers, timeout=TIMEOUT)
        # Stripe can send 4XX errors for payment failure (not badly-formed requests)
        # check if error `code` is present in 4XX response and raise only if not
        # cfr https://stripe.com/docs/error-codes
        # these can be made customer-facing, as they usually indicate a problem with the payment
        # (e.g. insufficient funds, expired card, etc.)
        # if the context key `stripe_manual_payment` is set then these errors will be raised as ValidationError,
        # otherwise, they will be silenced, and the will be returned no matter the status.
        # This key should typically be set for payments in the present and unset for automated payments
        # (e.g. through crons)
        if not resp.ok and self._context.get('stripe_manual_payment') and (400 <= resp.status_code < 500 and resp.json().get('error', {}).get('code')):
            try:
                resp.raise_for_status()
            except HTTPError:
                _logger.error(resp.text)
                stripe_error = resp.json().get('error', {}).get('message', '')
                error_msg = " " + (_("Stripe gave us the following info about the problem: '%s'") % stripe_error)
                raise ValidationError(error_msg)
        return resp.json()


class PaymentTransactionStripeCheckoutWH(models.Model):
    _inherit = 'payment.transaction'

    stripe_payment_intent = fields.Char(string='Stripe Payment Intent ID', readonly=True)

    def _stripe_s2s_validate_tree(self, tree):
        result = super()._stripe_s2s_validate_tree(tree)

        pi_id = tree.get('payment_intent')
        if pi_id:
            self.write({
                "stripe_payment_intent": pi_id,
            })

        return result
