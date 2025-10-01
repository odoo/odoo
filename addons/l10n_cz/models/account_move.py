# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    taxable_supply_date = fields.Date(compute='_compute_taxable_supply_date', store=True, readonly=False, precompute=True)

    @api.depends('country_code')
    def _compute_taxable_supply_date(self):
        for move in self.filtered(lambda m: m.country_code == 'CZ' and not m.taxable_supply_date):
            move.taxable_supply_date = fields.Date.context_today(move)

    @api.depends('taxable_supply_date')
    def _compute_date(self):
        draft_moves = self.filtered(lambda m: m.state == 'draft')
        super(AccountMove, draft_moves)._compute_date()
        for move in draft_moves.filtered(lambda m: m.country_code == 'CZ' and m.taxable_supply_date and not m.statement_line_id):
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
