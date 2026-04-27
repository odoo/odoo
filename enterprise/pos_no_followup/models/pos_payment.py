from odoo import models


class PosPayment(models.Model):
    _inherit = "pos.payment"

    def _create_payment_moves(self, values):
        moves = super()._create_payment_moves(values)
        moves.no_followup = False
        return moves
