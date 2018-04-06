# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ReportProjectTaskUser(models.Model):
    _inherit = "report.project.task.user"

    hours_planned = fields.Float('Planned Hours', readonly=True)
    hours_effective = fields.Float('Effective Hours', readonly=True)
    remaining_hours = fields.Float('Remaining Hours', readonly=True)
    progress = fields.Float('Progress', group_operator='avg', readonly=True)

    def _select(self):
        return super(ReportProjectTaskUser, self)._select() + """,
            progress as progress,
            t.effective_hours as hours_effective,
            t.planned_hours - t.effective_hours - t.subtask_effective_hours as remaining_hours,
            planned_hours as hours_planned"""

    def _group_by(self):
        return super(ReportProjectTaskUser, self)._group_by() + """,
            remaining_hours,
            t.effective_hours,
            progress,
            planned_hours
            """
