# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The currencies supported by Flutterwave, in ISO 4217 format.
# See https://support.flutterwave.com/en/articles/3632719-accepted-currencies.
SUPPORTED_CURRENCIES = [
    'ARS',
    'BRL',
    'GBP',
    'CAD',
    'CVE',
    'CLP',
    'COP',
    'CDF',
    'EGP',
    'EUR',
    'GMD',
    'GHS',
    'GNF',
    'KES',
    'LRD',
    'MWK',
    'MXN',
    'MAD',
    'MZN',
    'NGN',
    'SOL',
    'RWF',
    'SLL',
    'STD',
    'ZAR',
    'TZS',
    'UGX',
    'USD',
    'XAF',
    'XOF',
    'ZMK',
    'ZMW',
]


# Mapping of transaction states to Flutterwave payment statuses.
PAYMENT_STATUS_MAPPING = {
    'pending': ['pending auth'],
    'done': ['successful'],
    'cancel': ['cancelled'],
    'error': ['failed'],
}
