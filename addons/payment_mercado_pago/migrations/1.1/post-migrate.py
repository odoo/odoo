from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["payment.provider"]._move_columns_into_credentials(
        ["mercado_pago_access_token", "mercado_pago_refresh_token"]
    )
