from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.company"]._move_columns_into_credentials(
        [
            "l10n_hu_edi_password",
            "l10n_hu_edi_signature_key",
            "l10n_hu_edi_replacement_key",
        ]
    )
