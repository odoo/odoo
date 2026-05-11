# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.addons.sms.tools.sms_api import ERROR_MESSAGES, SmsApi
from odoo.addons.phone_validation.tools import phone_validation
from odoo.exceptions import ValidationError


class SmsAccountPhone(models.TransientModel):
    _name = 'sms.account.phone'
    _description = 'SMS Account Registration Phone Number Wizard'

    account_id = fields.Many2one('iap.account', required=True)
    phone_number = fields.Char(required=True)

    def action_send_verification_code(self):
        status = SmsApi(self.env, self.account_id)._send_verification_sms(self.phone_number)['state']

        if status == 'country_not_supported':
            country = False

            country_code = phone_validation.phone_get_country_code_for_number(self.phone_number)
            if country_code:
                country = self.env['res.country'].search([('code', '=', country_code)], limit=1)

            return {
                'type': 'ir.actions.act_window',
                'name': _('Country Not Supported'),
                'target': 'new',
                'view_mode': 'form',
                'res_model': 'sms.account.phone.error',
                'context': {
                    'default_phone_number': self.phone_number,
                    'default_country_id': country.id if country else False,
                    'dialog_size': 'small',
                },
            }

        if status != 'success':
            raise ValidationError(ERROR_MESSAGES.get(status, ERROR_MESSAGES['unknown_error']))

        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': _('Register Account'),
            'view_mode': 'form',
            'res_model': 'sms.account.code',
            'context': {'default_account_id': self.account_id.id},
        }


class SmsAccountPhoneError(models.TransientModel):
    _name = 'sms.account.phone.error'
    _description = 'SMS Country Not Supported Error'

    phone_number = fields.Char()
    country_id = fields.Many2one('res.country')

    def action_setup_twilio(self):
        twilio_module = self.env['ir.module.module'].search([('name', '=', 'sms_twilio')], limit=1)

        if twilio_module and twilio_module.state != 'installed':
            twilio_module.button_immediate_install()

        return {
            'name': _('Set up Twilio'),
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_mode': 'form',
            'res_model': 'sms.twilio.account.manage',
        }
