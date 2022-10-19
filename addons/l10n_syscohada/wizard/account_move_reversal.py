# -*- coding: utf-8 -*-
from odoo import models
from odoo.addons.account import SYSCOHADA_LIST


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    def reverse_moves(self):
        if self.country_code in SYSCOHADA_LIST and self.currency_id != self.env.company.currency_id:
            return super(AccountMoveReversal, self.with_context(origin_date=True)).reverse_moves()
        else:
            return super().reverse_moves()
