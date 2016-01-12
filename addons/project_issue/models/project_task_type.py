# -*- coding: utf-8 -*-

from openerp import models


class ProjectStage(models.Model):
    _name = "project.task.type"
    _inherit = ['project.task.type']

    def _get_mail_template_id_domain(self):
        domain = super(ProjectStage, self)._get_mail_template_id_domain()
        return ['|'] + domain + [('model', '=', 'project.issue')]
