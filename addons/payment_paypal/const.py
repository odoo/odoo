# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

# Mapping of transaction states to PayPal payment statuses.
# See https://developer.paypal.com/docs/api/orders/v2/#definition-capture_status.
# See https://developer.paypal.com/api/rest/webhooks/event-names/#orders.
PAYMENT_STATUS_MAPPING = {
    "pending": (
        "PENDING",
        "CREATED",
        "APPROVED",  # The buyer approved a checkout order.
    ),
    "done": ("COMPLETED", "CAPTURED"),
    "cancel": ("DECLINED", "DENIED", "VOIDED"),
    "error": ("FAILED",),
}

# Events which are handled by the webhook.
# See https://developer.paypal.com/api/rest/webhooks/event-names/
HANDLED_WEBHOOK_EVENTS = [
    "CHECKOUT.ORDER.COMPLETED",
    "CHECKOUT.ORDER.APPROVED",
    "CHECKOUT.PAYMENT-APPROVAL.REVERSED",
    "CUSTOMER.MERCHANT-INTEGRATION.SELLER-EMAIL-CONFIRMED",
    "MERCHANT.ONBOARDING.COMPLETED",
]

# Odoo's public credentials as a PayPal Partner.
# Needed to offer merchant onboarding via Odoo.
PARTNER_CREDENTIALS = {
    "partner_id": "QHZVTLZNWGSEW",
    "partner_client_id": "AUssUsouGEwQ-elJwte7-ullwiRUY3eQyYlWU-1T6iI7-zVw7bveLz"
    "-jm8ue53fhVFBojRE6RNQZiecp",
}
