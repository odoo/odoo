# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    @api.depends("user_id.im_status", "hr_presence_state_display")
    def _compute_presence_state(self):
        super()._compute_presence_state()
        company = self.env.company
        working_now_list = self._get_employee_working_now()
        for employee in self:
            if employee.manually_set_presence:
                employee.hr_presence_state = employee.hr_presence_state_display
                continue

            if not employee.company_id.hr_presence_control_email and not employee.company_id.hr_presence_control_ip:
                continue
            if company.hr_presence_last_compute_date and employee.id in working_now_list and \
                    company.hr_presence_last_compute_date.day == fields.Datetime.now().day and \
                    (employee.email_sent or employee.ip_connected or employee.manually_set_present):
                employee.hr_presence_state = 'present'
            elif employee.id in working_now_list and employee.is_absent and \
                not (employee.email_sent or employee.ip_connected or employee.manually_set_present):
                employee.hr_presence_state = 'absent'
            else:
                employee.hr_presence_state = 'out_of_working_hour'
