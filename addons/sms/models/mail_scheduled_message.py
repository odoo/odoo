from odoo import fields, models, _


class MailScheduledMessage(models.Model):
    _inherit = 'mail.scheduled.message'

    send_method = fields.Selection(
        selection=[
            ('email', 'Email'),
            ('sms', 'SMS'),
        ],
        string="Send Method",
        default='email',
        required=True
    )

    def _post_message_send(self, record):
        self.ensure_one()

        if self.send_method == 'sms':
            return self.env['sms.composer']._action_send_sms_comment_record(
                record=record,
                body=self.body,
                is_note=self.is_note,
            )

        return super()._post_message_send(record)

    def open_edit_form(self):
        self.ensure_one()

        if self.send_method == 'sms':
            return {
                'name': _('Edit Scheduled SMS'),
                'type': 'ir.actions.act_window',
                'res_model': 'sms.composer',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'new',
                'context': {
                    'default_mail_scheduled_message_id': self.id,
                    'dialog_size': 'medium',
                },
            }

        return super().open_edit_form()
