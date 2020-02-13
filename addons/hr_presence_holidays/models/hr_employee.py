# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Employee(models.AbstractModel):
    _inherit = 'hr.employee.base'

    def _compute_presence_state(self):
        super()._compute_presence_state()
        employees = self.filtered(lambda employee: employee.is_absent and employee.hr_presence_state != 'absent')
        employees.update({'hr_presence_state': 'absent'})

    def action_open_leave_request(self):
        self.ensure_one()
        action = self.env.ref('hr_holidays.action_hr_holidays_dashboard').read()[0]
        action['context'] = {
            'search_default_employee_id': self.id,
            'default_employee_id': self.id,
            'time_off_expand_employee': [self.id],
        }
        return action
