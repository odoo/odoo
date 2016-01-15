# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProjectStage(models.Model):
    _inherit = ['project.task.type']

    def _get_mail_template_id_domain(self):
        domain = super(ProjectStage, self)._get_mail_template_id_domain()
        return ['|'] + domain + [('model', '=', 'project.issue')]

    @api.multi
    def archive(self, archive, project_ids=None, archive_only_content=False):
        if project_ids:
            domain = [('project_id', 'in', project_ids), ('stage_id', 'in', self.ids)]
        else:
            domain = [('stage_id', 'in', self.ids)]
        self.env['project.issue'].search(domain).write({'active': not archive})
        return super(ProjectStage, self).archive(archive, project_ids=project_ids, archive_only_content=archive_only_content)
