# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _compute_l10n_latam_document_type(self):
        """ Override for debit notes. This sets the same document type as the one on the origin. Cannot
         override the defaults in the account.move.debit wizard because l10n_latam_invoice_document explicitly
         calls _compute_l10n_latam_document_type() after the debit note is created. """
        br_debit_notes = self.filtered(lambda m: m.state == "draft" and m.country_code == "BR" and m.debit_origin_id.l10n_latam_document_type_id)
        for move in br_debit_notes:
            move.l10n_latam_document_type_id = move.debit_origin_id.l10n_latam_document_type_id

        return super(AccountMove, self - br_debit_notes)._compute_l10n_latam_document_type()

    def _get_last_sequence_domain(self, relaxed=False):
        """ Override to give sequence names in the same journal their own, independent numbering. """
        where_string, param = super()._get_last_sequence_domain(relaxed)
        if self.country_code == "BR" and self.l10n_latam_use_documents:
            where_string += " AND l10n_latam_document_type_id = %(l10n_latam_document_type_id)s "
            param["l10n_latam_document_type_id"] = self.l10n_latam_document_type_id.id or 0
        return where_string, param
