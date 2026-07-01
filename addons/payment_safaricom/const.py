# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.const import SENSITIVE_KEYS as PAYMENT_SENSITIVE_KEYS

PAYMENT_URL = "/payment/safaricom/payment"
CANCEL_URL = "/payment/safaricom/cancel"
WEBHOOK_URL = "/payment/safaricom/webhook"

SENSITIVE_KEYS = {
    "safaricom_consumer_secret",
    "safaricom_consumer_key",
    "safaricom_passkey",
    "safaricom_access_token",
    "Password",  # In the STK Push payload; base64 of shortcode+passkey+timestamp, reversible
    "CallBackURL",  # In the STK Push payload; carries the signed token authenticating the webhook
}
PAYMENT_SENSITIVE_KEYS.update(SENSITIVE_KEYS)

# The currency supported by Safaricom, in ISO 4217 format.
SUPPORTED_CURRENCY = "KES"

# The codes of the payment methods to activate when Safaricom is activated.
DEFAULT_PAYMENT_METHOD_CODES = {"mpesa"}

# Mapping of M-PESA ResultCodes to Odoo payment statuses; unlisted codes are treated as errors
PAYMENT_STATUS_MAPPING = {
    "done": ["0"],
    "cancel": ["1032"],  # 1032: cancelled by the user
    "unreachable": ["1037"],  # 1037: DS timeout user cannot be reached
}
