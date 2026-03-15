# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.const import SENSITIVE_KEYS as PAYMENT_SENSITIVE_KEYS

SENSITIVE_KEYS = {'secret'}
PAYMENT_SENSITIVE_KEYS.update(SENSITIVE_KEYS)

PAYMENT_SUCCESS_RETURN_ROUTE = '/payment/toss-payments/success'
PAYMENT_FAILURE_RETURN_ROUTE = '/payment/toss-payments/failure'
WEBHOOK_ROUTE = '/payment/toss-payments/webhook'

# The currency supported by Toss Payments, in ISO 4217 format.
SUPPORTED_CURRENCY = 'KRW'

# The codes of the payment methods to activate when Toss Payments is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'bank_transfer',
    'card',
    'mobile',
}

# Mapping of payment method codes to Toss Payments codes.
PAYMENT_METHODS_MAPPING = {'card': 'CARD', 'bank_transfer': 'TRANSFER', 'mobile': 'MOBILE_PHONE'}

# Mapping of transaction states to Toss Payments' payment statuses.
PAYMENT_STATUS_MAPPING = {'done': 'DONE', 'canceled': 'EXPIRED', 'error': 'ABORTED'}

# Event statuses to skip secret key verification
VERIFICATION_EXEMPT_STATUSES = {'EXPIRED', 'ABORTED'}

# Events that are handled by the webhook.
HANDLED_WEBHOOK_EVENTS = {'PAYMENT_STATUS_CHANGED'}
