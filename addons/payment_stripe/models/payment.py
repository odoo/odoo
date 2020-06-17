# coding: utf-8

from collections import namedtuple
from datetime import datetime
from hashlib import sha256
import hmac
import json
import logging
import requests
import pprint
from requests.exceptions import HTTPError
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.http import request
from odoo.tools.float_utils import float_round
from odoo.tools import consteq
from odoo.exceptions import ValidationError
from .stripe_request import StripeApi

from odoo.addons.payment_stripe.controllers.main import StripeController

_logger = logging.getLogger(__name__)

# The following currencies are integer only, see https://stripe.com/docs/currencies#zero-decimal
INT_CURRENCIES = [
    'BIF', 'XAF', 'XPF', 'CLP', 'KMF', 'DJF', 'GNF', 'JPY', 'MGA', 'PYG', 'RWF', 'KRW',
    'VUV', 'VND', 'XOF'
]
STRIPE_SIGNATURE_AGE_TOLERANCE = 600  # in seconds


class PaymentAcquirerStripe(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('stripe', 'Stripe')
    ], ondelete={'stripe': 'set default'})
    stripe_secret_key = fields.Char(required_if_provider='stripe', groups='base.group_user')
    stripe_publishable_key = fields.Char(required_if_provider='stripe', groups='base.group_user')
    stripe_webhook_secret = fields.Char(
        string='Stripe Webhook Secret', groups='base.group_user',
        help="If you enable webhooks, this secret is used to verify the electronic "
             "signature of events sent by Stripe to Odoo. Failing to set this field in Odoo "
             "will disable the webhook system for this acquirer entirely.")
    stripe_image_url = fields.Char(
        "Checkout Image URL", groups='base.group_user',
        help="A relative or absolute URL pointing to a square image of your "
             "brand or product. As defined in your Stripe profile. See: "
             "https://stripe.com/docs/checkout")

    def stripe_form_generate_values(self, tx_values):
        self.ensure_one()

        base_url = self.get_base_url()
        stripe_session_data = {
            'line_items[][amount]': int(tx_values['amount'] if tx_values['currency'].name in INT_CURRENCIES else float_round(tx_values['amount'] * 100, 2)),
            'line_items[][currency]': tx_values['currency'].name,
            'line_items[][quantity]': 1,
            'line_items[][name]': tx_values['reference'],
            'client_reference_id': tx_values['reference'],
            'success_url': urls.url_join(base_url, StripeController._success_url) + '?reference=%s' % tx_values['reference'],
            'cancel_url': urls.url_join(base_url, StripeController._cancel_url) + '?reference=%s' % tx_values['reference'],
            'payment_intent_data[description]': tx_values['reference'],
            'payment_intent_data[capture_method]': 'manual' if self.capture_manually else 'automatic',
            'customer_email': tx_values.get('partner_email') or tx_values.get('billing_partner_email'),
        }

        self._add_available_payment_method_types(stripe_session_data, tx_values)

        session = StripeApi(self).create_checkout_session(**stripe_session_data)
        tx_values['session_id'] = session['id']
        tx = self.env['payment.transaction'].sudo().search([('reference', '=', tx_values['reference'])])
        tx.stripe_payment_intent = session['payment_intent']

        return tx_values

    @api.model
    def _add_available_payment_method_types(self, stripe_session_data, tx_values):
        """
        Add payment methods available for the given transaction

        :param stripe_session_data: dictionary to add the payment method types to
        :param tx_values: values of the transaction to consider the payment method types for
        """
        PMT = namedtuple('PaymentMethodType', ['name', 'countries', 'currencies', 'recurrence'])
        all_payment_method_types = [
            PMT('card', [], [], 'recurring'),
            PMT('ideal', ['nl'], ['eur'], 'punctual'),
            PMT('bancontact', ['be'], ['eur'], 'punctual'),
            PMT('eps', ['at'], ['eur'], 'punctual'),
            PMT('giropay', ['de'], ['eur'], 'punctual'),
            PMT('p24', ['pl'], ['eur', 'pln'], 'punctual'),
        ]

        country = (tx_values['billing_partner_country'].code or 'no_country').lower()
        pmt_country_filtered = filter(lambda pmt: not pmt.countries or country in pmt.countries, all_payment_method_types)
        currency = (tx_values.get('currency').name or 'no_currency').lower()
        pmt_currency_filtered = filter(lambda pmt: not pmt.currencies or currency in pmt.currencies, pmt_country_filtered)
        pmt_recurrence_filtered = filter(lambda pmt: tx_values.get('type') != 'form_save' or pmt.recurrence == 'recurring',
                                    pmt_currency_filtered)

        available_payment_method_types = map(lambda pmt: pmt.name, pmt_recurrence_filtered)

        for idx, payment_method_type in enumerate(available_payment_method_types):
            stripe_session_data[f'payment_method_types[{idx}]'] = payment_method_type

    @api.model
    def _get_stripe_api_url(self):
        return 'https://api.stripe.com/v1/'

    @api.model
    def stripe_s2s_form_process(self, data):
        if 'card' in data and not data.get('card'):
            # coming back from a checkout payment and iDeal (or another non-card pm)
            # can't save the token if it's not a card
            # note that in the case of a s2s payment, 'card' wont be
            # in the data dict because we need to fetch it from the stripe server
            _logger.info('unable to save card info from Stripe since the payment was not done with a card')
            return self.env['payment.token']
        last4 = data.get('card', {}).get('last4')
        if not last4:
            # PM was created with a setup intent, need to get last4 digits through
            # yet another call -_-
            acquirer_id = self.env['payment.acquirer'].browse(int(data['acquirer_id']))
            pm = data.get('payment_method')
            res = StripeApi(acquirer_id.sudo()).get_payment_method(pm)
            last4 = res.get('card', {}).get('last4', '****')

        payment_token = self.env['payment.token'].sudo().create({
            'acquirer_id': int(data['acquirer_id']),
            'partner_id': int(data['partner_id']),
            'stripe_payment_method': data.get('payment_method'),
            'name': 'XXXXXXXXXXXX%s' % last4,
            'acquirer_ref': data.get('customer')
        })
        return payment_token

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super(PaymentAcquirerStripe, self)._get_feature_support()
        res['tokenize'].append('stripe')
        res['authorize'].append('stripe')
        return res

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
            raise ValidationError('Stripe Webhook data does not conform to the expected API.')
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

    def _handle_checkout_webhook(self, checkout_object: dir):
        """
        Process a checkout.session.completed Stripe web hook event,
        mark related payment successful

        :param checkout_object: provided in the request body
        :return: True if and only if handling went well, False otherwise
        :raises ValidationError: if input isn't usable
        """
        tx_reference = checkout_object.get('client_reference_id')
        data = {'reference': tx_reference}
        try:
            odoo_tx = self.env['payment.transaction']._stripe_form_get_tx_from_data(data)
        except ValidationError as e:
            _logger.info('Received notification for tx %s. Skipped it because of %s', tx_reference, e)
            return False

        PaymentAcquirerStripe._verify_stripe_signature(odoo_tx.acquirer_id)

        stripe_tx = StripeApi(odoo_tx.acquirer_id.sudo()).get_payment_intent(odoo_tx)

        if 'error' in stripe_tx:
            error = stripe_tx['error']
            raise ValidationError("Could not fetch Stripe payment intent related to %s because of %s; see %s" % (
                odoo_tx, error['message'], error['doc_url']))

        if stripe_tx.get('charges') and stripe_tx.get('charges').get('total_count'):
            charge = stripe_tx.get('charges').get('data')[0]
            data.update(charge)

        return odoo_tx.form_feedback(data, 'stripe')


