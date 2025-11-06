# Part of Odoo. See LICENSE file for full copyright and licensing details.

PAYMENT_REQUEST_ROUTE = "/payment/authorize/payment"
WEBHOOK_ROUTE = "/payment/authorize/webhook"

# The codes of the payment methods to activate when Authorize is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    "ach_direct_debit",
    "card",
    # Brand payment methods.
    "visa",
    "mastercard",
    "amex",
    "discover",
}

# Mapping of payment method codes to Authorize codes.
PAYMENT_METHODS_MAPPING = {
    "ach_direct_debit": "echeck",
    "amex": "americanexpress",
    "card": "creditcard",
    "diners": "dinersclub",
}

# Mapping of payment status on Authorize side to transaction statuses.
# See https://developer.authorize.net/api/reference/index.html#transaction-reporting-get-transaction-details.
TRANSACTION_STATUS_MAPPING = {
    "authorized": ["authorizedPendingCapture", "capturedPendingSettlement"],
    "captured": ["settledSuccessfully"],
    "voided": ["voided"],
    "refunded": ["refundPendingSettlement", "refundSettledSuccessfully"],
}

# Mapping of webhook event types to their corresponding transaction type
WEBHOOK_EVENT_TYPE_MAPPING = {
    "net.authorize.payment.authcapture.created": "auth_capture",
    "net.authorize.payment.authorization.created": "auth_only",
    "net.authorize.payment.capture.created": "auth_capture",
    "net.authorize.payment.priorAuthCapture.created": "prior_auth_capture",
    "net.authorize.payment.refund.created": "refund",
    "net.authorize.payment.void.created": "void",
}

# Supported webhook event types
HANDLED_WEBHOOK_EVENTS = set(WEBHOOK_EVENT_TYPE_MAPPING)
