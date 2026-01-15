from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

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
