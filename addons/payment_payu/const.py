# Part of Odoo. See LICENSE file for full copyright and licensing details.

PROD_BASE_URL = 'info.payu.in'
TEST_BASE_URL = 'test.payu.in'
RETURN_URL = '/payment/payu/return'
WEBHOOK_URL = '/payment/payu/webhook'

# The currencies supported by PayU, in ISO 4217 format.
SUPPORTED_CURRENCIES = ['INR']

# Mapping of transaction states to Payu payment statuses.
# See References
# For payment: https://docs.payu.in/docs/webhook-events-and-sample-payloads#payments-event-payload-parameter-description
# For refund: https://docs.payu.in/docs/webhook-events-and-sample-payloads#refunds-payload-parameters
PAYMENT_STATUS_MAPPING = {
    'pending': ['pending'],
    'done': ['success'],
    'error': ['failure'],
}

# The codes of the payment methods to activate when PayU is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'netbanking',
    'card',
    'upi',
    'wallets_india',
    'emi_india',
    'paylater_india',
    # Brand payment methods.
    'visa',
    'mastercard',
    'maestro',
    'rupay',
    'amex',
    'diners',
}

# The hash sequences used to generate and validate PayU request/response signatures.
# See References
# For payment: https://docs.payu.in/docs/hashing-request-and-response?#hashing-scenarios-for-payment-request
# For webhook: https://docs.payu.in/docs/hashing-request-and-response?#hash-validation-logic-for-payment-response-reverse-hashing
# For refund: https://docs.payu.in/reference/refund_transaction_api?#body-params
PAYU_HASH_SEQUENCE = {
    'PAYMENT': 'key|txnid|amount|productinfo|firstname|email|udf1|udf2|udf3|udf4|udf5|udf6|udf7|udf8|udf9|udf10|salt',
    'PAYMENT_WEBHOOK': 'salt|status|udf10|udf9|udf8|udf7|udf6|udf5|udf4|udf3|udf2|udf1|email|firstname|productinfo|amount|txnid|key',
    'REFUND': 'key|command|var1|salt',
}

# Mapping of payment methods to Payu payment modes.
# See https://docs.payu.in/docs/checkout-plus-integration#supported-payment-modes
PAYMENT_METHODS_MAPPING = {
    'netbanking': ['netbanking'],
    'card': ['creditcard', 'debitcard'],
    'upi': ['upi'],
    'wallets_india': ['cashcard'],
    'emi_india': ['emi'],
    'paylater_india': ['bnpl'],
}
