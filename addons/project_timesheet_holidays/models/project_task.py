# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _

class Task(models.Model):
    _inherit = 'project.task'

    leave_types_count = fields.Integer(compute='_compute_leave_types_count', string="Time Off Types Count")
    is_timeoff_task = fields.Boolean("Is Time off Task", compute="_compute_is_timeoff_task", search="_search_is_timeoff_task")

    def _compute_leave_types_count(self):
        time_off_type_read_group = self.env['hr.leave.type']._read_group(
            [('timesheet_task_id', 'in', self.ids)],
            ['timesheet_task_id'],
            ['timesheet_task_id'],
        )
        time_off_type_count_per_task = {res['timesheet_task_id'][0]: res['timesheet_task_id_count'] for res in time_off_type_read_group}
        for task in self:
            task.leave_types_count = time_off_type_count_per_task.get(task.id, 0)

    def _compute_is_timeoff_task(self):
        timeoff_tasks = self.filtered(lambda task: task.leave_types_count or task.company_id.leave_timesheet_task_id == task)
        timeoff_tasks.is_timeoff_task = True
        (self - timeoff_tasks).is_timeoff_task = False

    def _search_is_timeoff_task(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise NotImplementedError(_('Operation not supported'))
        leave_type_read_group = self.env['hr.leave.type']._read_group(
            [('timesheet_task_id', '!=', False)],
            ['timesheet_task_ids:array_agg(timesheet_task_id)'],
            [],
        )
        timeoff_task_ids = leave_type_read_group[0]['timesheet_task_ids'] if leave_type_read_group else []
        if self.env.company.leave_timesheet_task_id:
            timeoff_task_ids.append(self.env.company.leave_timesheet_task_id.id)
        if operator == '!=':
            value = not value
        return [('id', 'in' if value else 'not in', timeoff_task_ids)]
