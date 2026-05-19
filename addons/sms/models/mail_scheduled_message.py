from odoo import fields, models, modules, _
from odoo.tools import html2plaintext


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

    def _post_message(self, raise_exception=True):
        sms_scheduled = self.filtered(lambda m: m.send_method == 'sms')
        mail_scheduled = self - sms_scheduled

        auto_commit = not modules.module.current_test

        for scheduled_message in sms_scheduled:
            try:
                with self.env.cr.savepoint():
                    record = self.env[scheduled_message.model].browse(scheduled_message.res_id)
                    if not record.exists():
                        continue

                    subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')
                    record.with_context(message_type='sms')._message_sms(
                        body=html2plaintext(scheduled_message.body, include_references=False),
                        subtype_id=subtype_id,
                    )
                    scheduled_message.unlink()

                    if auto_commit and not raise_exception:
                        self.env.cr.commit()

            except Exception as e:
                if auto_commit and not raise_exception:
                    self.env.cr.rollback()

                if raise_exception:
                    raise e
                continue

        if mail_scheduled:
            return super(MailScheduledMessage, mail_scheduled)._post_message(raise_exception=raise_exception)

    def open_edit_form(self):
        self.ensure_one()

        if self.send_method == 'sms':

            view = self.env.ref('sms.sms_composer_view_form', raise_if_not_found=False)
            view_id = view.id if view else False

            return {
                'name': _('Edit Scheduled SMS'),
                'type': 'ir.actions.act_window',
                'res_model': 'sms.composer',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                'target': 'new',
                'context': {
                    'default_mail_scheduled_message_id': self.id,
                    'dialog_size': 'medium',
                },
            }

        return super().open_edit_form()
