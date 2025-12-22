from odoo import api, fields, models


class TaskShareWizard(models.TransientModel):
    _name = 'task.share.wizard'
    _inherit = ['portal.share']
    _description = 'Task Sharing'

    @api.model
    def _selection_target_model(self):
        task_model = self.env['ir.model']._get('project.task')
        return [(task_model.model, task_model.name)]

    project_privacy_visibility = fields.Selection(selection=lambda self: self.env['project.project']._fields['privacy_visibility'].selection,
        compute='_compute_project_privacy_visibility',
    )

    @api.depends('res_model', 'res_id')
    def _compute_resource_ref(self):
        for wizard in self:
            if wizard.res_model and wizard.res_model == 'project.task':
                wizard.resource_ref = '%s,%s' % (wizard.res_model, wizard.res_id or 0)
            else:
                wizard.resource_ref = None

    @api.depends('resource_ref')
    def _compute_project_privacy_visibility(self):
        for wizard in self:
            wizard.project_privacy_visibility = wizard.resource_ref.project_privacy_visibility if wizard.resource_ref else False
