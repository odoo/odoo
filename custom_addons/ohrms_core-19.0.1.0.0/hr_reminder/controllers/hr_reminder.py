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
from datetime import timedelta
from odoo import fields, http
from odoo.http import request


class Reminders(http.Controller):

    @http.route('/hr_reminder/all_reminder', type='json', auth="public")
    def all_reminder(self):
        """Returns the records of the all reminders in the
        model HR Reminder."""
        reminders = []
        for reminder in request.env['hr.reminder'].search([]):
            if reminder.search_by == 'today':
                reminders.append({
                    'id': reminder.id,
                    'name': reminder.name
                })
            elif reminder.search_by == 'set_period':
                if (fields.Date.today() >=
                        reminder.date_from and fields.Date.today()
                        <= reminder.date_to and (
                                not reminder.expiry_date or fields.Date.today()
                                <= reminder.expiry_date)):
                    reminders.append({
                        'id': reminder.id,
                        'name': reminder.name
                    })
            else:
                if fields.Date.today() >= reminder.date_set - timedelta(
                        days=reminder.days_before) and (
                        not reminder.expiry_date or fields.Date.today()
                        <= reminder.expiry_date):
                    reminders.append({
                        'id': reminder.id,
                        'name': reminder.name
                    })
        return reminders

    @http.route('/hr_reminder/reminder_active', type='json', auth="public")
    def reminder_active(self, **kwargs):
        """Returns the current reminder when clicked in
        view button in the systray."""
        value = []
        for reminder in request.env['hr.reminder'].sudo().search([
            ('name', '=', kwargs.get('reminder_name'))]):
            value.append(reminder.model_id.model)
            value.append(reminder.field_id.name)
            value.append(reminder.search_by)
            value.append(reminder.date_set)
            value.append(reminder.date_from)
            value.append(reminder.date_to)
            value.append(reminder.id)
            value.append(fields.Date.today())
            value.append(reminder.field_id.ttype)
            value.append(reminder.days_before)
            if reminder.date_set:
                value.append(reminder.date_set - timedelta(
                    days=reminder.days_before))
        return value
