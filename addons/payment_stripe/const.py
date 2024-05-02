# Part of Odoo. See LICENSE file for full copyright and licensing details.

API_VERSION = '2019-05-16'  # The API version of Stripe implemented in this module

# Stripe proxy URL
PROXY_URL = 'https://stripe.api.odoo.com/api/stripe/'

# The payment methods for which Stripe supports tokenization.
# See https://stripe.com/docs/payments/payment-methods/integration-options.
PAYMENT_METHODS_TOKENIZATION_SUPPORT = {
    'acss_debit': True,
    'affirm': False,
    'afterpay_clearpay': False,
    'alipay': False,
    'apple_pay': True,
    'au_becs_debit': True,
    'bacs_debit': False,  # Stripe doesn't support saving BACS with setupIntent.
    'bancontact': False,
    'blik': False,
    'boleto': True,
    'card': True,
    'cashapp': True,
    'customer_balance': False,
    'eps': False,
    'fpx': False,
    'giropay': False,
    'google_pay': True,
    'grabpay': False,
    'ideal': False,
    'klarna': False,
    'konbini': False,
    'link': True,
    'mobilepay': False,
    'oxxo': False,
    'p24': False,
    'paynow': False,
    'paypal': True,
    'promptpay': False,
    'sepa_debit': True,
    'sofort': False,
    'us_bank_account': True,
    'wechat_pay': False,
    'zip': False,
}

# Mapping of transaction states to Stripe objects ({Payment,Setup}Intent, Refund) statuses.
# For each object's exhaustive status list, see:
# https://stripe.com/docs/api/payment_intents/object#payment_intent_object-status
# https://stripe.com/docs/api/setup_intents/object#setup_intent_object-status
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
    'payment_intent.processing',
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

# Businesses in supported outlying territories should register for a Stripe account with the parent
# territory selected as the Country.
# See https://support.stripe.com/questions/stripe-availability-for-outlying-territories-of-supported-countries.
COUNTRY_MAPPING = {
    'MQ': 'FR',  # Martinique
    'GP': 'FR',  # Guadeloupe
    'GF': 'FR',  # French Guiana
    'RE': 'FR',  # Réunion
    'YT': 'FR',  # Mayotte
    'MF': 'FR',  # Saint-Martin
}
