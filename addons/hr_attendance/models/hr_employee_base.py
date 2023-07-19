# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    @api.depends("user_id.im_status", "attendance_state")
    def _compute_presence_state(self):
        """
        Override to include checkin/checkout in the presence state
        Attendance has the second highest priority after login
        """
        super()._compute_presence_state()
        employees = self.filtered(lambda e: e.hr_presence_state != "present")
        employee_to_check_working = self.filtered(lambda e: e.attendance_state == "checked_out"
                                                            and e.hr_presence_state == "to_define")
        working_now_list = employee_to_check_working._get_employee_working_now()
        for employee in employees:
            if employee.attendance_state == "checked_out" and employee.hr_presence_state == "to_define" and \
                    employee.id in working_now_list:
                employee.hr_presence_state = "absent"
            elif employee.attendance_state == "checked_in":
                employee.hr_presence_state = "present"

    def _compute_presence_icon(self):
        res = super()._compute_presence_icon()
        # All employee must chek in or check out. Everybody must have an icon
        self.filtered(lambda employee: not employee.show_hr_icon_display).show_hr_icon_display = True
        return res
