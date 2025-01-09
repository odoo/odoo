# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ReportProjectTaskUser(models.Model):
    _inherit = "report.project.task.user"

    allocated_hours = fields.Float('Allocated Time', readonly=True, groups="hr_timesheet.group_hr_timesheet_user")
    effective_hours = fields.Float('Time Spent', readonly=True, groups="hr_timesheet.group_hr_timesheet_user")
    remaining_hours = fields.Float('Time Remaining', readonly=True, groups="hr_timesheet.group_hr_timesheet_user")
    remaining_hours_percentage = fields.Float('Time Remaining Percentage', readonly=True, groups="hr_timesheet.group_hr_timesheet_user")
    progress = fields.Float('Progress', aggregator='avg', readonly=True, groups="hr_timesheet.group_hr_timesheet_user")
    overtime = fields.Float(readonly=True, groups="hr_timesheet.group_hr_timesheet_user")

    def _select(self):
        return super()._select() + """,
                CASE WHEN COALESCE(t.allocated_hours, 0) = 0 THEN NULL ELSE t.effective_hours * 100 / t.allocated_hours END as progress,
                NULLIF(t.effective_hours, 0) as effective_hours,
                CASE WHEN COALESCE(t.allocated_hours, 0) = 0 THEN NULL ELSE t.allocated_hours - t.effective_hours END as remaining_hours,
                CASE WHEN t.allocated_hours > 0 THEN t.remaining_hours / t.allocated_hours ELSE 0 END as remaining_hours_percentage,
                NULLIF(t.allocated_hours, 0) as allocated_hours,
                NULLIF(t.overtime, 0) as overtime
        """

    def _group_by(self):
        return super()._group_by() + """,
                t.effective_hours,
                t.allocated_hours,
                t.overtime
        """
