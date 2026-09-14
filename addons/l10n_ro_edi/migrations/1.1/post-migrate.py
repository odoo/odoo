from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.company"]._move_columns_into_credentials(
        [
            "l10n_ro_edi_client_secret",
            "l10n_ro_edi_access_token",
            "l10n_ro_edi_refresh_token",
        ]
    )
