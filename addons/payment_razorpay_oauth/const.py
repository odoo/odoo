# TODO: change IAP url to the correct one (right now it's a test url)
OAUTH_URL = "https://razorpay.api.odoo.com"
OAUTH_TEST_URL = "https://razorpay.test.odoo.com"


# Events that are handled by the webhook.
HANDLED_WEBHOOK_EVENTS = [
    'payment.authorized',
    'payment.captured',
    'payment.failed',
    'refund.failed',
    'refund.processed',
    'account.app.authorization_revoked',
]
