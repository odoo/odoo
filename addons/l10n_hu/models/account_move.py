# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('country_code')
    def _compute_show_taxable_supply_date(self):
        super()._compute_show_taxable_supply_date()
        for move in self.filtered(lambda m: m.country_code == 'HU' and m.move_type != 'entry' and (m.state == 'draft' or m.taxable_supply_date)):
            move.show_taxable_supply_date = True

    @api.depends('country_code')
    def _compute_taxable_supply_date_placeholder(self):
        super()._compute_taxable_supply_date_placeholder()
        for move in self.filtered(lambda m: m.country_code == 'HU'):
            move.taxable_supply_date_placeholder = self.env._("Invoice Date")

    @api.depends('country_code', 'delivery_date')
    def _compute_taxable_supply_date(self):
        super()._compute_taxable_supply_date()
        for move in self.filtered(lambda m: m.country_code == 'HU' and m.delivery_date):
            move.taxable_supply_date = move.delivery_date

    def _get_accounting_date_source(self):
        if self.country_code == 'HU' and self.taxable_supply_date:
            if self.is_purchase_document():
                return max(self.taxable_supply_date, self.invoice_date or self.taxable_supply_date)
            if self.move_type != 'out_refund':
                return self.taxable_supply_date
        return super()._get_accounting_date_source()

    def _get_invoice_currency_rate_date(self):
        return (self.country_code == 'HU' and self.move_type != 'out_refund' and self.taxable_supply_date) or super()._get_invoice_currency_rate_date()

    def _get_default_currency_rate_date(self):
        return (self.country_code == 'HU' and self.move_type != 'out_refund' and self.taxable_supply_date) or super()._get_default_currency_rate_date()

    def _post(self, soft=True):
        res = super()._post(soft)
        for move in self:
            if move.country_code == 'HU' and move.is_sale_document() and not move.taxable_supply_date:
                with self.env.protecting([self._fields['date'], self._fields['invoice_currency_rate']], move):
                    move.taxable_supply_date = move.invoice_date
        return res
