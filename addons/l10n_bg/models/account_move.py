# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('country_code')
    def _compute_show_taxable_supply_date(self):
        super()._compute_show_taxable_supply_date()
        for move in self.filtered(lambda m: m.country_code == 'BG' and m.move_type != 'entry' and (m.state == 'draft' or m.taxable_supply_date)):
            move.show_taxable_supply_date = True

    @api.depends('country_code')
    def _compute_taxable_supply_date_placeholder(self):
        super()._compute_taxable_supply_date_placeholder()
        for move in self.filtered(lambda m: m.country_code == 'BG'):
            move.taxable_supply_date_placeholder = self.env._("Invoice Date")

    def _get_accounting_date_source(self):
        return (self.country_code == 'BG' and self.taxable_supply_date) or super()._get_accounting_date_source()

    def _get_invoice_currency_rate_date(self):
        return (self.country_code == 'BG' and self.taxable_supply_date) or super()._get_invoice_currency_rate_date()

    def _get_default_currency_rate_date(self):
        return (self.country_code == 'BG' and self.taxable_supply_date) or super()._get_default_currency_rate_date()
