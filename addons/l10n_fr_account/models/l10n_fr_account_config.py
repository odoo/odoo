from odoo import fields, models


class L10nFrAccountConfig(models.Model):
    _name = "l10n_fr_account.config"
    _description = "A company's l10n fr account configuration"
    _inherit = ["mixin.company.config"]

    l10n_fr_rounding_difference_loss_account_id = fields.Many2one(
        comodel_name="account.account",
        check_company=True,
    )
    l10n_fr_rounding_difference_profit_account_id = fields.Many2one(
        comodel_name="account.account",
        check_company=True,
    )
