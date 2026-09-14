from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["payment.provider"]._move_columns_into_credentials(
        [
            "razorpay_key_secret",
            "razorpay_webhook_secret",
            "razorpay_refresh_token",
            "razorpay_public_token",
            "razorpay_access_token",
        ]
    )
