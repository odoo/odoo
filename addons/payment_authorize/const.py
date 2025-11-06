# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The codes of the payment methods to activate when Authorize is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'ach_direct_debit',
    'card',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
}

# Mapping of payment method codes to Authorize codes.
PAYMENT_METHODS_MAPPING = {
    'ach_direct_debit': 'echeck',
    'amex': 'americanexpress',
    'diners': 'dinersclub',
    'card': 'creditcard',
}

# Mapping of payment status on Authorize side to transaction statuses.
# See https://developer.authorize.net/api/reference/index.html#transaction-reporting-get-transaction-details.
TRANSACTION_STATUS_MAPPING = {
    'authorized': ['authorizedPendingCapture', 'capturedPendingSettlement'],
    'captured': ['settledSuccessfully'],
    'voided': ['voided'],
    'refunded': ['refundPendingSettlement', 'refundSettledSuccessfully'],
}

# Supported webhook event types handled by the webhook controller.
HANDLED_WEBHOOK_EVENTS = [
    'net.authorize.payment.authcapture.created',
    'net.authorize.payment.authorization.created',
    'net.authorize.payment.capture.created',
    'net.authorize.payment.priorAuthCapture.created',
    'net.authorize.payment.refund.created',
    'net.authorize.payment.void.created',
]

# Mapping of webhook event types to their corresponding transaction types.
WEBHOOK_EVENT_TYPE_MAPPING = {
    'net.authorize.payment.authcapture.created': 'auth_capture',
    'net.authorize.payment.authorization.created': 'auth_only',
    'net.authorize.payment.capture.created': 'auth_capture',
    'net.authorize.payment.priorAuthCapture.created': 'prior_auth_capture',
    'net.authorize.payment.refund.created': 'refund',
    'net.authorize.payment.void.created': 'void',
}
