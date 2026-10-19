from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_discount_amount(self):
        self.ensure_one()
        if not self.quantity:
            return 0.0
        return (self.price_unit * self.quantity) - self.price_subtotal
