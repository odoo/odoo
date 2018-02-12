# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging


from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.iap.models import iap

_logger = logging.getLogger(__name__)

try:
    import phonenumbers
    _sms_phonenumbers_lib_imported = True

except ImportError:
    _sms_phonenumbers_lib_imported = False
    _logger.info(
        "The `phonenumbers` Python module is not available. "
        "Phone number validation will be skipped. "
        "Try `pip3 install phonenumbers` to install it."
    )


class SendSMS(models.TransientModel):
    _name = 'sms.send_sms'

    recipients = fields.Char('Recipients', required=True)
    message = fields.Text('Message', required=True)

    def _phone_get_country(self, partner):
        if 'country_id' in partner:
            return partner.country_id
        return self.env.user.company_id.country_id

    def _sms_sanitization(self, partner, field_name):
        number = partner[field_name]
        if number and _sms_phonenumbers_lib_imported:
            country = self._phone_get_country(partner)
            country_code = country.code if country else None
            try:
                phone_nbr = phonenumbers.parse(number, region=country_code, keep_raw_input=True)
            except phonenumbers.phonenumberutil.NumberParseException:
                return number
            if not phonenumbers.is_possible_number(phone_nbr) or not phonenumbers.is_valid_number(phone_nbr):
                return number
            phone_fmt = phonenumbers.PhoneNumberFormat.INTERNATIONAL
            return phonenumbers.format_number(phone_nbr, phone_fmt).replace(' ', '')
        else:
            return number

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
        model = self.env[active_model]

        records = self._get_records(model)
        if getattr(records, '_get_default_sms_recipients'):
            partners = records._get_default_sms_recipients()
            phone_numbers = []
            no_phone_partners = []
            for partner in partners:
                number = self._sms_sanitization(partner, self.env.context.get('field_name') or 'mobile')
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
        numbers = self.recipients.split(',')

        active_model = self.env.context.get('active_model')
        model = self.env[active_model]
        records = self._get_records(model)
        if getattr(records, 'message_post_send_sms'):
            records.message_post_send_sms(self.message, numbers=numbers)
        else:
            self.env['sms.api']._send_sms(numbers, self.message)
        return True
