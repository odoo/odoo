from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["account_edi_proxy_client.user"]._move_columns_into_credentials(
        ["refresh_token"]
    )
