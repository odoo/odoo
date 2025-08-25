import re

from odoo import fields, models, _
from odoo.exceptions import UserError

from odoo.addons.sms_twilio.tools.sms_api import SmsApiTwilio


class ResCompany(models.Model):
    _inherit = 'res.company'

    sms_provider = fields.Selection(
        string='SMS Provider',
        selection=[
            ('iap', 'Send via Odoo'),
            ('twilio', 'Send via Twilio'),
        ],
        default='iap',
    )
    sms_twilio_account_sid = fields.Char("Account SID", groups='base.group_system')
    sms_twilio_auth_token = fields.Char("Auth Token", groups='base.group_system')
    sms_twilio_number_ids = fields.One2many("sms.twilio.number", "company_id", "Numbers")

    def _get_sms_api_class(self):
        self.ensure_one()
        if self.sms_provider == 'twilio':
            return SmsApiTwilio
        return super()._get_sms_api_class()

    def _assert_twilio_sid(self):
        self.ensure_one()
        account_sid = self.sms_twilio_account_sid
        if not account_sid or len(account_sid) != 34 or not account_sid.startswith('AC'):
            raise UserError(_("Invalid Twilio Account SID: must start with 'AC' and be 34 characters long."))
        if not re.match(r'^[A-Za-z0-9]{32}$', account_sid[2:]):
            raise UserError(_("Invalid Twilio Account SID: must only contain alphanumeric characters after 'AC'."))

    def _action_open_sms_twilio_account_manage(self):
        return {
            'name': _('Manage Twilio SMS'),
            'res_model': 'sms.twilio.account.manage',
            'res_id': False,
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'new',
        }
