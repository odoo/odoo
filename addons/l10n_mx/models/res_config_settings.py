# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_mx_account_income_return_discount_id = fields.Many2one(
        comodel_name="account.account",
        string='Income Returns and Discounts Account',
        readonly=False,
        related='company_id.l10n_mx_income_return_discount_account_id',
        domain="[('account_type', '=', 'income')]",
    )
