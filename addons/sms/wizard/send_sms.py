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

    def _get_records(self, model):
        # if self.env.context.get('active_domain'):
        #     records = model.search(self.env.context.get('active_domain'))
        if self.env.context.get('active_ids'):
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
            for partner in partners:
                number = partner[self.env.context.get('field_name')] or partner['mobile'] or partner['phone']
                if number:
                    phone_numbers.append((partner.name, number))
                else:
                    no_phone_partners.append(partner.name)

            if len(partners) and no_phone_partners:
                if len(partners) == 1:
                    raise UserError(_('No number found on the contact.\n'
                                      'Please set one on the contact and try again.'))
                else:
                    raise UserError(_('No number found for the following contacts:\n%s') % '\n'.join(sorted(no_phone_partners)))

            result['sendto'] = '\n'.join(map(lambda x: '%s - %s' % x, sorted(phone_numbers)))
            result['recipients'] = ', '.join(map(lambda x: x[1], phone_numbers))

        return result

    def action_send_sms(self):
        numbers = self.recipients.split(',')

        active_model = self.env.context.get('active_model')
        model = self.env[active_model]
        records = self._get_records(model)

        partners = records._get_default_sms_recipients()

        if getattr(records, 'message_post_send_sms'):
            records.message_post_send_sms(self.message, numbers, partners)
        else:
            self.env['sms.api']._send_sms(numbers, self.message)


        return True
