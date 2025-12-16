from odoo import api, fields, models


class TaskShareWizard(models.TransientModel):
    _name = 'task.share.wizard'
    _inherit = ['portal.share']
    _description = 'Task Sharing'

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        if 'task_id' in fields and not result.get('task_id') and result['res_id']:
            result['task_id'] = result['res_id']
        else:
            result['task_id'] = False
        return result

    task_id = fields.Many2one('project.task')
    project_privacy_visibility = fields.Selection(related='task_id.project_privacy_visibility')
