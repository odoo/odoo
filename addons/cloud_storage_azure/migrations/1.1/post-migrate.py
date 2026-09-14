from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["credential.credential"]._move_parameters_into_system_secrets(
        ["cloud_storage_azure_client_secret"]
    )
