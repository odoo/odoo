# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _compute_currency_rate(self):
        super()._compute_currency_rate()
        for line in self:
            if line.move_id.country_code == 'CZ':
                line.currency_rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=line.company_currency_id,
                    to_currency=line.currency_id,
                    company=line.company_id,
                    date=line._get_rate_date(),
                )

    def _get_rate_date(self):
        # EXTENDS 'account'
        self.ensure_one()
        if self.move_id.country_code == 'CZ':
            return self.move_id.delivery_date or self.move_id.date or fields.Date.context_today(self)
        return super()._get_rate_date()
