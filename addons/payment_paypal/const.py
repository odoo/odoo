# Part of Odoo. See LICENSE file for full copyright and licensing details.

OAUTH_INIT_ROUTE = "/payment/paypal/oauth/init"
OAUTH_FINALIZE_ROUTE = "/payment/paypal/oauth/finalize"

# ISO 4217 codes of currencies supported by PayPal
# See https://developer.paypal.com/docs/reports/reference/paypal-supported-currencies/.
# Last seen on: 04 November 2025.

# CNY removed as it requires in-country PayPal accounts but China mostly uses WeChat and Alipay.
SUPPORTED_CURRENCIES = (
    "AUD",
    "BRL",
    "CAD",
    "CZK",
    "DKK",
    "EUR",
    "HKD",
    "HUF",
    "ILS",
    "JPY",
    "MYR",
    "MXN",
    "TWD",
    "NZD",
    "NOK",
    "PHP",
    "PLN",
    "GBP",
    "RUB",
    "SGD",
    "SEK",
    "CHF",
    "THB",
    "USD",
)

# The codes of the default primary payment methods to activate
DEFAULT_PAYMENT_METHOD_CODES = {"paypal"}

# Mapping of Odoo's local payment method codes to the payment source keys returned by PayPal's
# `find-eligible-methods` endpoint. Local codes that have no entry in this mapping are not
# affected by the eligibility check, e.g., because PayPal doesn't assess their eligibility.
# See https://docs.paypal.ai/api-reference/payments_payment_v2/find-eligible-methods.
PAYMENT_METHODS_MAPPING = {
    "paypal": "paypal",
    "venmo": "venmo",
    "paypal_paylater": "paypal_pay_later",
    "ideal": "ideal",
    "card": "advanced_cards",  # The `card` payment method is processed through ACDC.
    "blik": "blik",
    "p24": "p24",
    "eps": "eps",
    "bancontact": "bancontact",
    "trustly": "trustly",
    "mybank": "mybank",
    "mulitbanco": "multibanco",
}

# Mapping of transaction states to PayPal payment statuses.
# See https://developer.paypal.com/docs/api/orders/v2/#definition-capture_status.
# See https://developer.paypal.com/api/rest/webhooks/event-names/#orders.
PAYMENT_STATUS_MAPPING = {
    "pending": (
        "PENDING",
        "CREATED",
        "APPROVED",  # The buyer approved a checkout order.
        "PAYER_ACTION_REQUIRED",
    ),
    "done": ("COMPLETED", "CAPTURED"),
    "cancel": ("CANCELED", "VOIDED"),
    "error": ("FAILED", "DECLINED"),
}

# Events which are handled by the webhook.
# See https://developer.paypal.com/api/rest/webhooks/event-names/
CHECKOUT_WEBHOOK_EVENTS = [
    "CHECKOUT.ORDER.COMPLETED",
    "CHECKOUT.ORDER.APPROVED",
    "CHECKOUT.ORDER.DECLINED",
    "CHECKOUT.PAYMENT-APPROVAL.REVERSED",
]
CAPTURE_WEBHOOK_EVENTS = ["PAYMENT.CAPTURE.COMPLETED", "PAYMENT.CAPTURE.DENIED"]
MERCHANT_WEBHOOK_EVENTS = ["CUSTOMER.MERCHANT-INTEGRATION.SELLER-EMAIL-CONFIRMED"]

# Odoo's public identifiers as a PayPal Partner for OAuth
OAUTH_ODOO_PARTNER_ID = "QHZVTLZNWGSEW"
OAUTH_ODOO_CLIENT_ID = (
    "AUssUsouGEwQ-elJwte7-ullwiRUY3eQyYlWU-1T6iI7-zVw7bveLzjm8ue53fhVFBojRE6RNQZiecp"  # noqa: E501
)
