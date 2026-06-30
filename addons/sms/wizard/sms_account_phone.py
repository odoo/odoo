# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.addons.sms.tools.sms_api import ERROR_MESSAGES, SmsApi
from odoo.exceptions import ValidationError


class SmsAccountPhone(models.TransientModel):
    _name = 'sms.account.phone'
    _description = 'SMS Account Registration Phone Number Wizard'

    account_id = fields.Many2one('iap.account', required=True)
    phone_number = fields.Char(required=True)

    def action_send_verification_code(self):
        status = SmsApi(self.env, self.account_id)._send_verification_sms(self.phone_number)['state']
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
