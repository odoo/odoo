# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The currencies supported by Flutterwave, in ISO 4217 format.
# See https://flutterwave.com/us/support/general/what-are-the-currencies-accepted-on-flutterwave.
# Last website update: June 2022.
# Last seen online: 24 November 2022.
SUPPORTED_CURRENCIES = [
    'GBP',
    'CAD',
    'XAF',
    'CLP',
    'COP',
    'EGP',
    'EUR',
    'GHS',
    'GNF',
    'KES',
    'MWK',
    'MAD',
    'NGN',
    'RWF',
    'SLL',
    'STD',
    'ZAR',
    'TZS',
    'UGX',
    'USD',
    'XOF',
    'ZMW',
]

# Mapping of transaction states to Flutterwave payment statuses.
PAYMENT_STATUS_MAPPING = {
    'pending': ['pending auth'],
    'done': ['successful'],
    'cancel': ['cancelled'],
    'error': ['failed'],
}

PAYMENT_METHODS_MAPPING = {
    'bank_transfer': 'banktransfer',
}
