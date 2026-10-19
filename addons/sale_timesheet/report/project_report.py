# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import fields, models
from odoo.tools import SQL


class ReportProjectTaskUser(models.Model):
    _inherit = 'report.project.task.user'

    remaining_hours_so = fields.Float('Time Remaining on SO', readonly=True, groups="hr_timesheet.group_hr_timesheet_user")

    def _select(self):
        return SQL("""%s,
            sol.remaining_hours as remaining_hours_so
        """, super()._select())

    def _group_by(self):
        return SQL("""%s,
            sol.remaining_hours
        """, super()._group_by())

    def _from(self):
        return SQL("""%s
            LEFT JOIN sale_order_line sol ON t.sale_line_id = sol.id
        """, super()._from())
