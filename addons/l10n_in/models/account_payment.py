from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _prepare_move_counterpart_lines(self, default_values):
        self.ensure_one()
        lines = super()._prepare_move_counterpart_lines(default_values)
        if self.company_id.account_fiscal_country_id.code == 'IN' and self.withhold == 'withhold_pay':
            lines[0]['name'] += self.env._(' TDS amount: %s', self.withholding_amount)
        return lines
