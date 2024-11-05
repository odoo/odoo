from odoo import api, fields, models
from odoo.exceptions import UserError
import logging
from datetime import datetime
from pydantic import ValidationError
from twilio.rest import Client

_logger = logging.getLogger(__name__)


class CrmInherited(models.Model):
    _inherit = 'crm.lead'

    def send_message_twilio_method(self):
        account_sid = self.env['ir.config_parameter'].sudo().get_param('twilio_account_sid')
        auth_token = self.env['ir.config_parameter'].sudo().get_param('twilio_auth_token')
        twilio_phone_number = self.env['ir.config_parameter'].sudo().get_param('twilio_phone_number')
        if not account_sid or not auth_token or not twilio_phone_number:
            raise UserError("Twilio credentials are not set. Please configure them in System Parameters.")
        client = Client(account_sid, auth_token)
        try:
            if self.phone or self.mobile:
                message = client.messages.create(
                    body=f"Hi {self.name}, {self.env.company.lead_message_template}",
                    from_=twilio_phone_number,
                    to=self.phone or self.mobile,
                )
                _logger.info("SMS sent successfully via Twilio with SID: %s", message.sid)
                self.message_post(
                    body=f"SMS sent successfully to {message.to}: {message.body}",
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                )

                msg_dict = {
                    "account_sid": message.account_sid,
                    "body": message.body,
                    "date_sent": datetime.now(),
                    "direction": message.direction,
                    "error_code": message.error_code,
                    "error_message": message.error_message,
                    "from_phone": message.from_,
                    "messaging_service_sid": message.messaging_service_sid,
                    "sid": message.sid,
                    "status": message.status,
                    "to_phone": message.to,
                    "uri": message.uri,
                    "res_model": self._name,
                    "res_id": self.id,
                }
                log_message = self.env['twilio.message.log'].sudo().create(msg_dict)
            else:
                raise ValidationError("Phone and Mobile numbers are missing!")
        except Exception as e:
            _logger.error("Failed to send SMS via Twilio: %s", str(e))
            raise UserError("There was an error sending the SMS. Please check the log for more details.")
