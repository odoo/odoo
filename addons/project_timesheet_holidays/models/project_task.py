# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL


class ProjectTask(models.Model):
    _inherit = 'project.task'

    leave_types_count = fields.Integer(compute='_compute_leave_types_count', string="Time Types Count")
    is_timeoff_task = fields.Boolean("Is Time off Task", compute="_compute_is_timeoff_task", search="_search_is_timeoff_task", export_string_translation=False, groups="hr_timesheet.group_hr_timesheet_user")

    def _compute_leave_types_count(self):
        timesheet_read_group = self.env['account.analytic.line']._read_group(
            [('task_id', 'in', self.ids), '|', ('holiday_id', '!=', False), ('global_leave_id', '!=', False)],
            ['task_id'],
            ['__count'],
        )
        timesheet_count_per_task = {timesheet_task.id: count for timesheet_task, count in timesheet_read_group}
        for task in self:
            task.leave_types_count = timesheet_count_per_task.get(task.id, 0)

    @api.depends_context('allowed_company_ids')
    def _compute_is_timeoff_task(self):
        timeoff_tasks = self & self.env.companies.leave_timesheet_task_id
        timeoff_tasks.is_timeoff_task = True
        (self - timeoff_tasks).is_timeoff_task = False

    def _search_is_timeoff_task(self, operator, value):
        if operator != 'in':
            return NotImplemented

<<<<<<< 466c1f11fb0d4c9ea315ac324712087a92c9aa26
        timeoff_tasks_ids = {row[0] for row in self.env.execute_query(
            self.env['account.analytic.line']._search(
                [('task_id', '!=', False), '|', ('holiday_id', '!=', False), ('global_leave_id', '!=', False)],
            ).select(SQL('DISTINCT task_id'))
        )}

        if self.env.company.leave_timesheet_task_id:
            timeoff_tasks_ids.add(self.env.company.leave_timesheet_task_id.id)

        return Domain('id', 'in', tuple(timeoff_tasks_ids))
||||||| 9db68e615a72514a8673eb6dd06cb95ff857eda8
        timeoff_tasks_ids = {row[0] for row in self.env.execute_query(
            self.env['account.analytic.line']._search(
                [('task_id', '!=', False), '|', ('holiday_id', '!=', False), ('global_leave_id', '!=', False)],
            ).select('DISTINCT task_id')
        )}

        if self.env.company.leave_timesheet_task_id:
            timeoff_tasks_ids.add(self.env.company.leave_timesheet_task_id.id)

        return Domain('id', 'in', tuple(timeoff_tasks_ids))
=======
        return Domain('id', 'in', self.env.companies.leave_timesheet_task_id.ids)
>>>>>>> 80da40ba86218c555a4df0e1e098352d631e348c
