from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["pos.payment.method"]._move_columns_into_credentials(
        ["pine_labs_security_token"]
    )
