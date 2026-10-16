# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The code of the QR method, as stored on the invoices and the point of sale payment methods.
QR_METHOD = 'ph_qrph_maya'

# The Maya API, as in the Pay with Maya QR documentation.
PRODUCTION_URL = 'https://pg.paymaya.com'
SANDBOX_URL = 'https://pg-sandbox.paymaya.com'
CREATE_PAYMENT_ENDPOINT = 'payments/v1/qr/payments'
PAYMENT_STATUS_ENDPOINT = 'payments/v1/payments/{payment_id}/status'
REQUEST_TIMEOUT = 30

# Maya statuses meaning the money reached the merchant. They are reversible by a refund or a void,
# which is a decision taken in Odoo afterwards and not something the QRPH code can still change.
# An authorization on the other hand only holds funds, so it is not a payment to register yet.
PAID_STATUSES = {'PAYMENT_SUCCESS', 'CAPTURED'}
# Maya statuses a payment never leaves: the code behind it is dead and a new one must be generated.
FINAL_STATUSES = {
    'AUTH_FAILED',
    'CAPTURE_HOLD_EXPIRED',
    'PAYMENT_CANCELLED',
    'PAYMENT_EXPIRED',
    'PAYMENT_FAILED',
    'REFUNDED',
    'VOIDED',
}

# Maya expires a dynamic QRPH code one hour after minting it, and only ever takes one payment on
# it. We hand out the same code for well less than that, so that a payment screen left open is
# refreshed with a code that is still good rather than one Maya is about to refuse.
REUSE_SECONDS = 900

# A code nobody paid within a day will not be paid anymore; the cron has long stopped looking at it.
RETENTION_DAYS = 1
