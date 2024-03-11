# -*- coding: utf-8 -*-
from odoo import models
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    def create_debit(self):
        self.ensure_one()
        for move in self.move_ids:
            if move.journal_id.country_code == 'SA' and not self.reason:
                raise UserError(_("For debit notes issued in Saudi Arabia, you need to specify a Reason"))
        return super().create_debit()
