# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class PlanningAnalysisReport(models.Model):
    _inherit = "planning.analysis.report"

    percentage_hours = fields.Float("Progress (%)", readonly=True, aggregator="avg", groups="hr_timesheet.group_hr_timesheet_approver")
    effective_hours = fields.Float("Effective Time", readonly=True, groups="hr_timesheet.group_hr_timesheet_approver",
        help="Number of time recorded on the employee's Timesheets for this task (and its sub-tasks) during the timeframe of the shift.")
    remaining_hours = fields.Float("Time Remaining", readonly=True, groups="hr_timesheet.group_hr_timesheet_approver",
        help="Allocated time minus the effective time.")
    allocated_hours_cost = fields.Float("Allocated Time Cost", readonly=True, groups="hr.group_hr_user")
    effective_hours_cost = fields.Float("Effective Time Cost", readonly=True, groups="hr.group_hr_user")

    @api.model
    def _select(self):
        return super()._select() + """,
            S.effective_hours AS effective_hours,
            S.percentage_hours AS percentage_hours,
            (S.allocated_hours - S.effective_hours) AS remaining_hours,
            S.allocated_hours * E.hourly_cost AS allocated_hours_cost,
            S.effective_hours * E.hourly_cost AS effective_hours_cost
        """

    @api.model
    def _group_by(self):
        return super()._group_by() + """,
            S.effective_hours, S.allocated_hours, E.hourly_cost
        """
