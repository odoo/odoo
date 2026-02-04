# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz

from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    current_leave_id = fields.Many2one('hr.leave.type', compute='_compute_current_leave', string="Current Time Off Type",
                                       groups="hr.group_hr_user")

    def _compute_current_leave(self):
        self.current_leave_id = False

        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', 'in', self.ids),
            ('date_from', '<=', fields.Datetime.now()),
            ('date_to', '>=', fields.Datetime.now()),
            ('state', '=', 'validate'),
        ])
        for holiday in holidays:
            employee = self.filtered(lambda e: e.id == holiday.employee_id.id)
            employee.current_leave_id = holiday.holiday_status_id.id

    def _get_user_m2o_to_empty_on_archived_employees(self):
        return super()._get_user_m2o_to_empty_on_archived_employees() + ['leave_manager_id']

    def action_time_off_dashboard(self):
        return {
            'name': _('Time Off Dashboard'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave',
            'views': [[self.env.ref('hr_holidays.hr_leave_employee_view_dashboard').id, 'calendar']],
            'domain': [('employee_id', 'in', self.ids)],
            'context': {
                'employee_id': self.ids,
            },
        }

    def _is_leave_user(self):
        return self == self.env.user.employee_id and self.user_has_groups('hr_holidays.group_hr_holidays_user')

    def get_mandatory_days(self, start_date, end_date):
        all_days = {}

        self = self or self.env.user.employee_id

        mandatory_days = self._get_mandatory_days(start_date, end_date)
        for mandatory_day in mandatory_days:
            num_days = (mandatory_day.end_date - mandatory_day.start_date).days
            for d in range(num_days + 1):
                all_days[str(mandatory_day.start_date + relativedelta(days=d))] = mandatory_day.color

        return all_days

    @api.model
    def get_special_days_data(self, date_start, date_end):
        return {
            'mandatoryDays': self.get_mandatory_days_data(date_start, date_end),
            'bankHolidays': self.get_public_holidays_data(date_start, date_end),
        }

    @api.model
    def get_public_holidays_data(self, date_start, date_end):
        self = self._get_contextual_employee()
        employee_tz = pytz.timezone(self._get_tz() if self else self.env.user.tz or 'utc')
        public_holidays = self._get_public_holidays(date_start, date_end).sorted('date_from')
        return list(map(lambda bh: {
            'id': -bh.id,
            'colorIndex': 0,
            'end': datetime.combine(bh.date_to.astimezone(employee_tz), datetime.max.time()).isoformat(),
            'endType': "datetime",
            'isAllDay': True,
            'start': datetime.combine(bh.date_from.astimezone(employee_tz), datetime.min.time()).isoformat(),
            'startType': "datetime",
            'title': bh.name,
        }, public_holidays))

    def _get_public_holidays(self, date_start, date_end):
        domain = [
            ('resource_id', '=', False),
            ('company_id', 'in', self.env.companies.ids),
            ('date_from', '<=', date_end),
            ('date_to', '>=', date_start),
            '|',
            ('calendar_id', '=', False),
            ('calendar_id', '=', self.resource_calendar_id.id),
        ]

        return self.env['resource.calendar.leaves'].search(domain)

    @api.model
    def get_mandatory_days_data(self, date_start, date_end):
        self = self._get_contextual_employee()
        mandatory_days = self._get_mandatory_days(date_start, date_end).sorted('start_date')
        return list(map(lambda sd: {
            'id': -sd.id,
            'colorIndex': sd.color,
            'end': datetime.combine(sd.end_date, datetime.max.time()).isoformat(),
            'endType': "datetime",
            'isAllDay': True,
            'start': datetime.combine(sd.start_date, datetime.min.time()).isoformat(),
            'startType': "datetime",
            'title': sd.name,
        }, mandatory_days))

    def _get_mandatory_days(self, start_date, end_date):
        domain = [
            ('start_date', '<=', end_date),
            ('end_date', '>=', start_date),
            ('company_id', 'in', self.env.companies.ids),
            '|',
            ('resource_calendar_id', '=', False),
            ('resource_calendar_id', '=', self.resource_calendar_id.id),
        ]

        if self.department_id:
            department_ids = self.department_id.ids
            domain += [
                '|',
                ('department_ids', '=', False),
                ('department_ids', 'parent_of', department_ids),
            ]
        else:
            domain += [('department_ids', '=', False)]

        return self.env['hr.leave.mandatory.day'].search(domain)
