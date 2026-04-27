from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ee_rounding_difference_loss_account_id = fields.Many2one(
        comodel_name='account.account',
        related='company_id.l10n_ee_rounding_difference_loss_account_id',
        readonly=False,
        string="Loss Account for VAT Rounding",
        help="Account used for losses from rounding the lines of Estonian tax reports",
    )
    l10n_ee_rounding_difference_profit_account_id = fields.Many2one(
        comodel_name='account.account',
        related='company_id.l10n_ee_rounding_difference_profit_account_id',
        readonly=False,
        string="Profit Account for VAT Rounding",
        help="Account used for profits from rounding the lines of Estonian tax reports",
    )
