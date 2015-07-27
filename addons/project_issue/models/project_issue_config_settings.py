# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields

class ProjectIssueConfiguration(models.TransientModel):
    _inherit = 'project.config.settings'

    module_project_issue_sheet = fields.Selection([
            (0, "Do not track working hours on issues"),
            (1, "Activate timesheets on issues")
            ], string="Timesheets on Issues",
            help='Provides timesheet support for the issues/bugs management in project.\n'
                 '-This installs the module project_issue_sheet.')
