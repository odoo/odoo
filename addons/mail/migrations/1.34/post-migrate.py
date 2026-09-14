from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["credential.credential"]._move_parameters_into_system_secrets(
        ["mail.web_push_vapid_private_key"]
    )
