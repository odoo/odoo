# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Datetime

_logger = logging.getLogger(__name__)


class Employee(models.Model):
    _inherit = 'hr.employee'

    def _action_open_presence_view(self):
        action = super(Employee, self)._action_open_presence_view()

        if self.env['ir.config_parameter'].sudo().get_param('hr_presence.hr_presence_control_attendance'):
            company = self.env.user.company_id
            employees = self.env['hr.employee'].search([
                ('department_id.company_id', '=', company.id),
                ('user_id', '!=', False),
            ])

            employees.filtered(
                lambda e: e.attendance_state == 'checked_in'
            ).write({'hr_presence_state': 'present'})

            employees.filtered(
                lambda e: e.attendance_state == 'checked_out'
            ).write({'hr_presence_state': 'absent'})

        return action
