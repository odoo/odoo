# Part of Odoo. See LICENSE file for full copyright and licensing details.

PAYMENT_RETURN_ROUTE = "/payment/iyzico/return"
WEBHOOK_ROUTE = "/payment/iyzico/webhook"

# The currencies supported by Iyzico, in ISO 4217 format.
SUPPORTED_CURRENCIES = ["CHF", "EUR", "GBP", "IRR", "NOK", "RUB", "TRY", "USD"]

# The codes of the default primary payment methods to activate
DEFAULT_PAYMENT_METHOD_CODES = {"card"}

# Mapping of payment method codes to Iyzico codes.
PAYMENT_METHODS_MAPPING = {"amex": "american_express", "mastercard": "master_card"}

# Mapping of transaction states to Iyzico payment statuses.
# See https://docs.iyzico.com/en/advanced/webhook#hpp-format.
PAYMENT_STATUS_MAPPING = {
    "pending": (
        "INIT_THREEDS",
        "CALLBACK_THREEDS",
        "INIT_BANK_TRANSFER",
        "INIT_CREDIT",
        "PENDING_CREDIT",
    ),
    "done": ("SUCCESS",),
    "error": ("FAILURE",),
}
