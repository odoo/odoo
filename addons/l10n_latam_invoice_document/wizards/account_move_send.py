from odoo import api, models


class AccountMoveSend(models.Model):
    _inherit = 'account.move.send'

    @api.model
    def _get_invoice_pdf_report_filename(self, move):
        if move.l10n_latam_use_documents:
            return f"{move.l10n_latam_full_document_number.replace('/', '_')}.pdf"
        return super()._get_invoice_pdf_report_filename(move)
