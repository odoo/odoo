from odoo import models


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        # Add the Nilvera PDF to the mail attachments for answered commercial documents.
        attachments = super()._get_invoice_extra_attachments(move)
        if (
            move.l10n_tr_nilvera_send_status
            in {"commercial_approved", "commercial_rejected", "commercial_answered_automatically"}
            and move.message_main_attachment_id.id != move.invoice_pdf_report_id.id
        ):
            attachments += move.message_main_attachment_id
        return attachments
