# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The codes of the payment methods to activate when Authorize is activated.
DEFAULT_PAYMENT_METHODS_CODES = [
    # Primary payment methods.
    'ach_direct_debit',
    'card',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
]

# Mapping of payment method codes to Authorize codes.
PAYMENT_METHODS_MAPPING = {
    'amex': 'americanexpress',
    'diners': 'dinersclub',
    'card': 'creditcard'
}

# Mapping of payment status on Authorize side to transaction statuses.
# See https://developer.authorize.net/api/reference/index.html#transaction-reporting-get-transaction-details.
TRANSACTION_STATUS_MAPPING = {
    'authorized': ['authorizedPendingCapture', 'capturedPendingSettlement'],
    'captured': ['settledSuccessfully'],
    'voided': ['voided'],
    'refunded': ['refundPendingSettlement', 'refundSettledSuccessfully'],
}
