# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Route for ABA PayWay webhook.
PAYMENT_WEBHOOK_ROUTE = "/payment/payway/webhook"

# Mapping of payment method codes to ABA PayWay codes.
PAYMENT_METHODS_MAPPING = {"card": "cards", "aba_khqr": "abapay_khqr", "wechat_pay": "wechat"}

# The codes of the payment methods to activate when ABA PayWay is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    "card",
    "aba_khqr",
    "wechat_pay",
    "alipay",
    # Brand payment methods.
    "visa",
    "mastercard",
    "unionpay",
    "jcb",
}

# The keys to include in the secure hash for purchase payment requests, in the order they should be concatenated.
PURCHASE_PAYMENT_SECURE_HASH_KEYS = [
    "req_time",
    "merchant_id",
    "tran_id",
    "amount",
    "items",
    "firstname",
    "lastname",
    "email",
    "phone",
    "type",
    "payment_option",
    "return_url",
    "continue_success_url",
    "currency",
    "custom_fields",
    "lifetime",
    "skip_success_page",
]

# The keys to include in the secure hash for "check transaction" API requests, in the order they should be concatenated.
SUPPORTED_CURRENCIES = {"KHR", "USD"}

# The number of decimals to use for each supported currency, used for formatting and validating amounts.
CURRENCY_DECIMALS = {"KHR": 0, "USD": 2}

# Mapping of transaction states to PayWay success codes.
SUCCESS_CODE_MAPPING = {"done": (0,), "pending": (2,)}
