# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    def _compute_presence_state(self):
        super()._compute_presence_state()
        employees = self.filtered(lambda e: e.hr_presence_state != 'present' and not e.is_absent)
        company = self.env.company
        employee_to_check_working = employees.filtered(lambda e:
                                                       not e.is_absent and
                                                       (e.email_sent or e.ip_connected or e.manually_set_present))
        working_now_list = employee_to_check_working._get_employee_working_now()
        for employee in employees:
            if not employee.is_absent and company.hr_presence_last_compute_date and employee.id in working_now_list and \
                    company.hr_presence_last_compute_date.day == fields.Datetime.now().day and \
                    (employee.email_sent or employee.ip_connected or employee.manually_set_present):
                employee.hr_presence_state = 'present'
