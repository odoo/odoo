from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('move_id.country_code', 'move_id.move_type', 'display_type')
    def _compute_account_id(self):
        # EXTENDS 'account'
        super()._compute_account_id()
        for line in self:
            if (
                line.move_id.country_code == 'MX'
                and line.move_id.move_type == 'out_refund'
                and line.display_type == 'product'
                and line.company_id.l10n_mx_income_return_discount_account_id
            ):
                line.account_id = line.company_id.l10n_mx_income_return_discount_account_id
