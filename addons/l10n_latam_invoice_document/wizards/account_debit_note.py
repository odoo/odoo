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
