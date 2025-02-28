from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def unlink(self):
        detached_pdf_reports = self.filtered(
            lambda attachment:
            attachment.res_model == 'account.move'
            and attachment.res_id
            and not attachment.res_field
            and attachment.raw
            and guess_mimetype(attachment.raw) == 'application/pdf'
            and attachment.company_id.account_fiscal_country_id.code == 'JO'
        )

        moves = self.env['account.move'].browse(detached_pdf_reports.mapped('res_id')).exists()
        id2move = {move.id: move for move in moves}
        for attachment in detached_pdf_reports:
            move = id2move.get(attachment.res_id)
            if move and move.posted_before and move.country_code == 'JO':
                raise UserError(_("You cannot delete this detached PDF."))

        invoice_pdf_attachments = self.filtered(
            lambda attachment:
            attachment.res_model == 'account.move'
            and attachment.res_id
            and attachment.res_field == 'invoice_pdf_report_file'
            and attachment.company_id.account_fiscal_country_id.code == 'JO'
        )
        # this detachment is done to keep attachments in DB
        # it shouldn't be an issue as there aren't any security group on the fields as it is the public report
        invoice_pdf_attachments._detach()

        return super(IrAttachment, self - invoice_pdf_attachments).unlink()
