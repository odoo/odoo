from odoo import models, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('invoice_date')
    def _compute_delivery_date(self):
        # EXTENDS 'account'
        super()._compute_delivery_date()
        for move in self:
            if move.invoice_date and move.country_code == 'BG' and not move.delivery_date:
                move.delivery_date = move.invoice_date

    @api.depends('country_code', 'move_type')
    def _post(self, soft=True):
        for move in self:
            if move.country_code == 'BG' and move.is_sale_document() and not move.delivery_date:
                move.delivery_date = move.invoice_date
        return super()._post(soft)
