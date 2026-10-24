# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import frozendict

from odoo.addons.payment.const import SENSITIVE_KEYS as PAYMENT_SENSITIVE_KEYS

SENSITIVE_KEYS = {"store_passwd"}
PAYMENT_SENSITIVE_KEYS.update(SENSITIVE_KEYS)

PAYMENT_API_LIVE_URL = "https://uat-securepay.sslcommerz.com"
PAYMENT_API_TEST_URL = "https://sandbox.sslcommerz.com"
PAYMENT_RETURN_ROUTE = "/payment/sslcommerz/return"
IPN_ROUTE = "/payment/sslcommerz/ipn"

# The currencies supported by SSLCOMMERZ, in ISO 4217 format.
SUPPORTED_CURRENCIES = {
    "AED",
    "AUD",
    "BDT",
    "CAD",
    "EUR",
    "GBP",
    "IDR",
    "INR",
    "JPY",
    "LKR",
    "MVR",
    "MYR",
    "NGN",
    "NPR",
    "OMR",
    "QAR",
    "SAR",
    "SEK",
    "SGD",
    "THB",
    "USD",
}

# The codes of the default primary payment methods to activate
DEFAULT_PAYMENT_METHOD_CODES = {"card", "mobilebanking", "netbanking"}

# Mapping of payment method codes to SSLCOMMERZ codes.
PAYMENT_METHODS_MAPPING = frozendict({
    "card": "visacard,mastercard,amexcard",
    "netbanking": "internetbank",
})

# Mapping of payment method codes to SSLCOMMERZ response codes
PAYMENT_METHODS_RESPONSE_MAPPING = frozendict({"netbanking": "ib"})

# Mapping of transaction states to SSLCOMMERZ payment statuses.
PAYMENT_STATUS_MAPPING = frozendict({
    "done": ("VALID", "VALIDATED"),
    "cancel": ("CANCELLED", "EXPIRED", "UNATTEMPTED"),
    "error": ("FAILED", "INVALID_TRANSACTION"),
})
