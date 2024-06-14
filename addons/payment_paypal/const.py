# Part of Odoo. See LICENSE file for full copyright and licensing details.

# ISO 4217 codes of currencies supported by PayPal
# See https://developer.paypal.com/docs/reports/reference/paypal-supported-currencies/.
# Last seen on: 22 September 2022.
SUPPORTED_CURRENCIES = (
    'AUD',
    'BRL',
    'CAD',
    'CNY',
    'CZK',
    'DKK',
    'EUR',
    'HKD',
    'HUF',
    'ILS',
    'JPY',
    'MYR',
    'MXN',
    'TWD',
    'NZD',
    'NOK',
    'PHP',
    'PLN',
    'GBP',
    'RUB',
    'SGD',
    'SEK',
    'CHF',
    'THB',
    'USD',
)

# The codes of the payment methods to activate when Paypal is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'paypal',
}

# Mapping of new rest api statusses for capture and authorize
# https://developer.paypal.com/docs/api/orders/v2/#definition-capture_status
# https://developer.paypal.com/docs/api/orders/v2/#definition-authorization_status
# TODO Do i do 2 separate mappings for each method?
PAYMENT_STATUS_MAPPING = {
    'pending': (
        'PENDING',
        'CREATED',
    ),
    'done': (
        'COMPLETED',
        'PARTIALLY_REFUNDED',
        'REFUNDED',
        'CAPTURED',
        'PARTIALLY_CAPTURED',
    ),
    'cancel': (
        'DECLINED',
        'DENIED',
        'VOIDED',
    ),
    'error': ('FAILED',),
}
