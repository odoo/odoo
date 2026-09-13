from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_nl_rounding_difference_loss_account_id = fields.Many2one(
        comodel_name="account.account",
        check_company=True,
    )
    l10n_nl_rounding_difference_profit_account_id = fields.Many2one(
        comodel_name="account.account",
        check_company=True,
    )
