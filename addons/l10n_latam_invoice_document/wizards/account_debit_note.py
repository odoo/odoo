from odoo import models


class AccountDebitNote(models.TransientModel):

    _inherit = 'account.debit.note'

    def create_debit(self):
        """ Properly compute the latam document type of type debit note. """
        res = super().create_debit()
        new_move_id = res.get('res_id')
        if new_move_id:
            new_move = self.env['account.move'].browse(new_move_id)
            new_move._compute_l10n_latam_document_type()
            new_move._onchange_l10n_latam_document_type_id()
        return res

    def _prepare_default_values(self, move):
        default_values = super()._prepare_default_values(move)
        document_types = self.env['l10n_latam.document.type'].search([('internal_type', '=', 'debit_note'),
                                                                         ('country_id', '=', move.company_id.account_fiscal_country_id.id)])
        default_values['l10n_latam_document_type_id'] = document_types and document_types[0].id

        return default_values
