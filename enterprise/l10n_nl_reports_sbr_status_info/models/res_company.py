from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_nl_reports_sbr_password = fields.Char('Certificate or private key password', groups="account.group_account_user")  # Deprecated
