# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import project


class ProjectTask(project.ProjectTask):

    user_skill_ids = fields.One2many('hr.employee.skill', related='user_ids.employee_skill_ids')
