# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.l10n_th_edi_inet.models.account_move import DEBIT_NOTE_REASONS


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    l10n_th_edi_debit_note_reason = fields.Selection(selection=DEBIT_NOTE_REASONS, string="Debit Note Reason")
    l10n_th_edi_other_reason = fields.Char(string="Other Reason")
    l10n_th_edi_available_reasons = fields.Json(compute='_compute_l10n_th_edi_available_reasons')

    @api.depends('move_ids')
    def _compute_l10n_th_edi_available_reasons(self):
        for wizard in self:
            wizard.l10n_th_edi_available_reasons = wizard.move_ids._l10n_th_edi_get_available_reasons()

    def _prepare_default_values(self, move):
        # EXTENDS 'account_debit_note'
        return {
            **super()._prepare_default_values(move),
            'l10n_th_edi_debit_note_reason': self.l10n_th_edi_debit_note_reason,
            'l10n_th_edi_other_reason': self.l10n_th_edi_other_reason,
        }

    def create_debit(self):
        # EXTENDS 'account_debit_note'
        if self.l10n_th_edi_debit_note_reason:
            self.reason = self.env['account.move']._l10n_th_edi_get_reason_text(self.l10n_th_edi_debit_note_reason, self.l10n_th_edi_other_reason)
        return super().create_debit()
