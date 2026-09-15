# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReportProjectTaskUser(models.Model):
    _inherit = "report.project.task.user"

    def _get_remaining_hours_sql(self):
        return f"""
            CASE WHEN t.id = (SELECT rc.leave_timesheet_task_id FROM res_company rc WHERE rc.id = t.company_id)
            THEN 0 ELSE ({super()._get_remaining_hours_sql()}) END
        """
