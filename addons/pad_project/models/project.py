# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = ["project.task", 'pad.common']

    description_pad = fields.Char('Pad URL', pad_content_field='description')
    use_pad = fields.Boolean(related="project_id.use_pads", string="Use collaborative pad")


class ProjectProject(models.Model):
    _inherit = "project.project"

    use_pads = fields.Boolean("Use collaborative pads", help="Use collaborative pad for the tasks on this project.")
