from odoo import models


class MailComposeMessage(models.TransientModel):
    _name = 'mail.compose.message'
    _inherit = ['mail.compose.message']

    def _compute_attachment_ids(self):
        # EXTENDS
        super()._compute_attachment_ids()

        for composer in self:
            if composer.model != 'account.move':
                return
            moves = composer.env['account.move'].browse(composer._evaluate_res_ids())
            composer.attachment_ids += composer.env['ir.attachment'].browse([
                pdf.attachment_id for pdf in moves.mapped('invoice_pdf_report_file') if pdf
            ])
