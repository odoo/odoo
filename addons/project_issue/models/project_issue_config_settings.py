# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProjectIssueConfiguration(models.TransientModel):
    _inherit = 'project.config.settings'

    module_project_issue_sheet = fields.Boolean(string="Timesheets on Issues")
    module_rating_project_issue = fields.Boolean("Rating on Issues")
