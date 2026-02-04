from odoo import _, api, models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=True)
    def _except_submitted_invoices_pdfs(self):
        submitted_invoices_pdfs = self.filtered(
            lambda attachment:
            attachment.res_model == 'account.move'
            and attachment.res_id
            and attachment.res_field == 'invoice_pdf_report_file'
        )

        moves = self.env['account.move'].browse(submitted_invoices_pdfs.mapped('res_id')).exists()
        moves_with_jo_qr = moves.filtered('l10n_jo_edi_qr')
        if moves_with_jo_qr:
            raise UserError(_("You cannot delete this Invoice PDF as it has been submitted to JoFotara"))
