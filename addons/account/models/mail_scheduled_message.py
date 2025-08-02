from odoo import fields, models, _
from odoo.fields import Datetime


class MailScheduledMessage(models.Model):
    _inherit = 'mail.scheduled.message'

    # JSON field to store all move related data to generate and send invoice
    scheduled_send_payload = fields.Json()
    from_move_send_wizard = fields.Boolean()

    def unlink(self):
        for scheduled_message in self:
            if scheduled_message.is_note and scheduled_message.from_move_send_wizard and not scheduled_message.env.context.get('from_post'):
                move_id = self.env['account.move'].browse(scheduled_message.res_id)
                user = self.env.user
                create_date = Datetime.context_timestamp(user, Datetime.from_string(scheduled_message.create_date)).strftime('%Y-%m-%d %H:%M:%S')
                now = Datetime.context_timestamp(user, Datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
                replace_body = _('scheduled by %(author)s at %(create_date)s is cancelled by %(current_user)s at %(now)s',
                    author=scheduled_message.author_id.name,
                    create_date=create_date,
                    current_user=user.name,
                    now=now,
                )
                body = scheduled_message.body.replace('is scheduled to send', replace_body)
                move_id.message_post(
                    author_id=scheduled_message.author_id.id,
                    body=body,
                    subtype_xmlid='mail.mt_note',
                )
        return super().unlink()

    def post_message(self):
        super(MailScheduledMessage, self.with_context(post_manual=True)).post_message()

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

            sending_settings = {
                **payload,
                'pdf_report': self.env['ir.actions.report'].browse(payload['pdf_report']),
                'mail_template': self.env['mail.template'].browse(payload['mail_template']),
            }
            if payload['sending_methods'] and 'email' in payload['sending_methods']:
                payload_attachments_widget = payload.get('mail_attachments_widget', [])
                attachments_name_from_payload = [d.get('name') for d in payload_attachments_widget]
                manual_attachments_widget_data = [
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
                    **sending_settings,
                    'mail_partner_ids': scheduled_message.partner_ids.ids,
                    'mail_subject': scheduled_message.subject,
                    'mail_body': scheduled_message.body,
                    'mail_attachments_widget': payload_attachments_widget + manual_attachments_widget_data,
                }

            # The generate and send invoice logic (including any EDI sending methods) with extra manual attachment if any
            attachments = self.env['account.move.send']._generate_and_send_invoices(
                move_id,
                payload.get('allow_fallback_pdf', False),
                **sending_settings,
            )
            if attachments and scheduled_message.from_move_send_wizard and scheduled_message.is_note:
                msg = _('sent')
                body = scheduled_message.body.replace('scheduled to send', msg)
                is_post_manual = self.env.context.get('post_manual')
                author_id = self.env.user.partner_id.id if is_post_manual else self.env.ref('base.partner_root').id
                move_id.message_post(
                    author_id=author_id,
                    subject=scheduled_message.subject,
                    body=body,
                    subtype_xmlid='mail.mt_note',
                )
            scheduled_message.with_context(from_post=True).unlink()

        if remained_scheduled_message:
            super(MailScheduledMessage, remained_scheduled_message)._post_message(raise_exception)

    def get_sending_method_and_edi_data(self):
        methods_data = {
            'sending_methods': [],
            'extra_edis': [],
        }
        for scheduled_message in self:
            if scheduled_message.scheduled_send_payload:
                for sending_method in scheduled_message.scheduled_send_payload['sending_methods']:
                    if sending_method not in methods_data['sending_methods'] and sending_method != 'email':
                        # Exclude 'email' as it is neccessary to allow scheduling mlutiple emails at once
                        methods_data['sending_methods'].append(sending_method)
                for extra_edi in scheduled_message.scheduled_send_payload['extra_edis']:
                    if extra_edi not in methods_data['extra_edis']:
                        methods_data['extra_edis'].append(extra_edi)
        return methods_data
