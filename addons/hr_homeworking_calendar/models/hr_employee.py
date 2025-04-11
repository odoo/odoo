# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from odoo.addons.hr_homeworking.models.hr_homeworking import DAYS


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _get_worklocation(self, start_date, end_date):
        work_locations_by_employee = defaultdict(dict)
        for employee in self:
            work_locations_by_employee[employee.id].update({
                "user_id": employee.user_id.id,
                "employee_id": employee.id,
                "partner_id": employee.user_partner_id.id or employee.work_contact_id.id,
                "employee_name": employee.name
            })

            for day in DAYS:
                work_locations_by_employee[employee.id][day] = {
                    'location_type': employee[day]["location_type"],
                    'location_name': employee[day]["name"],
                    'work_location_id': employee[day].id,
                }

        exceptions_for_period = self.env['hr.employee.location'].search_read([
            ('employee_id', 'in', self.ids),
            ('date', '>=', start_date),
            ('date', '<=', end_date)
        ], ['employee_id', 'date', 'work_location_name', 'work_location_id', 'work_location_type'])

        for exception in exceptions_for_period:
            date = exception["date"].strftime(DEFAULT_SERVER_DATE_FORMAT)
            exception_value = {
                'hr_employee_location_id': exception["id"],
                'location_type': exception['work_location_type'],
                'location_name': exception['work_location_name'],
                'work_location_id': exception['work_location_id'][0],
            }
            employee_id = exception["employee_id"][0]
            if "exceptions" not in work_locations_by_employee[employee_id]:
                work_locations_by_employee[employee_id]["exceptions"] = {}
            work_locations_by_employee[employee_id]["exceptions"][date] = exception_value

        return work_locations_by_employee
