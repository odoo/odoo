# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    project_id = fields.Many2one('project.project', groups='project.group_project_user')
