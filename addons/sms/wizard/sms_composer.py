# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.phone_validation.tools import phone_validation
from odoo.exceptions import UserError


class SendSMS(models.TransientModel):
    _name = 'sms.composer'
    _description = 'Send SMS'

    recipients = fields.Char('Recipients', required=True)
    message = fields.Text('Message', required=True)

    def _get_records(self, model):
        if self.env.context.get('active_domain'):
            records = model.search(self.env.context.get('active_domain'))
        elif self.env.context.get('active_ids'):
            records = model.browse(self.env.context.get('active_ids', []))
        else:
            records = model.browse(self.env.context.get('active_id', []))
        return records

    @api.model
    def default_get(self, fields):
        result = super(SendSMS, self).default_get(fields)
        active_model = self.env.context.get('active_model')

        if not self.env.context.get('default_recipients') and active_model and hasattr(self.env[active_model], '_sms_get_default_partners'):
            model = self.env[active_model]
            records = self._get_records(model)
            partners = records._sms_get_default_partners()
            phone_numbers = []
            no_phone_partners = []
            for partner in partners:
                number = phone_validation.phone_get_sanitized_record_number(partner, self.env.context.get('field_name') or 'mobile', 'country_id')
                if number:
                    phone_numbers.append(number)
                else:
                    no_phone_partners.append(partner.name)
            if len(partners) > 1:
                if no_phone_partners:
                    raise UserError(_('Missing mobile number for %s.') % ', '.join(no_phone_partners))
            result['recipients'] = ', '.join(phone_numbers)
        return result

    def action_send_sms(self):
        numbers = [number.strip() for number in self.recipients.split(',') if number.strip()]

        active_model = self.env.context.get('active_model')
        if active_model and hasattr(self.env[active_model], '_message_sms'):
            model = self.env[active_model]
            records = self._get_records(model)
            records[0]._message_sms(self.message, sms_numbers=numbers)
        else:
            self.env['sms.api']._send_sms(numbers, self.message)
        return True
