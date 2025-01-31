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
from odoo import models, _
from twilio.rest import Client
from datetime import datetime,timedelta
from pytz import timezone
import logging

_logger = logging.getLogger(__name__)


class ResCompanyInherited(models.Model):
    _inherit = "res.company"

    def get_list_of_messages_last_time(self):
        # Fetch the Twilio account details
        twilio_account = self.env['twilio.account'].sudo().search([], limit=1)
        if twilio_account:
            # Calculate the timestamp 10 minutes ago
            utc_now = datetime.now(timezone('UTC'))
            last_datetime = utc_now - timedelta(minutes=10)

            # Twilio client initialization
            client = Client(twilio_account.account_sid, twilio_account.auth_token)
            try:
                # Fetch messages sent after the specified date
                messages = client.messages.list(date_sent_after=last_datetime)
                for record in messages:
                    if record.direction == 'inbound':
                        active_id = self.env['res.partner'].sudo().search([('phone', '=', record.from_)], limit=1)
                        if active_id:
                            lead_id = self.env['crm.lead'].search([('partner_id','=',active_id.id),
                                                                   ('type','=','opportunity')],
                                                                   limit=1, order="write_date DESC")
                            lead_id.message_post(
                                body=f"Reply from {active_id.name}: {record.body}",
                                message_type="notification",
                                subtype_xmlid="mail.mt_note",
                            )
                            msg_dict = {
                                "account_sid": record.account_sid,
                                "body": record.body,
                                "date_sent": datetime.now(),
                                "direction": record.direction,
                                "error_code": record.error_code,
                                "error_message": record.error_message,
                                "from_phone": record.from_,
                                "messaging_service_sid": record.messaging_service_sid,
                                "sid": record.sid,
                                "status": record.status,
                                "to_phone": record.to,
                                "uri": record.uri,
                                "res_model": 'crm.lead',
                                "res_id": str(lead_id.id),
                                "res_name": lead_id and lead_id.name or False,
                                "user_id": lead_id.user_id and lead_id.user_id.id or False,
                                "company_id": lead_id.company_id and lead_id.company_id.id or False,
                            }
                            log_message = self.env['twilio.message.log'].sudo().create(msg_dict)
                            _logger.info("Twilio SMS Reply - Pipeline (%s, %s) >> Log %s" %(str(lead_id.id), lead_id.name, log_message.id))
                        # else:
                        #     last_sent_message_log_id = self.env['twilio.message.log'].sudo().search([('to_phone', '=', record.from_)],
                        #                                                                             order='date_sent desc',
                        #                                                                             limit=1)
                        #     if last_sent_message_log_id and last_sent_message_log_id.res_model and last_sent_message_log_id.res_id:
                        #         active_id = self.env[last_sent_message_log_id.res_model].sudo().browse(int(last_sent_message_log_id.res_id))
                        #         active_id.message_post(
                        #             body=f"Reply from {record.from_}: {record.body}",
                        #             message_type="notification",
                        #             subtype_xmlid="mail.mt_note",
                        #         )
                        #         msg_dict = {
                        #             "account_sid": record.account_sid,
                        #             "body": record.body,
                        #             "date_sent": datetime.now(),
                        #             "direction": record.direction,
                        #             "error_code": record.error_code,
                        #             "error_message": record.error_message,
                        #             "from_phone": record.from_,
                        #             "messaging_service_sid": record.messaging_service_sid,
                        #             "sid": record.sid,
                        #             "status": record.status,
                        #             "to_phone": record.to,
                        #             "uri": record.uri,
                        #             "res_model": last_sent_message_log_id.res_model,
                        #             "res_id": last_sent_message_log_id.res_id,
                        #         }
                        #         log_message = self.env['twilio.message.log'].sudo().create(msg_dict)
                _logger.info("Message List: %s", [str(msg) for msg in messages])
            except Exception as e:
                _logger.error("Error fetching Twilio messages: %s", str(e))
        else:
            _logger.warning("No Twilio account configured.")

