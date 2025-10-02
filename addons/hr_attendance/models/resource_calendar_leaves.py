# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta

from odoo import api, models


class CalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    def _get_employee_dates(self):
        # returns the dict for each concerned employees, and fetches all employees concerned in case of a public holiday
        employee_dates = defaultdict(set)
        for leave in self:
            if not leave.resource_id and leave.company_id.hr_attendance_overtime:
                domain = []
                if leave.calendar_id:
                    domain.append(('resource_calendar_id', '=', leave.calendar_id.id))
                if leave.company_id:
                    domain.append(('company_id', '=', leave.company_id.id))
                employees = self.env['hr.employee'].search(domain)
                for emp in employees:
                    for d in range((leave.date_to - leave.date_from).days + 1):
                        employee_dates[emp].add(self.env['hr.attendance']._get_day_start_and_day(emp, leave.date_from + timedelta(days=d)))
            if leave.resource_id.employee_id and leave.company_id.hr_attendance_overtime:
                for d in range((leave.date_to - leave.date_from).days + 1):
                    employee_dates[leave.resource_id.employee_id].add(self.env['hr.attendance']._get_day_start_and_day(leave.resource_id.employee_id, leave.date_from + timedelta(days=d)))
        return employee_dates

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        employee_dates = res._get_employee_dates()
        if employee_dates:
            self.env['hr.attendance'].sudo()._update_overtime(employee_dates)
        return res

    def write(self, vals):
        employee_dates = self._get_employee_dates()
        res = super().write(vals)
        for emp, dates in self._get_employee_dates().items():
            employee_dates[emp].update(dates)
        if employee_dates:
            self.env['hr.attendance'].sudo()._update_overtime(employee_dates)
        return res

    def unlink(self):
        employee_dates = self._get_employee_dates()
        res = super().unlink()
        if employee_dates:
            self.env['hr.attendance'].sudo()._update_overtime(employee_dates)
        return res
