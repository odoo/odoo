# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ReportProjectTaskUser(models.Model):
    _inherit = "report.project.task.user"

    hours_planned = fields.Float('Planned Hours', readonly=True)
    hours_effective = fields.Float('Effective Hours', readonly=True)
    hours_delay = fields.Float('Avg. Plan.-Eff.', readonly=True)
    remaining_hours = fields.Float('Remaining Hours', readonly=True)
    progress = fields.Float('Progress', group_operator='avg', readonly=True)
    total_hours = fields.Float('Total Hours', readonly=True)

    def _select(self):
        return super(ReportProjectTaskUser, self)._select() + """,
            progress as progress,
            t.effective_hours as hours_effective,
            remaining_hours as remaining_hours,
            total_hours as total_hours,
            t.delay_hours as hours_delay,
            planned_hours as hours_planned"""

    def _group_by(self):
        return super(ReportProjectTaskUser, self)._group_by() + """,
            remaining_hours,
            t.effective_hours,
            progress,
            total_hours,
            planned_hours,
            hours_delay"""
