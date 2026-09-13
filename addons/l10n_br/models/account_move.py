from odoo import models
from odoo.fields import Domain


class AccountMove(models.Model):
    _inherit = "account.move"

    def _compute_l10n_latam_document_type_id(self):
        """Override for debit notes. This sets the same document type as the one on the origin. Cannot
        override the defaults in the account.debit.note wizard because l10n_latam_invoice_document explicitly
        calls _compute_l10n_latam_document_type_id() after the debit note is created."""
        br_debit_notes = self.filtered(
            lambda m: (
                m.state == "draft"
                and m.country_code == "BR"
                and m.debit_origin_id.l10n_latam_document_type_id
            )
        )
        for move in br_debit_notes:
            move.l10n_latam_document_type_id = (
                move.debit_origin_id.l10n_latam_document_type_id
            )

        return super(
            AccountMove, self - br_debit_notes
        )._compute_l10n_latam_document_type_id()

    def _get_domain_last_sequence(self, relaxed=False):
        domain = super()._get_domain_last_sequence(relaxed)
        if self.country_code == "BR" and self.l10n_latam_use_documents:
            document_type = self.l10n_latam_document_type_id
            domain &= (
                Domain("l10n_latam_document_type_id", "=", document_type.id)
                if document_type
                else Domain.FALSE
            )
        return domain
