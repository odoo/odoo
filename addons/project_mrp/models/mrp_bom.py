#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    project_ids = fields.Many2many('project.project', groups='project.group_project_user')
