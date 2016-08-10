# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.osv import fields, osv


class ReportProjectTaskUser(osv.Model):
    _inherit = "report.project.task.user"
    _columns = {
        'hours_planned': fields.float('Planned Hours', readonly=True),
        'hours_effective': fields.float('Effective Hours', readonly=True),
        'hours_delay': fields.float('Avg. Plan.-Eff.', readonly=True),
        'remaining_hours': fields.float('Remaining Hours', readonly=True),
        'progress': fields.float('Progress', readonly=True, group_operator='avg'),
        'total_hours': fields.float('Total Hours', readonly=True),
    }

    def _select(self):
        return super(ReportProjectTaskUser, self)._select() + ", progress as progress, t.effective_hours as hours_effective, remaining_hours as remaining_hours, total_hours as total_hours, t.delay_hours as hours_delay, planned_hours as hours_planned"

    def _group_by(self):
        return super(ReportProjectTaskUser, self)._group_by() + ", remaining_hours, t.effective_hours, progress, total_hours, planned_hours, hours_delay"
