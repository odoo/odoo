# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('delivery_date')
    def _compute_date(self):
        super()._compute_date()
        for move in self:
            if move.country_code == 'CZ' and move.delivery_date and move.state == 'draft':
                move.date = move.delivery_date
