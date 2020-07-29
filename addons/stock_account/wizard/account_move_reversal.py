# -*- coding: utf-8 -*-
from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    def _reverse_moves_post_hook(self, moves):
        if self.refund_method == "modify":
            moves.mapped("line_ids").filtered(lambda line: line.is_anglo_saxon_line).unlink()
        return super()._reverse_moves_post_hook(moves)
