# Part of Odoo. See LICENSE file for full copyright and licensing details.

# ISO 4217 codes of currencies supported by Bictorys.
# See https://www.bictorys.com for supported currencies.
SUPPORTED_CURRENCIES = (
    'XOF',  # West African CFA franc
    'XAF',  # Central African CFA franc
    'GNF',  # Guinean franc
    'USD',
    'EUR',
)

# The codes of the payment methods to activate when Bictorys is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'bictorys',
}

# Mapping of transaction states to Bictorys payment statuses.
PAYMENT_STATUS_MAPPING = {
    'pending': ('pending', 'pending auth'),
    'done': ('successful', 'succeeded', 'authorized'),
    'cancel': ('cancelled', 'canceled'),
    'error': ('failed', 'error'),
}
