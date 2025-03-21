import logging
import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.sms_twilio.tools.sms_tools import get_country_code_from_phone, get_twilio_from_number

_logger = logging.getLogger(__name__)


class SmsTwilioManageConnectionWizard(models.TransientModel):
    _name = 'sms_twilio.manage.connection.wizard'
    _description = 'SMS Twilio Connection Wizard'

    company_id = fields.Many2one(comodel_name='res.company', required=True, readonly=True, default=lambda self: self.env.company)
    sms_provider = fields.Selection(related='company_id.sms_provider', readonly=False)
    sms_twilio_account_sid = fields.Char(related='company_id.sms_twilio_account_sid', readonly=False)
    sms_twilio_auth_token = fields.Char(related='company_id.sms_twilio_auth_token', readonly=False)

    sms_twilio_number_ids = fields.One2many(related='company_id.sms_twilio_number_ids', readonly=False)
    sms_twilio_to_number = fields.Char("To Number")

    def reload_numbers(self):
        """Fetch the available numbers from Twilio account"""
        self.company_id._assert_twilio_sid()
        try:
            response = requests.get(
                f'https://api.twilio.com/2010-04-01/Accounts/{self.company_id.sms_twilio_account_sid}/IncomingPhoneNumbers.json',
                auth=(self.company_id.sms_twilio_account_sid, self.company_id.sms_twilio_auth_token),
                timeout=5,
            )
        except requests.exceptions.RequestException as e:
            _logger.warning('Twilio SMS API error: %s', str(e))
            return self._display_notification(
                notif_type='danger',
                message=_("An error occurred while fetching the numbers."),
            )

        json_response = response.json()
        if not response.ok:
            _logger.warning('Twilio SMS API error: %s', json_response.get('code'))
            return self._display_notification(
                notif_type='danger',
                message=_("Error: %s", json_response.get('message')),
            )

        self.sms_twilio_number_ids.unlink()
        for twilio_number in json_response.get('incoming_phone_numbers', []):
            country_code = get_country_code_from_phone(twilio_number.get('phone_number'))
            country_id = self.env['res.country'].search([
                ('code', '=', country_code)
            ], limit=1)
            if not self.env['sms.twilio.number'].search_count([
                ('company_id', '=', self.company_id.id),
                ('number', '=', twilio_number.get('phone_number')),
                ('country_id', '=', country_id.id),
            ], limit=1):
                self.env['sms.twilio.number'].create({
                    'company_id': self.company_id.id,
                    'number': twilio_number.get('phone_number'),
                    'country_id': country_id.id,
                })
        return self.company_id._action_sms_twilio_open_manage_connection_wizard(self)

    def action_test(self):
        if not self.sms_twilio_to_number:
            raise UserError(_("Please set the number to which you want to send a test SMS."))
        temp_partner = self.env['res.partner'].create({
            'name': 'Temporary Partner',
            'mobile': self.sms_twilio_to_number,
        })
        composer = self.env['sms.composer'].with_context(
            active_model='res.partner',
            active_id=temp_partner,
        ).create({'body': _("This is a test SMS from Odoo")})
        message_notif = composer._action_send_sms().notification_ids[0]

        res_error = False
        if not message_notif.failure_type:
            res_msg = _("The SMS has been sent from %s", get_twilio_from_number(self.company_id, self.sms_twilio_to_number).display_name)
        else:
            res_error = True
            if message_notif.failure_type != "unknown":
                res_msg = dict(message_notif._fields["failure_type"].selection).get(message_notif.failure_type)  # Translated error msg
            else:
                res_msg = _("Error: %s", message_notif.failure_reason)  # Not translated, coming from Twilio
        temp_partner.unlink()
        return self._display_notification(
            notif_type='danger' if res_error else 'success',
            message=res_msg,
        )

    def action_save(self):
        return {'type': 'ir.actions.act_window_close'}

    def _display_notification(self, notif_type, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Twilio SMS"),
                'message': message,
                'type': notif_type,
                'sticky': False,
            }
        }
