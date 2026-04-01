# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from uuid import uuid4

from odoo import fields, models, _
from odoo.tools.urls import urljoin as url_join


class MailingSmsTest(models.TransientModel):
    _name = 'mailing.sms.test'
    _description = 'Test SMS Mailing'

    def _default_numbers(self):
        previous_numbers = self.env['mailing.sms.test'].search([('create_uid', '=', self.env.uid)], order='create_date desc', limit=1).numbers
        return previous_numbers or self.env.user.partner_id.phone_sanitized or ""

    numbers = fields.Text(string='Number(s)', required=True,
                          default=_default_numbers, help='Carriage-return-separated list of phone numbers')
    mailing_id = fields.Many2one('mailing.mailing', string='Mailing', required=True, ondelete='cascade')

    def _prepare_test_trace_values(self, record, sms_number, sms_uuid, body):
        trace_code = self.env['mailing.trace']._get_random_code()
        trace_values = {
            'is_test_trace': True,
            'mass_mailing_id': self.mailing_id.id,
            'model': record._name,
            'res_id': record.id,
            'sms_code': trace_code,
            'sms_number': sms_number,
            'sms_tracker_ids': [(0, 0, {'sms_uuid': sms_uuid})],
            'trace_type': 'sms',
        }
        unsubscribe_info = self.env['sms.composer']._get_unsubscribe_info(
            self.env['sms.composer']._get_unsubscribe_url(self.mailing_id.id, trace_code)
        )
        body = '%s\n%s' % (body or '', unsubscribe_info)
        return trace_values, body

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
        # create and send SMS for valid numbers (skip other, likely to crash)
        sms_values_list, trace_values_list = [], []
        for sanitized_number in valid_numbers:
            if not sanitized_number:
                continue
            sms_values = {
                'number': sanitized_number,
                'uuid': uuid4().hex,
                'state': 'outgoing',
            }
            # include unsubscribe link and generate fake trace to test unsubscribe
            # flow if sms_allow_unsubscribe is enabled
            sms_body = body
            if self.mailing_id.sms_allow_unsubscribe:
                trace_values, sms_body = self._prepare_test_trace_values(record, sanitized_number, sms_values['uuid'], sms_body)
                trace_values_list.append(trace_values)
            sms_values['body'] = sms_body
            sms_values_list.append(sms_values)
        sms_sudo = self.env['sms.sms'].sudo().create(sms_values_list)
        if trace_values_list:
            self.env['mailing.trace'].create(trace_values_list)

        sms_api = self.env.company._get_sms_api_class()(self.env)
        sent_sms_list = sms_api._send_sms_batch(
            [{
                'content': body,
                'numbers': [{'number': sms.number, 'uuid': sms.uuid} for sms in sms_sudo],
            }],
            delivery_reports_url=url_join(self[0].get_base_url(), '/sms/status')
        )

        notification_messages = []
        sms_uuid_to_number_map = {sms.uuid: sms.number for sms in sms_sudo}
        for sent_sms in sent_sms_list:
            recipient = sms_uuid_to_number_map.get(sent_sms.get('uuid'))
            # 'success' and 'sent' IAP/Twilio both resolve to 'pending' SMS state
            # (= send for Odoo) via IAP_TO_SMS_STATE_SUCCESS
            if sent_sms.get('state') in ('success', 'sent'):
                notification_messages.append(
                    _('Test SMS successfully sent to %s', recipient)
                )
            else:
                failure_explanation = sms_api._get_sms_api_error_messages().get(sent_sms['state'])
                failure_reason = sent_sms.get('failure_reason')
                notification_messages.append(_(
                    "Test SMS could not be sent to %(destination)s: %(state)s",
                    destination=recipient,
                    state=failure_explanation or failure_reason or _("An error occurred."),
                ))
        if invalid_numbers:
            notification_messages.append(
                _(
                    "Test SMS skipped those numbers as they appear invalid: %(numbers)s",
                    numbers=', '.join(invalid_numbers)
                )
            )

        if notification_messages:
            message_body = Markup(
                f"<ul>{''.join('<li>%s</li>' for _ in notification_messages)}</ul>"
            ) % tuple(notification_messages)
            self.mailing_id._message_log(body=message_body)

        return True
