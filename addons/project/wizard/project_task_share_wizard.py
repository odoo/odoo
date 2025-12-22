from odoo import api, fields, models


class TaskShareWizard(models.TransientModel):
    _name = 'task.share.wizard'
    _inherit = ['portal.share']
    _description = 'Task Sharing'

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        res_model = result.get('res_model')
        res_id = result.get('res_id')
        if res_model and res_id:
            record = self.env[res_model].browse(res_id)
            result['project_privacy_visibility'] = record.project_privacy_visibility
        return result

    project_privacy_visibility = fields.Selection(selection=lambda self: self.env['project.task']._fields['project_privacy_visibility']._description_selection(self.env))
