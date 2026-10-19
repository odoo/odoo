from odoo import _, api, models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_rejected_zatca_document(self):
        '''
        Prevents unlinking of rejected XML documents
        '''
        descr = 'Rejected ZATCA Document not to be deleted - ثيقة ZATCA المرفوضة لا يجوز حذفها'
        for attach in self.filtered(lambda a: a.description == descr and a.res_model == 'account.move'):
            move = self.env['account.move'].browse(attach.res_id).exists()
            if move and move.country_code == "SA":
                raise UserError(_("You can't unlink an attachment being an EDI document refused by the government."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_validated_pdf_invoices(self):
        '''
        Prevents unlinking of invoice pdfs linked to an invoice
        where the pdf attachment was created after or at the same time as the edi_documents last write date.
        '''
        attachments_to_check = self.filtered(
            lambda attachment: attachment.res_model == "account.move"
            and attachment.res_field == "invoice_pdf_report_file"
            and attachment.res_id
        )
        res = self.env["l10n_sa_edi.document"]._read_group(
            domain=[("res_id", "in", attachments_to_check.mapped("res_id")), ("state", "in", ("accepted", "warning")), ("res_model", "=", "account.move")],
            aggregates=["write_date:min"],
            groupby=["res_id"],
        )
        edi_documents = dict(res)
        restricted_attachments = self.env["ir.attachment"]
        for attachment in attachments_to_check:
            if (document_date := edi_documents.get(attachment.res_id)) and attachment.create_date >= document_date:
                restricted_attachments += attachment
        if restricted_attachments:
            raise UserError(_(
                "Oops! The invoice PDF(s) are linked to a validated EDI document and cannot be deleted according to ZATCA rules: %s",
                ", ".join(restricted_attachments.mapped("name"))))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_government_document(self):
        if self.env['l10n_sa_edi.document'].sudo().search([('attachment_id', 'in', self.ids)]):
            raise UserError(self.env._("You can't unlink an attachment being a ZATCA document sent to the government"))

    def _get_posted_pdf_moves_to_check(self):
        # Extends l10n_sa: to bypass the unlink check in l10n_sa for posted moves
        return super()._get_posted_pdf_moves_to_check().filtered(lambda rec: not rec.l10n_sa_edi_state)
