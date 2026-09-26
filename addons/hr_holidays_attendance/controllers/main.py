# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import float_round

from odoo.addons.hr_attendance.controllers.main import HrAttendance


class HrHolidaysAttendance(HrAttendance):

    @staticmethod
    def _get_employee_info_response(employee):
        response = super(HrHolidaysAttendance, HrHolidaysAttendance)._get_employee_info_response(employee)

        if not employee:
            return response

        remaining_overtime_data = employee._get_deductible_employee_overtime()
        response['total_overtime'] = float_round(
            remaining_overtime_data.get(employee, 0.0),
            precision_digits=2,
        )
        return response
