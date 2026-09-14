from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["payment.provider"]._move_columns_into_credentials(
        ["xendit_secret_key", "xendit_webhook_token"]
    )
