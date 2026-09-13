from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_mx_account_income_return_discount_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.l10n_mx_income_return_discount_account_id",
        string="Income Returns and Discounts Account",
        readonly=False,
        domain="[('account_type', '=', 'income')]",
    )
    l10n_mx_account_income_re_invoicing_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.l10n_mx_income_re_invoicing_account_id",
        string="Income Re-invoicing Account",
        readonly=False,
        domain="[('account_type', '=', 'income')]",
    )
