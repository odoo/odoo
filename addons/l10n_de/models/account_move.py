from odoo import models, api, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('country_code', 'move_type')
    def _compute_show_delivery_date(self):
        # EXTENDS 'account'
        super()._compute_show_delivery_date()
        for move in self:
            if move.country_code == 'DE':
                move.show_delivery_date = move.is_sale_document()

    def _post(self, soft=True):
        for move in self:
            if move.country_code == 'DE' and move.is_sale_document() and not move.delivery_date:
                move.delivery_date = move.invoice_date or fields.Date.context_today(self)
        return super()._post(soft)
