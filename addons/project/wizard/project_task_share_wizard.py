from odoo import fields, models


class TaskShareWizard(models.TransientModel):
    _name = 'task.share.wizard'
    _inherit = ['portal.share']
    _description = 'Task Sharing'

    task_id = fields.Many2one('project.task', default=lambda self: self.res_id)
    project_privacy_visibility = fields.Selection(related='task_id.project_privacy_visibility')
