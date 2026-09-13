from odoo import fields, models


class ReportProjectTaskUser(models.Model):
    _inherit = "report.project.task.user"

    user_skill_ids = fields.One2many(
        comodel_name="hr.employee.skill",
        related="task_id.user_skill_ids",
        string="Skills",
    )
