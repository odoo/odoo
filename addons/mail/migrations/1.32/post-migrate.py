from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["credential.credential"]._move_parameters_into_system_secrets(
        [
            "mail.twilio_account_token",
            "mail.sfu_server_key",
            "discuss.klipy_api_key",
            "mail.google_translate_api_key",
        ]
    )
    env["fetchmail.server"]._move_columns_into_credentials(["password"])
    env["mail.ice.server"]._move_columns_into_credentials(["credential"])
