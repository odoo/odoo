"""
This module mimics a subset of the API client of Stripe.
We can't use the official Stripe API client since it is not available in the debian stable repos.
"""
import requests
import logging
import pprint
from requests.exceptions import HTTPError

from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_round
from odoo import _

_logger = logging.getLogger(__name__)

BASE_URL = 'https://api.stripe.com/v1'
VERSION = '2019-05-16'  # SetupIntent need a specific version

# The following currencies are integer only, see https://stripe.com/docs/currencies#zero-decimal
INT_CURRENCIES = [
    'BIF', 'XAF', 'XPF', 'CLP', 'KMF', 'DJF', 'GNF', 'JPY', 'MGA', 'PYG', 'RWF', 'KRW',
    'VUV', 'VND', 'XOF'
]


class StripeApi:
    """
    Implementation of a subset of https://stripe.com/docs/api
    """

    def __init__(self, acquirer):
        self.publishable_key = acquirer.stripe_publishable_key
        self.secret_key = acquirer.stripe_secret_key

    def create_payment_intent(self, tx, **params):
        """
        Create a new payment intent from a PaymentTransactionStripe
        See https://stripe.com/docs/api/payment_intents/create

        To create payment_intent without capturing the amount, set parameter capture_method to 'manual'

        :param tx: create a payment intent from it
        :type tx: PaymentTransactionStripe
        :return: the created Stripe payment_intent
        """
        url = f'{BASE_URL}/payment_intents'

        if not tx.payment_token_id.stripe_payment_method:
            # old token before using sca, need to fetch data from the api
            tx.payment_token_id._stripe_sca_migrate_customer()

        pi_params = {
            'amount': int(tx.amount if tx.currency_id.name in INT_CURRENCIES else float_round(tx.amount * 100, 2)),
            'currency': tx.currency_id.name.lower(),
            'off_session': True,
            'confirm': True,
            'payment_method': tx.payment_token_id.stripe_payment_method,
            'customer': tx.payment_token_id.acquirer_ref,
            "description": tx.reference,
        }

        pi_params.update(params)
        if not tx.env.context.get('off_session'):
            pi_params.update(setup_future_usage='off_session', off_session=False)

        return self._request(url, **pi_params)

    def get_payment_intent(self, tx):
        """
        :param tx: transaction related to requested payment_intent
        :type tx: PaymentTransactionStripe
        :return: the requested Stripe payment_intent
        """
        payment_intent = tx.acquirer_reference or tx.stripe_payment_intent
        url = f'{BASE_URL}/payment_intents/{payment_intent}'

        return self._request(url, method='GET')

    def capture_payment_intent(self, tx):
        """
        Capture a previously authorized payment intent (full amount)
        See https://stripe.com/docs/api/payment_intents/capture

        :param tx: transaction we want to capture the payment_intent of
        :type tx: PaymentTransactionStripe
        :return: modified Stripe payment_intent
        """
        url = f'{BASE_URL}/payment_intents/{tx.acquirer_reference}/capture'

        return self._request(url)

    def cancel_payment_intent(self, tx):
        """
        Cancel a previously authorized payment intent (remaining amount)
        See https://stripe.com/docs/api/payment_intents/cancel

        :param tx: transaction we want to cancel the payment_intent of
        :type tx: PaymentTransactionStripe
        :return: modified Stripe payment_intent
        """
        url = f'{BASE_URL}/payment_intents/{tx.acquirer_reference}/cancel'

        return self._request(url)

    def get_payment_method(self, payment_method):
        """
        See https://stripe.com/docs/api/payment_methods/retrieve
        """
        url = f'{BASE_URL}/payment_methods/{payment_method}'
        return self._request(url, method='GET', data=False)

    def list_payment_methods(self, customer, payment_method_type='card'):
        """
        See https://stripe.com/docs/api/payment_methods/list

        :param customer: the Stripe ID of the customer whose payment_method's will be retrieved
        :param payment_method_type: A required filter on the list
        """
        url = f'{BASE_URL}/payment_methods'

        return self._request(url, method='GET', customer=customer, type=payment_method_type)

    def attach_payment_method(self, payment_method, customer):
        """
        Attach a payment method to a customer for future payments
        See https://stripe.com/docs/api/payment_methods/attach
        """
        url = f'{BASE_URL}/payment_methods/{payment_method}/attach'

        return self._request(url, customer=customer)

    def create_refund(self, tx):
        """
        Create a new refund for an existing charge

        :param tx: the transaction to refund (full amount)
        :type tx: PaymentTransactionStripe
        :return: the created refund
        """
        url = f'{BASE_URL}/refunds'

        pi = self.get_payment_intent(tx)
        charge_id = pi['charges']['data'][0]['id']

        refund_params = {
            'charge': charge_id,
            'metadata[reference]': tx.reference,
        }

        return self._request(url, **refund_params)

    def create_checkout_session(self, **kwargs):
        """
        See https://stripe.com/docs/api/checkout/sessions/create
        """
        url = f'{BASE_URL}/checkout/sessions'

        return self._request(url, **kwargs)

    def create_setup_intent(self):
        """
        See https://stripe.com/docs/api/setup_intents/create
        """
        url = f'{BASE_URL}/setup_intents'
        params = {
            'usage': 'off_session',
        }

        return self._request(url, **params)

    def create_customer(self, **params):
        """
        See https://stripe.com/docs/api/customers/create
        """
        url = f'{BASE_URL}/customers'

        return self._request(url, **params)

    def get_customer(self, customer):
        """
        See https://stripe.com/docs/api/customers/retrieve
        """
        url = f'{BASE_URL}/customers/{customer}'

        return self._request(url, method='GET')

    def _request(self, url, method='POST', stripe_manual_payment=False, **params):
        """
        General purpose Stripe client

        :param url: to attack
        :param method: HTTP verb
        :param stripe_manual_payment: determine if the errors must face a user (True means they will)
        :param params: any params to send to Stripe
        :return: Stripe response
        """
        headers = {
            'AUTHORIZATION': 'Bearer %s' % self.secret_key,
            'Stripe-Version': VERSION,
        }
        _logger.info(f'Sending values to Stripe URL {url}:\n{pprint.pformat(params)}')
        resp = requests.request(method, url, data=params, headers=headers)
        json = resp.json()
        _logger.info(f'Values received:\n{pprint.pformat(json)}')

        # Stripe can send 4XX errors for payment failure (not badly-formed requests)
        # check if error `code` is present in 4XX response and raise only if not
        # cfr https://stripe.com/docs/error-codes
        # these can be made customer-facing, as they usually indicate a problem with the payment
        # (e.g. insufficient funds, expired card, etc.)
        # if the context key `stripe_manual_payment` is set then these errors will be raised as ValidationError,
        # otherwise, they will be silenced, and the will be returned no matter the status.
        # This key should typically be set for payments in the present and unset for automated payments
        # (e.g. through crons)
        if not resp.ok and stripe_manual_payment \
                and (400 <= resp.status_code < 500 and json.get('error', {}).get('code')):
            try:
                resp.raise_for_status()
            except HTTPError:
                _logger.error(resp.text)
                stripe_error = json.get('error', {}).get('message', '')
                error_msg = " " + (_("Stripe gave us the following info about the problem:") + " '%s'" % stripe_error)
                raise ValidationError(error_msg)
        return json
