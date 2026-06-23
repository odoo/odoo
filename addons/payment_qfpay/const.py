# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import frozendict

# Routes for QFPay redirection and webhook.
PAYMENT_RETURN_ROUTE = "/payment/qfpay/return"
WEBHOOK_ROUTE = "/payment/qfpay/webhook"

# The currencies supported by QFPay, in ISO 4217 format.
SUPPORTED_CURRENCIES = (
    "HKD",
    "CNY",
    "USD",
    "AED",
    "EUR",
    "IDR",
    "JPY",
    "MMK",
    "MYR",
    "SGD",
    "THB",
    "CAD",
    "AUD",
)

# The codes of the default primary payment methods to activate
DEFAULT_PAYMENT_METHOD_CODES = {
    "alipay",
    "alipay_hk",
    "wechat_pay",
    "unionpay",
    "fps",
    "payme",
    "card",
}

# Mapping of payment method codes to QFPay codes (for creating the payment intent).
PAYMENT_METHODS_MAPPING = frozendict({
    "alipay": "801101",
    "alipay_hk": "801514",
    "card": "802801",
    "fps": "802001",
    "payme": "805814",
    "unionpay": "800714",
    "wechat_pay": "800212",
})

# Mapping of payment method codes to UI picker type codes for the QFPay Element SDK.
PAYMENT_PICKER_TYPES = frozendict({
    "alipay": "Alipay",
    "alipay_hk": "AlipayHK",
    "card": "VisaMasterCardPayment",
    "fps": "FPS",
    "payme": "PayMe",
    "unionpay": "UnionPay",
    "wechat_pay": "WeChat",
})

# Mapping of transaction states to QFPay's payment statuses.
PAYMENT_STATUS_MAPPING = frozendict({
    "done": ("0000",),
    "pending": ("1143", "1145", "1298"),
    "cancel": ("1142", "1181", "1263", "1264"),
})
