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

    def _get_accounting_date_source(self):
        return (self.country_code == 'CZ' and self.taxable_supply_date) or super()._get_accounting_date_source()

    def _get_invoice_currency_rate_date(self):
        return (self.country_code == 'CZ' and self.taxable_supply_date) or super()._get_invoice_currency_rate_date()
