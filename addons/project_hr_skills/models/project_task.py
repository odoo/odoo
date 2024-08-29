# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import project

from odoo import fields, models

class ProjectTask(models.Model, project.ProjectTask):

    user_skill_ids = fields.One2many('hr.employee.skill', related='user_ids.employee_skill_ids')
