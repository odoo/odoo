# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import api, fields, models
from odoo.addons.sms.tools.sms_api import ERROR_MESSAGES, SmsApi
from odoo.exceptions import ValidationError


class SMSAccountSender(models.TransientModel):
    _name = 'sms.account.sender'
    _description = 'SMS Account Sender Name Wizard'

    account_id = fields.Many2one('iap.account', required=True)
    sender_name = fields.Char()

    @api.constrains("sender_name")
    def _check_sender_name(self):
        for record in self:
            if not re.match(r"[a-zA-Z0-9\- ]{3,11}", record.sender_name):
                raise ValidationError("Your sender name must be between 3 and 11 characters long and only contain alphanumeric characters.")

    def action_set_sender_name(self):
        status = SmsApi(self.env, self.account_id)._set_sender_name(self.sender_name)['state']
        if status != 'success':
            raise ValidationError(ERROR_MESSAGES.get(status, ERROR_MESSAGES['unknown_error']))
