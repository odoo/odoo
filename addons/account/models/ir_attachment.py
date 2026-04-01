from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.misc import format_date

import io
import zipfile


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _build_zip_from_attachments(self):
        """ Return the zip bytes content resulting from compressing the attachments in `self`"""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zipfile_obj:
            for attachment in self:
                zipfile_obj.writestr(attachment.display_name, attachment.raw)
        return buffer.getvalue()

    @api.ondelete(at_uninstall=True)
    def _except_audit_trail(self):
        audit_trail_attachments = self.filtered(lambda attachment:
            attachment.res_model == 'account.move'
            and attachment.res_id
            and attachment.raw
            and attachment.company_id.restrictive_audit_trail
            and guess_mimetype(attachment.raw) in (
                'application/pdf',
                'application/xml',
            )
        )
        id2move = self.env['account.move'].browse(set(audit_trail_attachments.mapped('res_id'))).exists().grouped('id')
        for attachment in audit_trail_attachments:
            move = id2move.get(attachment.res_id)
            if move and move.posted_before and move.company_id.restrictive_audit_trail:
                ue = UserError(_("You cannot remove parts of a restricted audit trail."))
                ue._audit_trail = True
                raise ue

    def write(self, vals):
        if vals.keys() & {'res_id', 'res_model', 'raw', 'datas', 'store_fname', 'db_datas', 'company_id'}:
            try:
                self._except_audit_trail()
            except UserError as e:
                if (
                    not hasattr(e, '_audit_trail')
                    or vals.get('res_model') != 'documents.document'
                    or vals.keys() & {'raw', 'datas', 'store_fname', 'db_datas'}
                ):
                    raise  # do not raise if trying to version the attachment through a document
                vals.pop('res_model', None)
                vals.pop('res_id', None)
        return super().write(vals)

    def unlink(self):
        invoice_pdf_attachments = self.filtered(lambda attachment:
            attachment.res_model == 'account.move'
            and attachment.res_id
            and attachment.res_field in ('invoice_pdf_report_file', 'ubl_cii_xml_file')
            and attachment.company_id.restrictive_audit_trail
        )
        if invoice_pdf_attachments:
            # only detach the document from the field, but keep it in the database for the audit trail
            # it shouldn't be an issue as there aren't any security group on the fields as it is the public report
            invoice_pdf_attachments.res_field = False
            today = format_date(self.env, fields.Date.context_today(self))
            for attachment in invoice_pdf_attachments:
                attachment_name = attachment.name
                attachment_extension = ''
                dot_index = attachment_name.rfind('.')
                if dot_index > 0:
                    attachment_name = attachment.name[:dot_index]
                    attachment_extension = attachment.name[dot_index:]
                attachment.name = _(
                    '%(attachment_name)s (detached by %(user)s on %(date)s)%(attachment_extension)s',
                    attachment_name=attachment_name,
                    attachment_extension=attachment_extension,
                    user=self.env.user.name,
                    date=today,
                )
        return super(IrAttachment, self - invoice_pdf_attachments).unlink()

    def _post_add_create(self, **kwargs):
        for move_id, attachments in self.filtered(lambda attachment: attachment.res_model == 'account.move').grouped('res_id').items():
            move = self.env['account.move'].browse(move_id)
            files_data = move._to_files_data(attachments)
            files_data.extend(move._unwrap_attachments(files_data))
            move._extend_with_attachments(files_data)
        super()._post_add_create(**kwargs)
