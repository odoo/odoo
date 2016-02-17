# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp.osv import fields,osv
from openerp import tools

class report_project_task_user(osv.Model):
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
        return  super(report_project_task_user, self)._select() + ", progress as progress, t.effective_hours as hours_effective, remaining_hours as remaining_hours, total_hours as total_hours, t.delay_hours as hours_delay, planned_hours as hours_planned"

    def _group_by(self):
        return super(report_project_task_user, self)._group_by() + ", remaining_hours, t.effective_hours, progress, total_hours, planned_hours, hours_delay"
