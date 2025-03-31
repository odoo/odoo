# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    user_id = fields.Many2one(copy=False)
    employee_id = fields.One2many('hr.employee', 'resource_id', check_company=True, context={'active_test': False})

    job_title = fields.Char(related='employee_id.job_title')
    department_id = fields.Many2one(related='employee_id.department_id')
    work_email = fields.Char(related='employee_id.work_email')
    work_phone = fields.Char(related='employee_id.work_phone')
    show_hr_icon_display = fields.Boolean(related='employee_id.show_hr_icon_display')
    hr_icon_display = fields.Selection(related='employee_id.hr_icon_display')

    @api.depends('employee_id')
    def _compute_avatar_128(self):
        is_hr_user = self.env.user.has_group('hr.group_hr_user')
        if not is_hr_user:
            public_employees = self.env['hr.employee.public'].with_context(active_test=False).search([
                ('resource_id', 'in', self.ids),
            ])
            avatar_per_employee_id = {emp.id: emp.avatar_128 for emp in public_employees}

        for resource in self:
            employee = resource.employee_id
            if not employee:
                resource.avatar_128 = False
                continue
            if is_hr_user:
                resource.avatar_128 = employee[0].avatar_128
            else:
                resource.avatar_128 = avatar_per_employee_id[employee[0].id]
