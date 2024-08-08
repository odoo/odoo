# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.misc import format_date


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=True)
    def _except_audit_trail(self):
        audit_trail_attachments = self.filtered(lambda attachment:
            attachment.res_model == 'account.move'
            and attachment.res_id
            and guess_mimetype(attachment.raw) in (
                'application/pdf',
                'application/xml',
            )
        )
        id2move = self.env['account.move'].browse(set(audit_trail_attachments.mapped('res_id'))).exists().grouped('id')
        for attachment in audit_trail_attachments:
            move = id2move.get(attachment.res_id)
            if move and move.posted_before and move.country_code == 'DE':
                raise UserError(_("You cannot remove parts of the audit trail."))

    def write(self, vals):
        if vals.keys() & {'res_id', 'res_model', 'raw', 'datas', 'store_fname', 'db_datas'}:
            self._except_audit_trail()
        return super().write(vals)

    def unlink(self):
        invoice_pdf_attachments = self.filtered(lambda attachment:
            attachment.res_model == 'account.move'
            and attachment.res_id
            and attachment.res_field in ('invoice_pdf_report_file', 'ubl_cii_xml_id')
        )
        if invoice_pdf_attachments:
            # only detach the document from the field, but keep it in the database for the audit trail
            # it shouldn't be an issue as there aren't any security group on the fields as it is the public report
            invoice_pdf_attachments.res_field = False
            today = format_date(self.env, fields.Date.context_today(self))
            for attachment in invoice_pdf_attachments:
                attachment.name = _(
                    '%(attachment_name)s (detached by %(user)s on %(date)s)',
                    attachment_name=attachment.name,
                    user=self.env.user.name,
                    date=today,
                )
        return super(IrAttachment, self - invoice_pdf_attachments).unlink()
