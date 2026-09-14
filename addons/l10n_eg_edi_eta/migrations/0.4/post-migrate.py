from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["l10n_eg_edi.thumb.drive"]._move_columns_into_credentials(["access_token"])
