# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.addons.phone_validation.tools import phone_validation


class MassSMSTest(models.TransientModel):
    _name = 'mailing.sms.test'
    _description = 'Test SMS Mailing'

    def _default_numbers(self):
        return self.env.user.partner_id.phone_sanitized or ""

    numbers = fields.Text(string='Number(s)', required=True,
                          default=_default_numbers, help='Carriage-return-separated list of phone numbers')
    mailing_id = fields.Many2one('mailing.mailing', string='Mailing', required=True, ondelete='cascade')

    def action_send_sms(self):
        self.ensure_one()

        numbers = [number.strip() for number in self.numbers.splitlines()]
        sanitize_res = phone_validation.phone_sanitize_numbers_w_record(numbers, self.env.user)
        sanitized_numbers = [info['sanitized'] for info in sanitize_res.values() if info['sanitized']]
        invalid_numbers = [number for number, info in sanitize_res.items() if info['code']]

        record = self.env[self.mailing_id.mailing_model_real].search([], limit=1)
        body = self.mailing_id.body_plaintext
        if record:
            # Returns a proper error if there is a syntax error with qweb
            body = self.env['mail.render.mixin']._render_template(body, self.mailing_id.mailing_model_real, record.ids)[record.id]

        # res_id is used to map the result to the number to log notifications as IAP does not return numbers...
        # TODO: clean IAP to make it return a clean dict with numbers / use custom keys / rename res_id to external_id
        sent_sms_list = self.env['sms.api']._send_sms_batch([{
            'res_id': number,
            'number': number,
            'content': body,
        } for number in sanitized_numbers])

        error_messages = {}
        if any(sent_sms.get('state') != 'success' for sent_sms in sent_sms_list):
            error_messages = self.env['sms.api']._get_sms_api_error_messages()

        notification_messages = []
        if invalid_numbers:
            notification_messages.append(_('The following numbers are not correctly encoded: %s',
                ', '.join(invalid_numbers)))

        for sent_sms in sent_sms_list:
            if sent_sms.get('state') == 'success':
                notification_messages.append(
                    _('Test SMS successfully sent to %s', sent_sms.get('res_id')))
            elif sent_sms.get('state'):
                notification_messages.append(
                    _('Test SMS could not be sent to %s:<br>%s',
                    sent_sms.get('res_id'),
                    error_messages.get(sent_sms['state'], _("An error occurred.")))
                )

        if notification_messages:
            self.mailing_id._message_log(body='<ul>%s</ul>' % ''.join(
                ['<li>%s</li>' % notification_message for notification_message in notification_messages]
            ))

        return True
