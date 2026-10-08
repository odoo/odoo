from odoo import api, fields, models


class TaskShareWizard(models.TransientModel):
    _name = 'task.share.wizard'
    _inherit = ['portal.share']
    _description = 'Task Sharing'

    project_privacy_visibility = fields.Selection(selection=lambda self: self.env['project.task']._fields['project_privacy_visibility']._description_selection(self.env),
        compute='_compute_project_privacy_visibility',
    )

    @api.depends('resource_ref')
    def _compute_project_privacy_visibility(self):
        for wizard in self:
            wizard.project_privacy_visibility = wizard.resource_ref.project_privacy_visibility if wizard.resource_ref else False
