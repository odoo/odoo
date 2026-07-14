from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    taxable_supply_date = fields.Date()

    def _get_accounting_date_source(self):
        self.ensure_one()
        if self.country_code == 'PL' and self.taxable_supply_date:
            return self.taxable_supply_date
        return super()._get_accounting_date_source()

    @api.depends('taxable_supply_date')
    def _compute_date(self):
        super()._compute_date()

    @api.depends('taxable_supply_date')
    def _compute_invoice_currency_rate(self):
        # In Poland, the currency rate should be based on the taxable supply date.
        super()._compute_invoice_currency_rate()

    def _get_invoice_currency_rate_date(self):
        self.ensure_one()
        if self.country_code == 'PL' and self.taxable_supply_date:
            return self.taxable_supply_date
        return super()._get_invoice_currency_rate_date()
