# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import namedtuple


API_VERSION = '2019-05-16'  # The API version of Stripe implemented in this module

# Stripe proxy URL
PROXY_URL = 'https://stripe.api.odoo.com/api/stripe/'

# Support payment method types
PMT = namedtuple('PaymentMethodType', ['name', 'countries', 'currencies', 'recurrence'])
PAYMENT_METHOD_TYPES = [
    PMT('card', [], [], 'recurring'),
    PMT('ideal', ['nl'], ['eur'], 'punctual'),
    PMT('bancontact', ['be'], ['eur'], 'punctual'),
    PMT('eps', ['at'], ['eur'], 'punctual'),
    PMT('giropay', ['de'], ['eur'], 'punctual'),
    PMT('p24', ['pl'], ['eur', 'pln'], 'punctual'),
]

# Mapping of transaction states to Stripe objects ({Payment,Setup}Intent, Charge, Refund) statuses.
# For each object's exhaustive status list, see:
# https://stripe.com/docs/api/payment_intents/object#payment_intent_object-status
# https://stripe.com/docs/api/setup_intents/object#setup_intent_object-status
# https://stripe.com/docs/api/charges/object#charge_object-status
# https://stripe.com/docs/api/refunds/object#refund_object-status
STATUS_MAPPING = {
    'draft': ('requires_confirmation', 'requires_action'),
    'pending': ('processing', 'pending'),
    'authorized': ('requires_capture',),
    'done': ('succeeded',),
    'cancel': ('canceled',),
    'error': ('requires_payment_method', 'failed',),
}

# Events which are handled by the webhook
HANDLED_WEBHOOK_EVENTS = [
    'payment_intent.amount_capturable_updated',
    'payment_intent.succeeded',
    'payment_intent.payment_failed',
    'setup_intent.succeeded',
    'charge.refunded',  # A refund has been issued.
    'charge.refund.updated',  # The refund status has changed, possibly from succeeded to failed.
]

# The countries supported by Stripe. See https://stripe.com/global page.
SUPPORTED_COUNTRIES = {
    'AE',
    'AT',
    'AU',
    'BE',
    'BG',
    'BR',
    'CA',
    'CH',
    'CY',
    'CZ',
    'DE',
    'DK',
    'EE',
    'ES',
    'FI',
    'FR',
    'GB',
    'GI',  # Beta
    'GR',
    'HK',
    'HR',  # Beta
    'HU',
    'ID',  # Beta
    'IE',
    'IT',
    'JP',
    'LI',  # Beta
    'LT',
    'LU',
    'LV',
    'MT',
    'MX',
    'MY',
    'NL',
    'NO',
    'NZ',
    'PH',  # Beta
    'PL',
    'PT',
    'RO',
    'SE',
    'SG',
    'SI',
    'SK',
    'TH',  # Beta
    'US',
}
