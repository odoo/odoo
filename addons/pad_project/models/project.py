# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = ["project.task", 'pad.common']

    description_pad = fields.Char('Pad URL', pad_content_field='description')
    use_pad = fields.Boolean(related="project_id.use_pads", string="Use collaborative pad")

    @api.model
    def create(self, vals):
        # When using quick create, the project_id is in the context, not in the vals
        project_id = vals.get('project_id', False) or self.default_get(['project_id'])['project_id']
        if not self.env['project.project'].browse(project_id).use_pads:
            self = self.with_context(pad_no_create=True)
        return super(ProjectTask, self).create(vals)

    @api.multi
    def copy(self, default=None):
        if not self.use_pad:
            self = self.with_context(pad_no_create=True)
        return super(ProjectTask, self).copy(default)


class ProjectProject(models.Model):
    _inherit = "project.project"

    use_pads = fields.Boolean("Use collaborative pads", help="Use collaborative pad for the tasks on this project.")
