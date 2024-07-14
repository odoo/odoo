# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    def _get_default_project_ids(self):
        # Call super first to take into account the context
        default_project_ids = super()._get_default_project_ids()
        default_user_id = self._context.get('default_user_id') # To check if it is a personal stage
        if self._context.get('fsm_mode') and not default_project_ids and not default_user_id:
            default_project = self.env['project.project'].search([('is_fsm', '=', True)], limit=1, order='sequence')
            default_project_ids = [default_project.id] if default_project else None
        return default_project_ids
