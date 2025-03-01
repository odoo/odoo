from odoo import models


class AccountDebitNote(models.TransientModel):

    _inherit = 'account.debit.note'

    def _prepare_default_values(self, move):
        default_values = super()._prepare_default_values(move)

        # properly compute debit type
        debit_note = self.env['account.move'].new({
            'move_type': default_values.get('move_type'),
            'journal_id': default_values.get('journal_id'),
            'partner_id': move.partner_id.id,
            'company_id': move.company_id.id,
        })
        document_types = debit_note.l10n_latam_available_document_type_ids.filtered(lambda x: x.internal_type == 'debit_note')
        default_values['l10n_latam_document_type_id'] = document_types and document_types[0].ids[0]
        return default_values
