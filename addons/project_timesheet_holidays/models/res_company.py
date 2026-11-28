# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    leave_timesheet_task_id = fields.Many2one(
        'project.task', string="Time Off Task",
        domain="[('project_id', '=', internal_project_id)]")

    def write(self, vals):
        if 'leave_timesheet_task_id' not in vals:
            return super().write(vals)
        old_timeoff_tasks = self.leave_timesheet_task_id
        res = super().write(vals)
        new_timeoff_tasks = self.leave_timesheet_task_id.sudo()
        (old_timeoff_tasks | new_timeoff_tasks).invalidate_recordset(['is_timeoff_task'])
        new_timeoff_tasks.remaining_hours = 0.0
        # the tasks no longer used as time off task get back their real remaining hours
        released_tasks = (old_timeoff_tasks - new_timeoff_tasks).sudo()
        self.env.add_to_compute(released_tasks._fields['remaining_hours'], released_tasks)
        return res

    def _create_internal_project_task(self):
        projects = super()._create_internal_project_task()
        for project in projects:
            company = project.company_id
            company = company.with_company(company)
            if not company.leave_timesheet_task_id:
                task = company.env['project.task'].sudo().create({
                    'name': _('Time Off'),
                    'project_id': company.internal_project_id.id,
                    'active': True,
                    'company_id': company.id,
                })
                company.write({
                    'leave_timesheet_task_id': task.id,
                })
        return projects
