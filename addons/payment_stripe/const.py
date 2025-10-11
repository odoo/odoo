# Part of Odoo. See LICENSE file for full copyright and licensing details.

API_VERSION = '2019-05-16'  # The API version of Stripe implemented in this module

# Stripe proxy URL
PROXY_URL = 'https://stripe.api.odoo.com/api/stripe/'

# The codes of the payment methods to activate when Stripe is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'card',
    'bancontact',
    'eps',
    'giropay',
    'ideal',
    'p24',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
}

# Mapping of payment method codes to Stripe codes.
PAYMENT_METHODS_MAPPING = {
    'ach_direct_debit': 'us_bank_account',
    'bacs_direct_debit': 'bacs_debit',
    'becs_direct_debit': 'au_becs_debit',
    'sepa_direct_debit': 'sepa_debit',
    'afterpay': 'afterpay_clearpay',
    'clearpay': 'afterpay_clearpay',
    'cash_app_pay': 'cashapp',
    'mobile_pay': 'mobilepay',
    'unknown': 'card',  # For express checkout.
}

INDIAN_MANDATES_SUPPORTED_CURRENCIES = [
    'USD',
    'EUR',
    'GBP',
    'SGD',
    'CAD',
    'CHF',
    'SEK',
    'AED',
    'JPY',
    'NOK',
    'MYR',
    'HKD',
]

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
    'payment_intent.canceled',
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

# Stripe-specific mapping of currency codes in ISO 4217 format to the number of decimals.
# Only currencies for which Stripe does not follow the ISO 4217 norm are listed here.
CURRENCY_DECIMALS = {
    # https://docs.stripe.com/currencies#special-cases
    'ISK': 2,
    'UGX': 2,
    # https://docs.stripe.com/currencies#zero-decimal
    'MGA': 0,
}
