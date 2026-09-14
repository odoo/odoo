from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.company"]._move_columns_into_credentials(["l10n_hr_mer_password"])
