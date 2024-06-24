from odoo import models


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        if invoice.country_code == 'PT':
            # Marking the invoice as sent will trigger the generation of the hash
            # and the invoice QR code so that they can be displayed on the generated PDF attachment
            invoice.is_move_sent = True
