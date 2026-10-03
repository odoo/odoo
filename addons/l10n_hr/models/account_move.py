from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('country_code')
    def _compute_taxable_supply_date(self):
        super()._compute_taxable_supply_date()
        for move in self.filtered(lambda m: m.country_code == 'HR' and not m.taxable_supply_date):
            move.taxable_supply_date = fields.Date.context_today(move) if not move.delivery_date else move.delivery_date

    @api.depends('country_code')
    def _compute_show_taxable_supply_date(self):
        super()._compute_show_taxable_supply_date()
        for move in self.filtered(lambda m: m.country_code == 'HR'):
            move.show_taxable_supply_date = True

    def _get_accounting_date_source(self):
        return (self.country_code == 'HR' and self.taxable_supply_date) or super()._get_accounting_date_source()

    def _get_invoice_currency_rate_date(self):
        return (self.country_code == 'HR' and self.taxable_supply_date) or super()._get_invoice_currency_rate_date()
