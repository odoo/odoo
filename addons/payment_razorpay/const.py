# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The currencies supported by Razorpay, in ISO 4217 format. Last updated on May 26, 2021.
# See https://razorpay.com/docs/payments/payments/international-payments/#supported-currencies.
# Last seen online: 16 November 2022.
SUPPORTED_CURRENCIES = [
    'AED',
    'ALL',
    'AMD',
    'ARS',
    'AUD',
    'AWG',
    'BBD',
    'BDT',
    'BMD',
    'BND',
    'BOB',
    'BSD',
    'BWP',
    'BZD',
    'CAD',
    'CHF',
    'CNY',
    'COP',
    'CRC',
    'CUP',
    'CZK',
    'DKK',
    'DOP',
    'DZD',
    'EGP',
    'ETB',
    'EUR',
    'FJD',
    'GBP',
    'GHS',
    'GIP',
    'GMD',
    'GTQ',
    'GYD',
    'HKD',
    'HNL',
    'HRK',
    'HTG',
    'HUF',
    'IDR',
    'ILS',
    'INR',
    'JMD',
    'KES',
    'KGS',
    'KHR',
    'KYD',
    'KZT',
    'LAK',
    'LKR',
    'LRD',
    'LSL',
    'MAD',
    'MDL',
    'MKD',
    'MMK',
    'MNT',
    'MOP',
    'MUR',
    'MVR',
    'MWK',
    'MXN',
    'MYR',
    'NAD',
    'NGN',
    'NIO',
    'NOK',
    'NPR',
    'NZD',
    'PEN',
    'PGK',
    'PHP',
    'PKR',
    'QAR',
    'RUB',
    'SAR',
    'SCR',
    'SEK',
    'SGD',
    'SLL',
    'SOS',
    'SSP',
    'SVC',
    'SZL',
    'THB',
    'TTD',
    'TZS',
    'USD',
    'UYU',
    'UZS',
    'YER',
    'ZAR',
]

# The codes of the payment methods to activate when Razorpay is activated.
DEFAULT_PAYMENT_METHODS_CODES = [
    # Primary payment methods.
    'card',
    'netbanking',
    'upi',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
]

# The maximum amount in INR that can be paid through an eMandate.
MANDATE_MAX_AMOUNT = {
    'card': 500000,
    'upi': 100000,
}

# Mapping of transaction states to Razorpay's payment statuses.
# See https://razorpay.com/docs/payments/payments#payment-life-cycle.
PAYMENT_STATUS_MAPPING = {
    'pending': ('created', 'pending'),
    'authorized': ('authorized',),
    'done': ('captured', 'refunded', 'processed'),  # refunded is included to discard refunded txs.
    'error': ('failed',),
}

# Events that are handled by the webhook.
HANDLED_WEBHOOK_EVENTS = [
    'payment.authorized',
    'payment.captured',
    'payment.failed',
    'refund.failed',
    'refund.processed',
]
