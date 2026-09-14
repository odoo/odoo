from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["payment.provider"]._move_columns_into_credentials(
        ["asiapay_secure_hash_secret"]
    )
