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
    _description = 'Send SMS'

    recipients = fields.Char('Recipients', required=True)
    message = fields.Text('Message', required=True)
    sendto = fields.Text('Send to')
    template = fields.Many2one('mail.template', 'Template')

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
                raise UserError('Number %s must be in international format (E.164).'
                                'Make sure you correctly set the country code and have the right number of digits.' % (number))
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
        if getattr(records, '_get_default_sms_recipients') and not self.env.context.get('default_recipients'):
            partners = records._get_default_sms_recipients()
            phone_numbers = []
            no_phone_partners = []
            partner_numbers = []
            for partner in partners:
                # number = self._sms_sanitization(partner, self.env.context.get('field_name') or 'mobile' if partner.mobile else 'phone')
                number = partner[self.env.context.get('field_name') or 'mobile' if partner.mobile else 'phone']
                if number:
                    phone_numbers.append(number)
                    partner_numbers.append((partner.name, number))
                else:
                    no_phone_partners.append(partner.name)
            if len(partners) and no_phone_partners:
                if len(no_phone_partners) == 1:
                    raise UserError(_('No number found on the contact.\n'
                                      'Please set one on the contact and try again.'))
                else:
                    raise UserError(_('No number found for the following contacts:\n%s') % '\n'.join(sorted(no_phone_partners)))

            sendto = map(lambda partner_number: '%s - %s' % partner_number, sorted(partner_numbers))
            result['sendto'] = '\n'.join(sendto)
            result['recipients'] = ', '.join(phone_numbers)
        return result

    def action_send_sms(self):
        active_model = self.env.context.get('active_model')
        model = self.env[active_model]
        records = self._get_records(model)

        for partner in records:
            message_id = partner.message_post(body=self.message, message_type='sms')
            number = self._sms_sanitization(partner, self.env.context.get('field_name') or 'mobile' if partner.mobile else 'phone')
            sms = self.env['sms.sms'].create({
                'user_id': self.env.user.id,
                'partner_id': partner.id,
                'number': number,
                'body': self.message,
                'message_id': message_id.id,
            })
            sms.send_sms()

        # if getattr(records, 'message_post_send_sms'):
        #     records.message_post_send_sms(self.message, numbers=numbers)
        # else:
        #     self.env['sms.api']._send_sms(numbers, self.message)
        return True
