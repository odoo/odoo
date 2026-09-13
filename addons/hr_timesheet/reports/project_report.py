from odoo import fields, models


class ReportProjectTaskUser(models.Model):
    _inherit = "report.project.task.user"

    allocated_hours = fields.Float(
        string="Allocated Time",
        readonly=True,
        groups="hr_timesheet.group_hr_timesheet_user",
    )
    effective_hours = fields.Float(
        string="Time Spent",
        readonly=True,
        groups="hr_timesheet.group_hr_timesheet_user",
    )
    remaining_hours = fields.Float(
        string="Time Remaining",
        readonly=True,
        groups="hr_timesheet.group_hr_timesheet_user",
    )
    remaining_hours_percentage = fields.Float(
        string="Time Remaining Percentage",
        readonly=True,
        groups="hr_timesheet.group_hr_timesheet_user",
    )
    progress = fields.Float(
        readonly=True,
        aggregator="avg",
        groups="hr_timesheet.group_hr_timesheet_user",
    )
    overtime = fields.Float(
        readonly=True,
        groups="hr_timesheet.group_hr_timesheet_user",
    )

    def _select(self):
        return (
            super()._select()
            + """,
                CASE WHEN COALESCE(t.planned_hours, 0) = 0 THEN NULL ELSE t.effective_hours * 100 / t.planned_hours END as progress,
                NULLIF(t.effective_hours, 0) as effective_hours,
                CASE WHEN COALESCE(t.planned_hours, 0) = 0 THEN NULL ELSE t.planned_hours - t.effective_hours END as remaining_hours,
                CASE WHEN t.planned_hours > 0 THEN t.remaining_hours / t.planned_hours ELSE 0 END as remaining_hours_percentage,
                NULLIF(t.allocated_hours, 0) as allocated_hours,
                NULLIF(t.overtime, 0) as overtime
        """
        )

    def _group_by(self):
        return (
            super()._group_by()
            + """,
                t.effective_hours,
                t.allocated_hours,
                t.planned_hours,
                t.remaining_hours,
                t.overtime
        """
        )
