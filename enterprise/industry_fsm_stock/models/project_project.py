from odoo import models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    def _get_picking_action(self, action_name, picking_type=None):
        action = super()._get_picking_action(action_name, picking_type)
        if picking_type == 'outgoing':
            action['view_mode'] += ',map'
        return action
