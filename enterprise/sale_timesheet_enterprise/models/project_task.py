# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

from odoo.addons.sale_timesheet_enterprise.models.sale import DEFAULT_INVOICED_TIMESHEET


PROJECT_TASK_READABLE_FIELDS_TO_MAP = {
    'remaining_hours': 'portal_remaining_hours',
    'effective_hours': 'portal_effective_hours',
    'total_hours_spent': 'portal_total_hours_spent',
    'subtask_effective_hours': 'portal_subtask_effective_hours',
    'progress': 'portal_progress',
}

class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Project Sharing fields
    portal_remaining_hours = fields.Float(compute='_compute_project_sharing_timesheets', help="Total remaining time, can be re-estimated periodically by the assignee of the task.", export_string_translation=False)
    portal_effective_hours = fields.Float(compute='_compute_project_sharing_timesheets', help="Time spent on this task, excluding its sub-tasks.", export_string_translation=False)
    portal_total_hours_spent = fields.Float(compute='_compute_project_sharing_timesheets', help="Time spent on this task, including its sub-tasks.", export_string_translation=False)
    portal_subtask_effective_hours = fields.Float(compute='_compute_project_sharing_timesheets', help="Time spent on the sub-tasks (and their own sub-tasks) of this task.", export_string_translation=False)
    portal_progress = fields.Float(compute='_compute_project_sharing_timesheets', aggregator="avg", help="Display progress of current task.", export_string_translation=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS | set(PROJECT_TASK_READABLE_FIELDS_TO_MAP.values()) - set(PROJECT_TASK_READABLE_FIELDS_TO_MAP.keys())

    @api.depends('allocated_hours')
    def _compute_project_sharing_timesheets(self):
        subtask_ids_per_task_id = self.sudo().with_context(active_test=False)._get_subtask_ids_per_task_id()
        # Say `self.ids` is [1, 2, 3] and `_get_subtask_ids_per_task_id()` returns {1: [2, 4], 2: [4], 3: []}.
        # We want to merge all subtask ids and add `self.ids` to it.
        # Unpacking `subtask_ids_per_task_id` values in `set.union` seems to be the appropriate method:
        # >>> set.union({}, [2, 4], [4], [], [1, 2, 3]) = {2, 4, 1, 3}
        all_task_ids = set.union(set(), *subtask_ids_per_task_id.values(), self.ids)
        timesheet_read_group = self.env['account.analytic.line'].sudo()._read_group(
            [
                ('project_id', '!=', False),
                ('task_id', 'in', list(all_task_ids)),
                ('validated', 'in', [True, self.env['ir.config_parameter'].sudo().get_param('sale.invoiced_timesheet', DEFAULT_INVOICED_TIMESHEET) == 'approved'])
            ],
            ['task_id'],
            ['unit_amount:sum'],
        )
        timesheets_per_task = {task.id: unit_amount_sum for task, unit_amount_sum in timesheet_read_group}
        for task in self:
            progress = 0.0
            effective_hours = timesheets_per_task.get(task.id, 0.0)
            subtask_effective_hours = sum(timesheets_per_task.get(subtask_id, 0.0) for subtask_id in subtask_ids_per_task_id.get(task.id, []))
            total_hours_spent = effective_hours + subtask_effective_hours
            if task.allocated_hours > 0:
                progress = 1 if max(total_hours_spent - task.allocated_hours, 0) else round(total_hours_spent / task.allocated_hours, 2)
            task.portal_remaining_hours = task.allocated_hours - total_hours_spent
            task.portal_effective_hours = effective_hours
            task.portal_subtask_effective_hours = subtask_effective_hours
            task.portal_total_hours_spent = total_hours_spent
            task.portal_progress = progress

    def read(self, fields=None, load='_classic_read'):
        """ Override read method to filter timesheets in the task(s) is the user is portal user
            and the sale.invoiced_timesheet configuration is set to 'approved'
            Then we need to give the id of timesheets which is validated.
        """
        result = super().read(fields=fields, load=load)
        if fields and 'timesheet_ids' in fields and (self.env.user._is_portal() or 'project_sharing_id' in self.env.context):
            # We need to check if configuration
            param_invoiced_timesheet = self.env['ir.config_parameter'].sudo().get_param('sale.invoiced_timesheet', DEFAULT_INVOICED_TIMESHEET)
            if param_invoiced_timesheet == 'approved':
                timesheets_read_group = self.env['account.analytic.line']._read_group(
                    [('task_id', 'in', self.ids), ('validated', '=', True)],
                    ['task_id'],
                    ['id:array_agg'],
                )
                timesheets_dict = {task.id: ids for task, ids in timesheets_read_group}
                for record_read in result:
                    record_read['timesheet_ids'] = timesheets_dict.get(record_read['id'], [])
        return result

    def _gantt_progress_bar_sale_line_id(self, res_ids):
        if not self.env['sale.order.line'].has_access('read'):
            return {}
        uom_hour = self.env.ref('uom.product_uom_hour')
        planned_hours_per_sol = self.env['project.task']._read_group([
            ('sale_line_id', 'in', res_ids),
        ], ['sale_line_id'], ['planned_hours:sum'])
        planned_hours_per_sol_mapped = {
            sale_line.id: planned_hours_sum
            for sale_line, planned_hours_sum in planned_hours_per_sol
        }
        return {
            sol.id: {
                'value': planned_hours_per_sol_mapped.get(sol.id, 0.0),
                'max_value': sol.product_uom._compute_quantity(sol.product_uom_qty, uom_hour),
            }
            for sol in self.env['sale.order.line'].search([('id', 'in', res_ids)])
        }

    def _gantt_progress_bar(self, field, res_ids, start, stop):
        if field == 'sale_line_id':
            return dict(
                self._gantt_progress_bar_sale_line_id(res_ids),
                warning=_("This Sale Order Item doesn't have a target value of planned hours.")
            )
        return super()._gantt_progress_bar(field, res_ids, start, stop)
