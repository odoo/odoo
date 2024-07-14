# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.osv import expression

class ProjectMilestone(models.Model):
    _inherit = 'project.milestone'

    @api.model
    def search_milestone_from_task(self, task_domain=None, milestone_domain=None, fields=None, order=None):
        project_ids = self.env['project.task']._read_group(task_domain or [], ['project_id'])
        milestone_domain = expression.AND([
            milestone_domain or [],
            [('project_id', 'in', [project.id for [project] in project_ids if project])]
        ])
        return self.env['project.milestone'].search_read(milestone_domain, fields=fields, order=order)
