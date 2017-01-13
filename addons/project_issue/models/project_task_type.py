# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProjectStage(models.Model):
    _inherit = ['project.task.type']

    def _get_mail_template_id_domain(self):
        domain = super(ProjectStage, self)._get_mail_template_id_domain()
        return ['|'] + domain + [('model', '=', 'project.issue')]
