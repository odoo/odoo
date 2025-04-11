SUPPORTED_CURRENCIES = [
    'XOF',
    'XAF',
    'USD',
    'EUR',
]

PAYMENT_STATUS_MAPPING = {
    'pending': ['PENDING'],
    'done': ['ACCEPTED'],
    'cancel': ['REFUSED'],
    'error': ['FAILED'],
}

DEFAULT_PAYMENT_METHOD_CODES = {
    'card',
    'mobile_money',
    'bank_transfer',
}
