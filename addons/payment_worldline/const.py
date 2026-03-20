# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The codes of the payment methods to activate when Worldline is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'card',
    # Brand payment methods.
    'amex',
    'discover',
    'mastercard',
    'visa',
}

# Mapping of payment method codes to Worldline codes.
# See https://docs.direct.worldline-solutions.com/en/payment-methods-and-features/index.
PAYMENT_METHODS_MAPPING = {
    'alipay_plus': 5405,
    'amex': 2,
    'bancontact': 3012,
    'bizum': 5001,
    'cartes_bancaires': 130,
    'cofidis': 3012,
    'diners': 132,
    'discover': 128,
    'eps': 5406,
    'floa_bank': 5139,
    'ideal': 809,
    'jcb': 125,
    'klarna': 3301,
    'maestro': 117,
    'mastercard': 3,
    'mbway': 5908,
    'multibanco': 5500,
    'p24': 3124,
    'paypal': 840,
    'post_finance_pay': 3203,
    'twint': 5407,
    'upi': 56,
    'visa': 1,
    'wechat_pay': 5404,
}

# The payment methods that involve a redirection to 3rd parties by Worldline.
REDIRECT_PAYMENT_METHODS = {
    'alipay_plus',
    'bizum',
    'eps',
    'floa_bank',
    'ideal',
    'klarna',
    'mbway',
    'multibanco',
    'p24',
    'paypal',
    'post_finance_pay',
    'twint',
    'wechat_pay',
}

# Mapping of transaction states to Worldline's payment statuses.
# See https://docs.direct.worldline-solutions.com/en/integration/api-developer-guide/statuses.
PAYMENT_STATUS_MAPPING = {
    'pending': (
        'CREATED', 'REDIRECTED', 'AUTHORIZATION_REQUESTED', 'PENDING_CAPTURE', 'CAPTURE_REQUESTED'
    ),
    'done': ('CAPTURED',),
    'cancel': ('CANCELLED',),
    'declined': ('REJECTED', 'REJECTED_CAPTURE'),
}

# Mapping of response codes indicating Worldline handled the request
# See https://apireference.connect.worldline-solutions.com/s2sapi/v1/en_US/json/response-codes.html.
VALID_RESPONSE_CODES = {
    200: 'Successful',
    201: 'Created',
    402: 'Payment Rejected',
}
