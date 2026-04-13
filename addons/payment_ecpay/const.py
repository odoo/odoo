# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import frozendict

# Routes for ECPay redirection and webhook.
PAYMENT_RETURN_ROUTE = "/payment/ecpay/return"
WEBHOOK_ROUTE = "/payment/ecpay/webhook"

# The currency supported by ECPay, in ISO 4217 format.
SUPPORTED_CURRENCY = "TWD"

# The codes of the default primary payment methods to activate
DEFAULT_PAYMENT_METHOD_CODES = {"card"}

# Mapping of payment method codes to ECPay codes.
PAYMENT_METHODS_MAPPING = frozendict({
    "card": ("Credit",),
    "wechat_pay": ("WeiXin",),
    "cvs": ("CVS", "BARCODE"),
    "bank_transfer": ("ATM", "WebATM"),
    "mobile_wallet": ("DigitalPayment",),
    "twqr": ("TWQR",),
    "none": (
        "BNPL",
        "ApplePay",
    ),  # Unused but required to compute the ignored methods to send to ECPay
})

# Mapping of Odoo payment method codes to the values returned by ECPay notifications.
# This map intentionally contains only methods where the returned value lets us pick a brand PM
# in Odoo (e.g., convenience stores and specific wallets). Other methods are still supported via
# PAYMENT_METHODS_MAPPING, but their response values are either generic (e.g., Credit_CreditCard)
# or not mapped to brand PMs in Odoo (e.g., ATM/WebATM bank variants).
PAYMENT_METHODS_RESPONSE_MAPPING = frozendict({
    "ok_mart": "CVS_OK",
    "hi_life": "CVS_HILIFE",
    "family_mart": "CVS_FAMILY",
    "7eleven": "CVS_IBON",
    "jkopay": "DigitalPayment_Jkopay",
    "ipass_money": "DigitalPayment_IPASS",
})

# Mapping IETF language tags (e.g.: 'fr-BE') to ECPay language codes.
# If a language tag is not listed, the country code prefix can serve as fallback.
LANGUAGE_CODES_MAPPING = frozendict({"en": "ENG", "ja_JP": "JPN", "ko": "KOR", "zh": "CHI"})

# Mapping of transaction states to ECPay success codes.
SUCCESS_CODE_MAPPING = frozendict({"done": ("1", "2", "10100073")})
