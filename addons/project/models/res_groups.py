# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResGroups(models.Model):
    _inherit = 'res.groups'

    def _get_light_group_xmlids(self):
        return super()._get_light_group_xmlids() + (
            'project.group_project_milestone',
            'project.group_project_recurring_tasks',
            'project.group_project_task_dependencies',
            'project.group_project_stages',
        )
