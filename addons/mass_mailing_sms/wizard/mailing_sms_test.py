# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from werkzeug.urls import url_join

from odoo import fields, models, _


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
        sanitized_numbers = [self.env.user._phone_format(number=number) for number in numbers]
        valid_numbers = [number for sanitized, number in zip(sanitized_numbers, numbers) if sanitized]
        invalid_numbers = [number for sanitized, number in zip(sanitized_numbers, numbers) if not sanitized]

        record = self.env[self.mailing_id.mailing_model_real].search([], limit=1)
        body = self.mailing_id.body_plaintext
        if record:
            # Returns a proper error if there is a syntax error with qweb
            body = self.env['mail.render.mixin']._render_template(body, self.mailing_id.mailing_model_real, record.ids)[record.id]

        new_sms_messages_sudo = self.env['sms.sms'].sudo().create([{'body': body, 'number': number} for number in valid_numbers])
        sms_api = self.env.company._get_sms_api_class()(self.env)
        sent_sms_list = sms_api._send_sms_batch([{
            'content': body,
            'numbers': [{'number': sms_id.number, 'uuid': sms_id.uuid} for sms_id in new_sms_messages_sudo],
        }], delivery_reports_url=url_join(self[0].get_base_url(), '/sms/status'))

        notification_messages = []
        if invalid_numbers:
            notification_messages.append(_('The following numbers are not correctly encoded: %s',
                ', '.join(invalid_numbers)))

        for sent_sms, db_sms in zip(sent_sms_list, new_sms_messages_sudo):
            recipient = db_sms.number or sent_sms.get('res_id')
            # 'success' and 'sent' IAP/Twilio both resolve to 'pending' SMS state
            # (= send for Odoo) via IAP_TO_SMS_STATE_SUCCESS
            if sent_sms.get('state') in ('success', 'sent'):
                notification_messages.append(
                    _('Test SMS successfully sent to %s', recipient))
            elif sent_sms.get('state'):
                failure_explanation = sms_api._get_sms_api_error_messages().get(sent_sms['state'])
                failure_reason = sent_sms.get('failure_reason')
                message = _('Test SMS could not be sent to %s: %s',
                    recipient,
                    failure_explanation or failure_reason or _("An error occurred."),
                )
                notification_messages.append(message)

        if notification_messages:
            message_body = Markup(
                f"<ul>{''.join('<li>%s</li>' for _ in notification_messages)}</ul>"
            ) % tuple(notification_messages)
            self.mailing_id._message_log(body=message_body)

        return True
