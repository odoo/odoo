# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = ["project.task", 'pad.common']
    _description = 'Task'

    description_pad = fields.Char('Pad URL', pad_content_field='description', copy=False)
    use_pad = fields.Boolean(related="project_id.use_pads", string="Use collaborative pad", readonly=True)

    @api.onchange('use_pad')
    def _onchange_use_pads(self):
        """ Copy the content in the pad when the user change the project of the task to the one with no pads enabled.

            This case is when the use_pad becomes False and we have already generated the url pad,
            that is the description_pad field contains the url of the pad.
        """
        if not self.use_pad and self.description_pad:
            vals = {'description_pad': self.description_pad}
            self._set_pad_to_field(vals)
            self.description = vals['description']

    @api.model
    def create(self, vals):
        # When using quick create, the project_id is in the context, not in the vals
        project_id = vals.get('project_id', False) or self.default_get(['project_id']).get('project_id', False)
        if not self.env['project.project'].browse(project_id).use_pads:
            self = self.with_context(pad_no_create=True)
        return super(ProjectTask, self).create(vals)

    def _get_pad_content(self):
        """
        Gets the content of the pad used to edit the task description
        and returns it.
        """
        self.ensure_one()
        return self.pad_get_content(self.description_pad)


class ProjectProject(models.Model):
    _name = "project.project"
    _inherit = ["project.project", 'pad.common']
    _description = 'Project'

    description_pad = fields.Char('Pad URL', pad_content_field='description', copy=False)
    use_pads = fields.Boolean("Use collaborative pads", default=True,
        help="Use collaborative pad for the tasks on this project.")
