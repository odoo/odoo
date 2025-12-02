# Part of Odoo. See LICENSE file for full copyright and licensing details.

# ISO 4217 codes of currencies supported by PayPal
# See https://developer.paypal.com/docs/reports/reference/paypal-supported-currencies/.
# Last seen on: 04 November 2025.

# CNY removed as it requires in-country PayPal accounts but China mostly uses WeChat and Alipay.
SUPPORTED_CURRENCIES = (
    'AUD',
    'BRL',
    'CAD',
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

# Mapping of transaction states to PayPal payment statuses.
# See https://developer.paypal.com/docs/api/orders/v2/#definition-capture_status.
# See https://developer.paypal.com/api/rest/webhooks/event-names/#orders.
PAYMENT_STATUS_MAPPING = {
    'pending': (
        'PENDING',
        'CREATED',
        'APPROVED',  # The buyer approved a checkout order.
    ),
    'done': (
        'COMPLETED',
        'CAPTURED',
    ),
    'cancel': (
        'DECLINED',
        'DENIED',
        'VOIDED',
    ),
    'error': ('FAILED',),
}

# Events which are handled by the webhook.
# See https://developer.paypal.com/api/rest/webhooks/event-names/
HANDLED_WEBHOOK_EVENTS = [
    'CHECKOUT.ORDER.COMPLETED',
    'CHECKOUT.ORDER.APPROVED',
    'CHECKOUT.PAYMENT-APPROVAL.REVERSED',
]
