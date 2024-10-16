# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import mrp


class MrpBom(mrp.MrpBom):

    project_id = fields.Many2one('project.project')
