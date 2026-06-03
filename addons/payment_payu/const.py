# Part of Odoo. See LICENSE file for full copyright and licensing details.

from types import MappingProxyType

OAUTH_URL = "https://payu.api.odoo.com/api/payu/1"
OAUTH_RETURN_ROUTE = "/payment/payu/oauth/return"
PARTNER_API_URL = "https://partner.payu.in"
PAYMENT_API_LIVE_URL = "https://secure.payu.in"
PAYMENT_API_TEST_URL = "https://test.payu.in"
PAYMENT_RETURN_ROUTE = "/payment/payu/return"
WEBHOOK_ROUTE = "/payment/payu/webhook"

# The currencies supported by PayU, in ISO 4217 format.
# PayU accounts are configured for a single settlement/display currency.
# Supporting additional currencies would require separate PayU account configurations, so only INR
# is supported at this time.
SUPPORTED_CURRENCIES = ["INR"]

# The codes of the default primary payment methods to activate
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods
    "card",
    "netbanking",
    "upi",
    # Brand payment methods
    "amex",
    "mastercard",
    "rupay",
    "visa",
}

# Mapping of payment method codes to PayU codes
PAYMENT_METHODS_MAPPING = MappingProxyType({
    "card": "creditcard | debitcard",
    "emi_india": "emi",
    "netbanking": "netbanking",
    "paylater_india": "bnpl",
    "upi": "upi",
    "wallets_india": "cashcard",
})

# Mapping of payment method codes to PayU response codes
PAYMENT_METHODS_RESPONSE_MAPPING = MappingProxyType({
    "emi_india": "EMI",
    "netbanking": "NB",
    "paylater_india": "BNPL",
    "upi": "UPI",
    "wallets_india": "CASH",
})

# The keys of the values to use in the calculation of the signature
SIGNATURE_KEYS = MappingProxyType({
    "outgoing": (
        "key",
        "txnid",
        "amount",
        "productinfo",
        "firstname",
        "email",
        "udf1",
        "udf2",
        "udf3",
        "udf4",
        "udf5",
        "udf6",
        "udf7",
        "udf8",
        "udf9",
        "udf10",
        "salt",
    ),
    "incoming": (
        "salt",
        "status",
        "udf10",
        "udf9",
        "udf8",
        "udf7",
        "udf6",
        "udf5",
        "udf4",
        "udf3",
        "udf2",
        "udf1",
        "email",
        "firstname",
        "productinfo",
        "amount",
        "txnid",
        "key",
    ),
})

# Mapping of transaction states to PayU payment statuses
PAYMENT_STATUS_MAPPING = MappingProxyType({
    "pending": ("pending",),
    "done": ("success",),
    "error": ("failure",),
})
