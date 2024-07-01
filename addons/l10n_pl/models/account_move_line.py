# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends('move_id.delivery_date')
    def _compute_currency_rate(self):
        super()._compute_currency_rate()

    def _get_rate_date(self):
        # EXTENDS 'account'
        self.ensure_one()
        if self.move_id.country_code == 'PL':
            return self.move_id.delivery_date or self.move_id.date or fields.Date.context_today(self)
        return super()._get_rate_date()
