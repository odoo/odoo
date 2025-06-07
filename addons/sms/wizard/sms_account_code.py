# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.addons.sms.tools.sms_api import ERROR_MESSAGES, SmsApi
from odoo.exceptions import ValidationError


class SMSAccountCode(models.TransientModel):
    _name = 'sms.account.code'
    _description = 'SMS Account Verification Code Wizard'

    account_id = fields.Many2one('iap.account', required=True)
    verification_code = fields.Char(required=True)

    def action_register(self):
        status = SmsApi(self.env, self.account_id)._verify_account(self.verification_code)['state']
        if status != 'success':
            raise ValidationError(ERROR_MESSAGES.get(status, ERROR_MESSAGES['unknown_error']))

        self.account_id.state = "registered"
        self.env['iap.account']._send_success_notification(
            message=_("Your SMS account has been successfully registered."),
        )

        sender_name_wizard = self.env['sms.account.sender'].create({
            'account_id': self.account_id.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': _('Choose your sender name'),
            'view_mode': 'form',
            'res_model': 'sms.account.sender',
            'res_id': sender_name_wizard.id,
        }
