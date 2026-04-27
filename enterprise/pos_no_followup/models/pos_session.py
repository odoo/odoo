from odoo import models


class PosPayment(models.Model):
    _inherit = "pos.session"

    def _create_pay_later_receivable_lines(self, data):
        lines = super()._create_pay_later_receivable_lines(data)
        lines['pay_later_move_lines'].no_followup = False
        return lines
