# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    l10n_fr_date_to_changed = fields.Boolean()

    def _get_fr_date_to(self, vals):
        # The french date_to is meant to be computed only in very specific cases:
        # - there is only one employee affected by the leave
        # - the employee company is french
        # - the leave_type is the reference leave_type of that company
        # If any of those condition is not filled, the initial date_to is returned
        if 'employee_id' not in vals and not len(self) == 1:
            return vals['date_to']
        employee = self.env['hr.employee'].browse(vals['employee_id']).sudo() if 'employee_id' in vals else self.employee_id
        employee_calendar = employee.resource_calendar_id
        company_calendar = employee.company_id.resource_calendar_id
        leave_type_id = vals['holiday_status_id'] if 'holiday_status_id' in vals else self.holiday_status_id.id
        if employee.company_id.country_id.code == 'FR' and employee_calendar != company_calendar and leave_type_id:
            reference_leave_type = employee.company_id._get_fr_reference_leave_type()
            if reference_leave_type.id == leave_type_id:
                return self._get_fr_new_date_to(vals['date_to'], employee_calendar, company_calendar)
        return vals['date_to']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['date_to'] = self._get_fr_date_to(vals)
        return super().create(vals_list)

    def write(self, vals):
        if 'date_to' not in vals:
            return super().write(vals)
        if 'employee_id' in vals:
            vals['date_to'] = self._get_fr_date_to(vals)
            return super().write(vals)
        else:
            # Different employees could share different calendars
            for leave in self:
                vals_copy = vals.copy()
                vals_copy['date_to'] = leave._get_fr_date_to(vals_copy)
                super(HrLeave, leave).write(vals_copy)

    def _get_fr_new_date_to(self, date_to, employee_calendar, company_calendar):
        date_target = date_to
        if isinstance(date_to, str):
            date_target = datetime.fromisoformat(date_to)
        new_date_to = date_target
        date_target += relativedelta(days=1)
        while not employee_calendar._works_on_date(date_target):
            if company_calendar._works_on_date(date_target):
                new_date_to = date_target
            date_target += relativedelta(days=1)

        return new_date_to

    def _get_fr_number_of_days(self, employee, date_from, date_to, employee_calendar, company_calendar):
        self.ensure_one()

        self.l10n_fr_date_to_changed = False
        # We can fill the holes using the company calendar as default
        # What we need to compute is how much we will need to push date_to in order to account for the lost days
        # This gets even more complicated in two_weeks_calendars

        if self.request_unit_half and self.request_date_from_period == 'am':
            # In normal workflows request_unit_half implies that date_from and date_to are the same
            # request_unit_half allows us to choose between `am` and `pm`
            # In a case where we work from mon-wed and request a half day in the morning
            # we do not want to push date_to since the next work attendance is actually in the afternoon
            date_from_weektype = str(self.env['resource.calendar.attendance'].get_week_type(date_from))
            date_from_dayofweek = str(date_from.weekday())
            # Fetch the attendances we care about
            attendance_ids = employee_calendar.attendance_ids.filtered(lambda a:
                a.dayofweek == date_from_dayofweek
                and a.day_period != "lunch"
                and (not employee_calendar.two_weeks_calendar or a.week_type == date_from_weektype))
            if len(attendance_ids) == 2:
                # The employee took the morning off on a day where he works the afternoon aswell
                attendance = attendance_ids[0] if attendance_ids[0].day_period == 'morning' else attendance_ids[1]
                return {'days': 0.5, 'hours': attendance.hour_to - attendance.hour_from}
        # Check calendars for working days until we find the right target, start at date_to + 1 day
        # Postpone date_target until the next working day
        date_start = date_from
        date_target = date_to + relativedelta(days=1)
        counter = 0
        while not employee_calendar._works_on_date(date_start):
            date_start += relativedelta(days=1)
        while not employee_calendar._works_on_date(date_target):
            date_target += relativedelta(days=1)
            counter += 1
            # Allow up to 14 days for two weeks calendars to avoid infinite loop.
            if counter > 14:
                # Default behaviour
                result = employee._get_work_days_data_batch(date_start, date_to, calendar=employee_calendar)[employee.id]
                if self.request_unit_half and result['hours'] > 0:
                    result['days'] = 0.5
                return result
        date_target = datetime.combine(date_target.date(), datetime.min.time())
        self.l10n_fr_date_to_changed = True
        return employee._get_work_days_data_batch(date_start, date_target, calendar=company_calendar)[employee.id]

    def _get_number_of_days(self, date_from, date_to, employee):
        """
        In french time off laws, if an employee has a part time contract, when taking time off
        before one of his off day (compared to the company's calendar) it should also count the time
        between the time off and the next calendar work day/company off day (weekends).

        For example take an employee working mon-wed in a company where the regular calendar is mon-fri.
        If the employee were to take a time off ending on wednesday, the legal duration would count until friday.

        Returns a dict containing two keys: 'days' and 'hours' with the value being the duration for the requested time period.
        """
        basic_amount = super()._get_number_of_days(date_from, date_to, employee)

        if not employee or not (basic_amount['days'] or basic_amount['hours']):
            return basic_amount
        employee = employee.sudo()
        company = employee.company_id
        if company.country_id.code != 'FR' or not company.resource_calendar_id:
            return basic_amount
        calendar = self._get_calendar()
        if not calendar or not calendar != company.resource_calendar_id:
            return basic_amount
        if self.holiday_status_id != employee.company_id._get_fr_reference_leave_type():
            return basic_amount

        return self._get_fr_number_of_days(employee, date_from, date_to, calendar, company.resource_calendar_id)
