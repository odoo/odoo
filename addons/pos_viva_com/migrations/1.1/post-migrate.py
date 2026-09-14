from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["pos.payment.method"]._move_columns_into_credentials(
        [
            "viva_com_api_key",
            "viva_com_client_secret",
            "viva_com_bearer_token",
            "viva_com_webhook_verification_key",
        ]
    )
