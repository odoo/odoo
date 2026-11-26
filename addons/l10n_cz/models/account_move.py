# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _is_taxable_supply_date_used(self):
        # EXTENDS 'account'
        return self.country_code == 'CZ' or super()._is_taxable_supply_date_used()

    @api.depends('country_code')
    def _compute_taxable_supply_date(self):
        super()._compute_taxable_supply_date()
        for move in self.filtered(lambda m: m.country_code == 'CZ' and not m.taxable_supply_date):
            move.taxable_supply_date = fields.Date.context_today(move)
