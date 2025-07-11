# Part of Odoo. See LICENSE file for full copyright and licensing details.


# The codes of the payment methods to activate when Iyzico is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods
    'card',
}

# Mapping of transaction states to Iyzico payment statuses.
PAYMENT_STATUS_MAPPING = {
    'done': ('SUCCESS',),
    'error': ('FAILURE',),
}

# The currencies supported by Iyzico, in ISO 4217 format.
SUPPORTED_CURRENCIES = [
    'CHF',
    'EUR',
    'GBP',
    'IRR',
    'NOK',
    'RUB',
    'TRY',
    'USD',
]
