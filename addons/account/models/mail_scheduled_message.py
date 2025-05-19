from odoo import fields, models


class MailScheduledMessage(models.Model):
    _inherit = 'mail.scheduled.message'

    # JSON field to store all move related data to generate and send invoice
    scheduled_send_payload = fields.Json()

    def _post_message(self, raise_exception=True):
        remained_scheduled_message = self.env['mail.scheduled.message']

        for scheduled_message in self:
            payload = scheduled_message.scheduled_send_payload
            if not (payload and scheduled_message.model == 'account.move'):
                remained_scheduled_message += scheduled_message
                continue

            move_id = self.env['account.move'].browse(scheduled_message.res_id)
            if not move_id:
                remained_scheduled_message += scheduled_message
                continue

            payload_attachments_widget = payload.get('mail_attachments_widget', [])
            attachments_name_from_payload = [d.get('name') for d in payload_attachments_widget]
            attachment_widget_data = [
                {
                    'id': attachment.id,
                    'name': attachment.name,
                    'mimetype': attachment.mimetype,
                    'placeholder': False,
                    'manual': True,
                }
                for attachment in scheduled_message.attachment_ids
                if attachment.name not in attachments_name_from_payload
            ]
            sending_settings = {
                **payload,
                'mail_partner_ids': scheduled_message.partner_ids.ids,
                'mail_subject': scheduled_message.subject,
                'mail_body': scheduled_message.body,
                'pdf_report': self.env['ir.actions.report'].browse(payload['pdf_report']),
                'mail_template': self.env['mail.template'].browse(payload['mail_template']),
                'mail_attachments_widget': payload_attachments_widget + attachment_widget_data,
            }

            # The generate and send invoice logic (including any EDI sending methods) with extra manual attachment if any
            self.env['account.move.send']._generate_and_send_invoices(
                move_id,
                payload.get('allow_fallback_pdf', False),
                **sending_settings,
            )
            scheduled_message.unlink()

        if remained_scheduled_message:
            super(MailScheduledMessage, remained_scheduled_message)._post_message(raise_exception)
