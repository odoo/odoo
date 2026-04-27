from odoo import models, Command, _
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = ['account.journal']

    def _is_attachment_ocrizable(self, attachment):
        """ Checks if the attachment is in OCRizable formats such as PDF and images."""
        return (attachment.raw or b'').strip().startswith(b'%PDF') or attachment.mimetype in ['image/png', 'image/jpeg']

    def _check_attachments_ocrizable(self, attachments):
        all_attachments_ocrizable = True
        any_attachments_ocrizable = False

        for attachment in attachments:
            if self._is_attachment_ocrizable(attachment):
                any_attachments_ocrizable = True
            else:
                all_attachments_ocrizable = False

            if not all_attachments_ocrizable and any_attachments_ocrizable:
                break

        return all_attachments_ocrizable, any_attachments_ocrizable

    def _get_bank_statements_available_import_formats(self):
        result = super()._get_bank_statements_available_import_formats()
        result.extend(['PDF', 'JPEG', 'PNG'])
        return result

    def _import_bank_statement(self, attachments):
        all_attachments_ocrizable, any_attachments_ocrizable = self._check_attachments_ocrizable(attachments)

        if any_attachments_ocrizable and not all_attachments_ocrizable:
            return UserError(_("Mixing PDF/Image files with other file types is not allowed."))
        elif not all_attachments_ocrizable:
            return super()._import_bank_statement(attachments)

        statements = self.env['account.bank.statement'].create([
            {
                'journal_id': self.id,
                'attachment_ids': [Command.set(attachment.ids)],
                'message_main_attachment_id': attachment.id,
            }
            for attachment in attachments
        ])

        statements._send_batch_for_digitization()
        action = statements._get_records_action()
        if len(statements) > 1:
            action.update({
                'name': _("Generated Bank Statements")
            })
        return action
