# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Only 5 countries are supported and for each country the matching currency is required.
# For each country, different api endpoints are used.
# Paymob deals with the amount in cents, so each amount needs to be converted according to
# the number of cents in each currency
# Last seen on: 17 December 2024.
# ISO 4217 codes of currencies supported by Paymob

PAYMOB_CONFIG = {
    'AED': {
        'amount_cents': 100,
        'country_code': 'AE',
        'api_prefix': 'uae',
    },
    'EGP': {
        'amount_cents': 100,
        'country_code': 'EG',
        'api_prefix': 'accept',
    },
    'OMR': {
        'amount_cents': 1000,
        'country_code': 'OM',
        'api_prefix': 'oman',
    },
    'PKR': {
        'amount_cents': 100,
        'country_code': 'PK',
        'api_prefix': 'pakistan',
    },
    'SAR': {
        'amount_cents': 100,
        'country_code': 'SA',
        'api_prefix': 'ksa',
    },
}

# The codes of the payment methods to activate when Paymob is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'card',
}

PAYMOB_SIGNATURE_FIELDS = [
    'amount_cents',
    'created_at',
    'currency',
    'error_occured',
    'has_parent_transaction',
    'id',
    'integration_id',
    'is_3d_secure',
    'is_auth',
    'is_capture',
    'is_refunded',
    'is_standalone_payment',
    'is_voided',
    'order',
    'owner',
    'pending',
    'source_data.pan',
    'source_data.sub_type',
    'source_data.type',
    'success',
]
