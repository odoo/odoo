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
