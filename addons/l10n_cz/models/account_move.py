# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('country_code')
    def _compute_taxable_supply_date(self):
        super()._compute_taxable_supply_date()
        for move in self.filtered(lambda m: m.country_code == 'CZ' and not m.taxable_supply_date):
            move.taxable_supply_date = fields.Date.context_today(move)

    @api.depends('country_code')
    def _compute_show_taxable_supply_date(self):
        super()._compute_show_taxable_supply_date()
        for move in self.filtered(lambda m: m.country_code == 'CZ' and m.move_type != 'entry'):
            move.show_taxable_supply_date = True

    def _compute_date(self):
        super()._compute_date()
        for move in self:
            if move.country_code == 'CZ' and move.taxable_supply_date and move.state == 'draft' and not move.statement_line_id:
                move.date = move.taxable_supply_date

    def _get_invoice_currency_rate_date(self):
        self.ensure_one()
        if self.country_code == 'CZ' and self.taxable_supply_date:
            return self.taxable_supply_date
        return super()._get_invoice_currency_rate_date()
