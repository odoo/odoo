# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    taxable_supply_date = fields.Date(default=fields.Date.today())

    @api.depends('taxable_supply_date')
    def _compute_date(self):
        super()._compute_date()
        for move in self:
            if move.country_code == 'CZ' and move.taxable_supply_date and move.state == 'draft':
                move.date = move.taxable_supply_date
