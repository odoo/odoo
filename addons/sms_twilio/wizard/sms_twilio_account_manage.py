import logging
import requests

from odoo import _, fields, models
from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.sms_twilio.tools.sms_twilio import get_twilio_from_number
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SmsTwilioAccountManage(models.TransientModel):
    _name = 'sms.twilio.account.manage'
    _description = 'SMS Twilio Connection Wizard'

    company_id = fields.Many2one(comodel_name='res.company', required=True, readonly=True, default=lambda self: self.env.company)
    sms_provider = fields.Selection(related='company_id.sms_provider', readonly=False)
    sms_twilio_account_sid = fields.Char(related='company_id.sms_twilio_account_sid', readonly=False)
    sms_twilio_auth_token = fields.Char(related='company_id.sms_twilio_auth_token', readonly=False)
    sms_twilio_number_ids = fields.One2many(related='company_id.sms_twilio_number_ids', readonly=False)
    test_number = fields.Char("Test Number")

    def action_reload_numbers(self):
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
            country_code = phone_validation.phone_get_country_code_for_number(twilio_number.get('phone_number'))
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
        return {
            'name': _('Manage Twilio SMS'),
            'res_model': self._name,
            'res_id': self.id,
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'new',
        }

    def action_send_test(self):
        if not self.test_number:
            raise UserError(_("Please set the number to which you want to send a test SMS."))
        composer = self.env['sms.composer'].create({
            'body': _("This is a test SMS from Odoo"),
            'composition_mode': 'numbers',
            'numbers': self.test_number,
        })
        sms_su = composer._action_send_sms()[0]

        has_error = bool(sms_su.failure_type)
        if not has_error:
            message = _("The SMS has been sent from %s", get_twilio_from_number(self.company_id.sudo(), self.test_number).display_name)
        elif sms_su.failure_type != "unknown":
            sms_api = self.company_id._get_sms_api_class()(self.env)
            failure_type = dict(self.env['sms.sms']._fields['failure_type'].get_description(self.env)['selection']).get(sms_su.failure_type, sms_su.failure_type)
            message = _('%(failure_type)s: %(failure_reason)s',
                         failure_type=failure_type,
                         failure_reason=sms_api._get_sms_api_error_messages().get(sms_su.failure_type, failure_type),
            )
        else:
            message = _("Error: %s", sms_su.failure_type)
        return self._display_notification(
            notif_type='danger' if has_error else 'success',
            message=message,
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
