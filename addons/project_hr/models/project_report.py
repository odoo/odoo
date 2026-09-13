from odoo import fields, models


class ReportProjectTaskUser(models.Model):
    _inherit = "report.project.task.user"

    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        related="task_id.employee_ids",
        string="Employees",
    )
