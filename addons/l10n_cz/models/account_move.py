# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    taxable_supply_date = fields.Date(default=fields.Date.today())

    @api.depends('taxable_supply_date', 'date')
    def _compute_date(self):
        super()._compute_date()
        for move in self:
            if move.country_code == 'CZ':
                # In case of sale document, we want to align the date with the taxable supply date (user can change it)
                if move.is_sale_document(include_receipts=True) and move.taxable_supply_date and move.state == 'draft':
                    move.date = move.taxable_supply_date
                # For other documents, we want to align the taxable supply date with the document date
                # since user can't set up the taxable supply date manually (most forms don't have this field)
                elif move.date and move.state == 'draft':
                    move.taxable_supply_date = move.date
