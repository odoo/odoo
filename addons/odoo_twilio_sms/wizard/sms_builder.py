# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import fields, models, _
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class SmsBuilder(models.TransientModel):
    """Class to handle all the functions required in send sms """
    _name = 'sms.builder'
    _description = 'SMS Builder'

    partner_id = fields.Many2one('res.partner', string='Recipient',
                                 help='Receiving User')
    receiving_number = fields.Char(string='Receiving Number',
                                   help='Receiving Number',
                                   required=True, readonly=False,
                                   related='partner_id.mobile')
    template_id = fields.Many2one('twilio.sms.template',
                                  string='Select Template',
                                  help='Message Template')
    text_message = fields.Text(string='Message', help='Message Content',
                               required=True, related='template_id.content',
                               readonly=False)
    account_id = fields.Many2one('twilio.account',
                                 string='Twilio Account', help='Choose the '
                                                               'Twilio '
                                                               'account',
                                 required=True)

    def action_confirm_sms(self):
        """Send sms to the corresponding user by using the twilio connection"""
        active_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        try:
            client = Client(self.account_id.account_sid,
                            self.account_id.auth_token)
            message = client.messages.create(
                body=self.text_message,
                from_=self.account_id.from_number,
                to=self.receiving_number
            )
            if message.sid:
                message_data = _("Message Sent!")
                type_data = 'success'
                _logger.info("SMS sent successfully via Twilio with SID: %s", message.sid)
                active_id.message_post(
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
                    "res_model": self._context.get('active_model'),
                    "res_id": self._context.get('active_id'),
                }
                log_message = self.env['twilio.message.log'].sudo().create(msg_dict)
            else:
                message_data = _("Message Not Sent!")
                type_data = 'warning'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message_data,
                    'type': type_data,
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.act_window_close'
                    },
                }
            }
        except TwilioException:
            message_data = _("Message Not Sent!")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message_data,
                    'type': 'warning',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.act_window_close'
                    },
                }
            }
