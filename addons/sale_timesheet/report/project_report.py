# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import fields, models


class ReportProjectTaskUser(models.Model):
    _inherit = 'report.project.task.user'

    remaining_hours_so = fields.Float('Remaining Hours on SO', readonly=True)

    def _select(self):
        return super()._select() + """,
            sol.remaining_hours as remaining_hours_so
        """

    def _group_by(self):
        return super()._group_by() + """,
            sol.remaining_hours
        """

    def _from(self):
        return super()._from() + """
            LEFT JOIN sale_order_line sol ON t.id = sol.task_id
        """
