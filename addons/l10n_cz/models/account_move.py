# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    taxable_supply_date = fields.Date(default=fields.Date.today())

    @api.depends('taxable_supply_date')
    def _compute_date(self):
        super()._compute_date()
        for move in self:
            if move.country_code == 'CZ' and move.taxable_supply_date and move.state == 'draft' and not move.statement_line_id:
                move.date = move.taxable_supply_date

    @api.depends('taxable_supply_date')
    def _compute_invoice_currency_rate(self):
        # In the Czech Republic, the currency rate should be based on the taxable supply date.
        super()._compute_invoice_currency_rate()

    @api.depends('taxable_supply_date')
    def _compute_expected_currency_rate(self):
        super()._compute_expected_currency_rate()

    def _get_invoice_currency_rate_date(self):
        self.ensure_one()
        if self.country_code == 'CZ' and self.taxable_supply_date:
            return self.taxable_supply_date
        return super()._get_invoice_currency_rate_date()
