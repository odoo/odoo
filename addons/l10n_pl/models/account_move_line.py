# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends('currency_id', 'company_id', 'move_id.delivery_date')
    def _compute_currency_rate(self):
        if self.company_id.country_code == "PL":
            for line in self:
                if line.currency_id:
                    line.currency_rate = self.env['res.currency']._get_conversion_rate(
                        from_currency=line.company_currency_id,
                        to_currency=line.currency_id,
                        company=line.company_id,
                        date=line.move_id.delivery_date or line.move_id.invoice_date or fields.Date.context_today(line),
                    )
                else:
                    line.currency_rate = 1
        else:
            super()._compute_currency_rate()
