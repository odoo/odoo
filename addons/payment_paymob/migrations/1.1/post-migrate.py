from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["payment.provider"]._move_columns_into_credentials(
        ["paymob_secret_key", "paymob_hmac_key", "paymob_api_key"]
    )
