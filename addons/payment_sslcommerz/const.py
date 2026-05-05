# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import frozendict

from odoo.addons.payment.const import SENSITIVE_KEYS as PAYMENT_SENSITIVE_KEYS

SENSITIVE_KEYS = {"store_passwd"}
PAYMENT_SENSITIVE_KEYS.update(SENSITIVE_KEYS)

IPN_ROUTE = "/payment/sslcommerz/ipn"
PAYMENT_API_LIVE_URL = "https://uat-securepay.sslcommerz.com"
PAYMENT_API_TEST_URL = "https://sandbox.sslcommerz.com"
PAYMENT_RETURN_ROUTE = "/payment/sslcommerz/return"

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
DEFAULT_PAYMENT_METHOD_CODES = {"bkash", "card", "netbanking"}

# Mapping of payment method codes to SSLCOMMERZ codes.
PAYMENT_METHODS_MAPPING = frozendict({
    "card": "visacard,mastercard,amexcard",
    "netbanking": "internetbank",
})

# The codes of the payment methods that map to a single SSLCOMMERZ channel. For these, the
# customer can be redirected directly to that channel, skipping SSLCOMMERZ's own selection page.
DIRECT_OPEN_PAYMENT_METHOD_CODES = {
    "alarafahbank",
    "bkash",
    "cashbaba",
    "cellfine",
    "dbblmobilebanking",
    "ibbl_m",
    "meghnapay",
    "mobilemoney",
    "mycash",
    "nagad",
    "okaywallet",
    "pathaopay",
    "pocket",
    "rainbow",
    "stpay",
    "upay",
}

# Mapping of payment method codes to SSLCOMMERZ response codes
PAYMENT_METHODS_RESPONSE_MAPPING = frozendict({
    "dbblmobilebanking": "dbblmobileb",
    "ibbl_m": "ibbl",
    "mobilemoney": "tap",
    "netbanking": "ib",
})

# Mapping of transaction states to SSLCOMMERZ payment statuses.
PAYMENT_STATUS_MAPPING = frozendict({
    "done": ("VALID", "VALIDATED"),
    "cancel": ("CANCELLED", "EXPIRED", "UNATTEMPTED"),
    "error": ("FAILED", "INVALID_TRANSACTION"),
})
