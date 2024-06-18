from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_rate_date(self):
        # EXTENDS 'account'
        self.ensure_one()
        if self.company_id.account_fiscal_country_id.code == 'PL':
            return self.move_id.delivery_date or self.move_id.date or fields.Date.context_today(self)
        return super()._get_rate_date()
