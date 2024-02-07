# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ReportProjectTaskUser(models.Model):
    _inherit = "report.project.task.user"

    allocated_hours = fields.Float('Allocated Time', readonly=True)
    effective_hours = fields.Float('Hours Spent', readonly=True)
    remaining_hours = fields.Float('Remaining Hours', readonly=True)
    remaining_hours_percentage = fields.Float('Remaining Hours Percentage', readonly=True)
    progress = fields.Float('Progress', aggregator='avg', readonly=True)
    overtime = fields.Float(readonly=True)
    total_hours_spent = fields.Float("Total Hours Spent", help="Time spent on this task, including its sub-tasks.")
    subtask_effective_hours = fields.Float("Hours Spent on Sub-Tasks", help="Time spent on the sub-tasks (and their own sub-tasks) of this task.")

    def _select(self):
        return super()._select() +  """,
                CASE WHEN COALESCE(t.allocated_hours, 0) = 0 THEN NULL ELSE t.effective_hours * 100 / t.allocated_hours END as progress,
                NULLIF(t.effective_hours, 0) as effective_hours,
                t.allocated_hours - t.effective_hours - t.subtask_effective_hours as remaining_hours,
                CASE WHEN t.allocated_hours > 0 THEN t.remaining_hours / t.allocated_hours ELSE 0 END as remaining_hours_percentage,
                t.allocated_hours,
                NULLIF(t.overtime, 0) as overtime,
                NULLIF(t.total_hours_spent, 0) as total_hours_spent,
                t.subtask_effective_hours
        """

    def _group_by(self):
        return super()._group_by() + """,
                t.effective_hours,
                t.subtask_effective_hours,
                t.allocated_hours,
                t.overtime,
                t.total_hours_spent
        """

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """The override of _get_view changing the time field labels according to the company timesheet encoding UOM
        makes the view cache dependent on the company timesheet encoding uom"""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self.env.company.timesheet_encode_uom_id,)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type in ['pivot', 'graph'] and self.env.company.timesheet_encode_uom_id == self.env.ref('uom.product_uom_day'):
            arch = self.env['account.analytic.line']._apply_time_label(arch, related_model=self._name)
        return arch, view
