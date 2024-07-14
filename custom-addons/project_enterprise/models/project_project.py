# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Project(models.Model):
    _inherit = 'project.project'

    def action_view_tasks(self):
        action = super().action_view_tasks()
        if self._get_hide_partner():
            action['views'] = [(view_id, view_type) for view_id, view_type in action['views'] if view_type != 'map']
        return action
