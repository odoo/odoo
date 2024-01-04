from odoo import models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("country_code", "move_type")
    def _compute_show_delivery_date(self):
        # EXTEND 'account'
        super()._compute_show_delivery_date()
        for move in self.filtered(lambda m: m.country_code == 'FR'):
            move.show_delivery_date = move.is_sale_document()

    def _post(self, soft=True):
        # EXTEND 'account'
        res = super()._post(soft=soft)
        for move in self.filtered(lambda m: m.show_delivery_date and not m.delivery_date):
            move.delivery_date = move.invoice_date
        return res
