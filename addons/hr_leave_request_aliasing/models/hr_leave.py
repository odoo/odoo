# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import re
from datetime import datetime
from odoo import api, models
from odoo.tools import email_split


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """This function extracts required fields of hr.holidays from incoming
         mail then creating records"""
        if custom_values is None:
            custom_values = {}
        msg_subject = msg_dict.get('subject', '')
        mail_from = msg_dict.get('email_from', '')
        subject = re.search(self.env['ir.config_parameter'].sudo(
        ).get_param('hr_holidays.alias_prefix'), msg_subject)
        from_mail = re.search(self.env['ir.config_parameter'].sudo(
        ).get_param('hr_holidays.alias_domain'), mail_from)
        if subject and from_mail:
            email_address = email_split(msg_dict.get('email_from', False))[
                0]
            employee = self.env['hr.employee'].sudo().search(
                ['|', ('work_email', 'ilike', email_address),
                 ('user_id.email', 'ilike', email_address)], limit=1)
            msg_body = msg_dict.get('body', '')
            cleaner = re.compile('<.*?>')
            clean_msg_body = re.sub(cleaner, '', msg_body)
            date_list = re.findall(r'\d{2}/\d{2}/\d{4}', clean_msg_body)
            if len(date_list) > 0:
                start_date = datetime.strptime(
                    date_list[0], '%d/%m/%Y')
                if len(date_list) == 1:
                    date_to = start_date
                else:
                    date_to = datetime.strptime(
                        date_list[1], '%d/%m/%Y')
                no_of_days_temp = (
                        datetime.strptime(str(date_to),
                                          "%Y-%m-%d %H:%M:%S") -
                        datetime.strptime(str(start_date),
                                          '%Y-%m-%d %H:%M:%S')).days
                leave_type = self.env['hr.leave.type'].search([
                    ('requires_allocation', '=', 'no'),
                    '|',
                    ('company_id', 'in', self.env.user.company_ids.ids),
                    '&',
                    ('company_id', '=', False),
                    ('country_id', 'in', self.env.companies.country_id.ids + [False])
                ], limit=1)
                custom_values.update({
                    'name': msg_subject.strip(),
                    'employee_id': employee.id,
                    'holiday_status_id': leave_type.id,
                    'request_date_from': start_date,
                    'request_date_to': date_to,
                    'duration_display': no_of_days_temp + 1
                })
        return super().message_new(msg_dict, custom_values)
