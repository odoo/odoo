# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.l10n_th_edi_inet.models.account_move import CREDIT_NOTE_REASONS


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_th_edi_credit_note_reason = fields.Selection(selection=CREDIT_NOTE_REASONS, string="Credit Note Reason")
    l10n_th_edi_other_reason = fields.Char(string="Other Reason")
    l10n_th_edi_available_reasons = fields.Json(compute='_compute_l10n_th_edi_available_reasons')

    @api.depends('move_ids')
    def _compute_l10n_th_edi_available_reasons(self):
        for wizard in self:
            wizard.l10n_th_edi_available_reasons = wizard.move_ids._l10n_th_edi_get_available_reasons()

    def _prepare_default_reversal(self, move):
        # EXTENDS 'account'
        return {
            **super()._prepare_default_reversal(move),
            'l10n_th_edi_credit_note_reason': self.l10n_th_edi_credit_note_reason,
            'l10n_th_edi_other_reason': self.l10n_th_edi_other_reason,
        }

    def reverse_moves(self, is_modify=False):
        # EXTENDS 'account'
        if self.l10n_th_edi_credit_note_reason:
            self.reason = self.env['account.move']._l10n_th_edi_get_reason_text(self.l10n_th_edi_credit_note_reason, self.l10n_th_edi_other_reason)
        return super().reverse_moves(is_modify=is_modify)
