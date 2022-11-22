# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    def _prepare_default_values(self, move):
        return {
            **super(AccountDebitNote, self)._prepare_default_values(move),
            'l10n_sa_reversal_reason': self.reason
        }

    def create_debit(self):
        self.ensure_one()
        for move in self.move_ids:
            if move.journal_id.country_code == 'SA' and not self.reason:
                raise UserError(_("For debit notes issued in Saudi Arabia, you need to specify a Reason"))
        return super().reverse_moves()
