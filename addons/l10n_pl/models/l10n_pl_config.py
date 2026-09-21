from odoo import fields, models


class L10nPlConfig(models.Model):
    _name = "l10n_pl.config"
    _description = "A company's l10n pl configuration"
    _inherit = ["mixin.company.config"]

    l10n_pl_reports_tax_office_id = fields.Many2one(
        comodel_name="l10n_pl.l10n_pl_tax_office",
        string="Tax Office",
        groups="account.group_account_user",
    )
