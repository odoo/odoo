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

# Response reason codes and AVS/CVV result codes of declines caused by a mismatch with the card
# issuer's records. See https://developer.authorize.net/api/reference/features/errorandresponsecodes.html.
AVS_MISMATCH_REASON_CODES = {'27', '127'}  # The reason text already describes the mismatch.
CVV_MISMATCH_REASON_CODES = {'44', '65'}
AVS_AND_CVV_MISMATCH_REASON_CODES = {'45'}
AVS_MISMATCH_RESULT_CODES = {'A', 'N', 'W', 'Z'}
CVV_MISMATCH_RESULT_CODES = {'N'}
