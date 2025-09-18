# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProjectTask(models.Model):
    """Expose assignee skills directly from the employee identity."""

    _inherit = "project.task"

    user_skill_ids = fields.One2many(
        "hr.employee.skill",
        related="employee_ids.employee_skill_ids",
    )
