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
                messages = client.messages.list(limit=20, date_sent_after=last_datetime)
                _logger.info("Message List: %s", [str(msg) for msg in messages])  # Log message SIDs
            except Exception as e:
                _logger.error("Error fetching Twilio messages: %s", str(e))
        else:
            _logger.warning("No Twilio account configured.")

