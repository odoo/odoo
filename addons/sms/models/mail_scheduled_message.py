from odoo import models, _
from odoo.tools import html2plaintext
from odoo.tools.misc import clean_context


class MailScheduledMessage(models.Model):
    _inherit = 'mail.scheduled.message'

    def _post_message(self, raise_exception=True):
        sms_scheduled = self.filtered(lambda m: m.send_context and m.send_context.get('is_sms'))
        mail_scheduled = self - sms_scheduled

        for scheduled_message in sms_scheduled:

            ctx = dict(self.env.context,
                       default_res_model=scheduled_message.model,
                       default_res_id=scheduled_message.res_id,
                       default_composition_mode='comment')
            ctx.update(clean_context(scheduled_message.send_context or {}))

            composer = self.env['sms.composer'].with_user(scheduled_message.create_uid).with_context(ctx).create({
                'body': html2plaintext(scheduled_message.body),
                'res_model': scheduled_message.model,
                'res_id': scheduled_message.res_id,
                'composition_mode': 'comment',
                'mass_keep_log': True,
            })

            composer.action_send_sms()
            scheduled_message.unlink()

        if mail_scheduled:
            return super(MailScheduledMessage, mail_scheduled)._post_message(raise_exception=raise_exception)

    def open_edit_form(self):
        self.ensure_one()

        if self.send_context and self.send_context.get('is_sms'):

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
                    'default_res_model': self.model,
                    'default_res_id': self.res_id,
                    'default_body': html2plaintext(self.body),
                    'default_composition_mode': 'comment',
                    'default_scheduled_date': self.scheduled_date,
                    'mail_scheduled_message_id': self.id,
                    'dialog_size': 'medium',
                },
            }

        return super().open_edit_form()
