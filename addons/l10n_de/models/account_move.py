from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _is_delivery_date_expected(self):
        # EXTENDS 'account'
        return self.country_code == 'DE' or super()._is_delivery_date_expected()

    def _is_taxable_supply_date_used(self):
        # EXTENDS 'account'
        return self.country_code == 'DE' or super()._is_taxable_supply_date_used()

    def _post(self, soft=True):
        for move in self:
            if move.country_code == 'DE' and move.is_sale_document() and not move.delivery_date:
                move.delivery_date = move.invoice_date or fields.Date.context_today(self)
        return super()._post(soft)
