# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.const import SENSITIVE_KEYS as PAYMENT_SENSITIVE_KEYS

SENSITIVE_KEYS = {"store_passwd"}
PAYMENT_SENSITIVE_KEYS.update(SENSITIVE_KEYS)

PAYMENT_RETURN_ROUTE = "/payment/sslcommerz/return"
IPN_ROUTE = "/payment/sslcommerz/ipn"

# The currency supported by SSLCOMMERZ, in ISO 4217 format.
SUPPORTED_CURRENCY = "BDT"

# The codes of the payment methods to activate when SSLCOMMERZ is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    "card",
    "bkash",
    "nagad",
    # Brand payment methods.
    "amex",
    "mastercard",
    "visa",
}


# Mapping of payment method codes to SSLCOMMERZ codes.
PAYMENT_METHODS_MAPPING = {
    "card": "visacard,mastercard,amexcard",
    "bkash": "bkash",
    "mastercard": "master",
    "nagad": "nagad",
}

# Mapping of transaction states to SSLCOMMERZ payment statuses.
PAYMENT_STATUS_MAPPING = {
    "done": ("VALID", "VALIDATED"),
    "cancel": ("CANCELLED", "EXPIRED", "UNATTEMPTED"),
    "error": ("FAILED", "INVALID_TRANSACTION"),
}
