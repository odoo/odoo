from odoo import fields, models


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = "project.task"

    user_skill_ids = fields.One2many(
        comodel_name="hr.employee.skill",
        related="employee_ids.current_employee_skill_ids",
    )
