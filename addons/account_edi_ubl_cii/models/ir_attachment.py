from odoo import _, api, models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _filter_protected_ubl_cii_attachments(self):
        protected_attachments = self.env['ir.attachment']
        for attachment in self.filtered(lambda a: a.res_model == 'account.move' and a.res_id):
            # Imported XML that generate PDF must remain deletable
            if attachment.res_field == 'invoice_pdf_report_file':
                continue
            message = self.env['mail.message'].search(
                [('attachment_ids', 'in', attachment.id)],
                limit=1,
            )
            if message.attachment_ids.filtered(
                lambda a: a.res_model == 'account.move'
                and a.res_field == 'ubl_cii_xml_file'
            ):
                protected_attachments |= attachment

        return protected_attachments

    @api.ondelete(at_uninstall=False)
    def _unlink_except_received_ubl_cii_attachments(self):
        if self.env.context.get('account_edi_ubl_cii_skip_protected_attachments'):
            return
        if self._filter_protected_ubl_cii_attachments():
            raise UserError(_("Attachment imported electronically cannot be deleted"))