class PaymentTransactionStripe(models.Model):
    _inherit = 'payment.transaction'

    stripe_payment_intent = fields.Char(string='Stripe Payment Intent ID', readonly=True)
    stripe_payment_intent_secret = fields.Char(string='Stripe Payment Intent Secret', readonly=True)

    def _get_processing_info(self):
        res = super()._get_processing_info()
        if self.acquirer_id.provider == 'stripe':
            stripe_info = {
                'stripe_payment_intent': self.stripe_payment_intent,
                'stripe_payment_intent_secret': self.stripe_payment_intent_secret,
                'stripe_publishable_key': self.acquirer_id.stripe_publishable_key,
            }
            res.update(stripe_info)
        return res

    def form_feedback(self, data, acquirer_name):
        if data.get('reference') and acquirer_name == 'stripe':
            transaction = self.env['payment.transaction'].search([('reference', '=', data['reference'])])

            res = StripeApi(transaction.acquirer_id).get_payment_intent(transaction)

            data.update(res)
            _logger.info('Stripe: entering form_feedback with post data %s' % pprint.pformat(data))
        return super(PaymentTransactionStripe, self).form_feedback(data, acquirer_name)

    def stripe_s2s_do_transaction(self, **kwargs):
        self.ensure_one()

        capture_method = 'manual' if self.acquirer_id.capture_manually else 'automatic'
        result = StripeApi(self.acquirer_id).create_payment_intent(self, capture_method=capture_method)

        return self._stripe_s2s_validate_tree(result)

    def stripe_s2s_capture_transaction(self, **kwargs):
        self.ensure_one()

        result = StripeApi(self.acquirer_id).capture_payment_intent(self)

        return self._stripe_s2s_validate_tree(result)

    def stripe_s2s_void_transaction(self, **kwargs):
        self.ensure_one()

        result = StripeApi(self.acquirer_id).cancel_payment_intent(self)

        return self._stripe_s2s_validate_tree(result)

    def stripe_s2s_do_refund(self, **kwargs):
        self.ensure_one()

        result = StripeApi(self.acquirer_id).create_refund(self)

        return self._stripe_s2s_validate_tree(result)

    @api.model
    def _stripe_form_get_tx_from_data(self, data):
        """ Given a data dict coming from stripe, verify it and find the related
        transaction record. """
        reference = data.get('reference')
        if not reference:
            stripe_error = data.get('error', {}).get('message', '')
            _logger.error('Stripe: invalid reply received from stripe API, looks like '
                          'the transaction failed. (error: %s)', stripe_error or 'n/a')
            error_msg = _("We're sorry to report that the transaction has failed.")
            if stripe_error:
                error_msg += " " + (_("Stripe gave us the following info about the problem: '%s'") %
                                    stripe_error)
            error_msg += " " + _("Perhaps the problem can be solved by double-checking your "
                                 "credit card details, or contacting your bank?")
            raise ValidationError(error_msg)

        tx = self.search([('reference', '=', reference)])
        if not tx:
            error_msg = _('Stripe: no order found for reference %s', reference)
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        elif len(tx) > 1:
            error_msg = _('Stripe: %(count)s orders found for reference %(reference)s', count=len(tx), reference=reference)
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return tx[0]

    def _stripe_s2s_validate_tree(self, tree):
        """
        Update self according to its counterpart from Stripe

        :param tree: the payment_intent from Stripe
        :return: True if and only if everything went well
        """
        self.ensure_one()
        if self.state == 'done':
            _logger.info('Stripe: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        status = tree.get('status')
        tx_id = tree.get('id')
        tx_secret = tree.get("client_secret")
        pi_id = tree.get('payment_intent')
        vals = {
            "date": fields.datetime.now(),
            "acquirer_reference": tx_id,
            "stripe_payment_intent": pi_id or tx_id,
            "stripe_payment_intent_secret": tx_secret
        }
        if status in ('succeeded', 'requires_capture'):
            self.write(vals)
            init_state = self.state
            if status == 'succeeded':
                self._set_transaction_done()
            else:
                self._set_transaction_authorized()
            if init_state != 'authorized':
                self.execute_callback()
            if self.type == 'form_save':
                s2s_data = {
                    'customer': tree.get('customer'),
                    'payment_method': tree.get('payment_method'),
                    'card': tree.get('payment_method_details').get('card'),
                    'acquirer_id': self.acquirer_id.id,
                    'partner_id': self.partner_id.id
                }
                token = self.acquirer_id.stripe_s2s_form_process(s2s_data)
                self.payment_token_id = token.id
            if self.payment_token_id:
                self.payment_token_id.verified = True
            return True
        if status in ('processing', 'requires_action'):
            self.write(vals)
            self._set_transaction_pending()
            return True
        if status == 'requires_payment_method':
            self._set_transaction_cancel()
            StripeApi(self.acquirer_id).cancel_payment_intent(self)
            return False
        if status == 'canceled':
            self.write({'state_message': tree.get('cancellation_reason')})
            self._set_transaction_cancel()
            return True
        else:
            error = tree.get("failure_message") or tree.get('error', {}).get('message')
            self._set_transaction_error(error)
            return False

    def _stripe_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        if data.get('amount') != int(self.amount if self.currency_id.name in INT_CURRENCIES else float_round(self.amount * 100, 2)):
            invalid_parameters.append(('Amount', data.get('amount'), self.amount * 100))
        if data.get('currency').upper() != self.currency_id.name:
            invalid_parameters.append(('Currency', data.get('currency'), self.currency_id.name))
        if data.get('payment_intent') and data.get('payment_intent') != self.stripe_payment_intent:
            invalid_parameters.append(('Payment Intent', data.get('payment_intent'), self.stripe_payment_intent))
        return invalid_parameters

    def _stripe_form_validate(self, data):
        return self._stripe_s2s_validate_tree(data)


class PaymentTokenStripe(models.Model):
    _inherit = 'payment.token'

    stripe_payment_method = fields.Char('Payment Method ID')

    @api.model
    def stripe_create(self, values):
        if values.get('stripe_payment_method') and not values.get('acquirer_ref'):
            partner_id = self.env['res.partner'].browse(values.get('partner_id'))
            payment_acquirer = self.env['payment.acquirer'].browse(values.get('acquirer_id'))

            stripe_api = StripeApi(payment_acquirer)
            customer_res = stripe_api.create_customer(email=partner_id.email)
            stripe_api.attach_payment_method(values['stripe_payment_method'], customer_res.get('id'))

            return {
                'acquirer_ref': customer_res['id'],
            }
        return values

    def _stripe_sca_migrate_customer(self):
        """Migrate a token from the old implementation of Stripe to the SCA one.

        In the old implementation, it was possible to create a valid charge just by
        giving the customer ref to ask Stripe to use the default source (= default
        card). Since we have a one-to-one matching between a saved card, this used to
        work well - but now we need to specify the payment method for each call and so
        we have to contact stripe to get the default source for the customer and save it
        in the payment token.
        This conversion will happen once per token, the first time it gets used following
        the installation of the module."""
        self.ensure_one()
        stripe_api = StripeApi(self.acquirer_id)
        data = stripe_api.get_customer(self.acquirer_ref)
        sources = data.get('sources', {}).get('data', [])
        pm_ref = False
        if sources:
            if len(sources) > 1:
                _logger.warning('stripe sca customer conversion: there should be a single saved source per customer!')
            pm_ref = sources[0].get('id')
        else:
            payment_methods = stripe_api.list_payment_methods(customer=self.acquirer_ref)
            cards = payment_methods.get('data', [])
            if len(cards) > 1:
                _logger.warning('stripe sca customer conversion: there should be a single saved source per customer!')
            pm_ref = cards and cards[0].get('id')
        if not pm_ref:
            raise ValidationError(_('Unable to convert Stripe customer for SCA compatibility. Is there at least one card for this customer in the Stripe backend?'))
        self.stripe_payment_method = pm_ref
        _logger.info('converted old customer ref to sca-compatible record for payment token %s', self.id)
