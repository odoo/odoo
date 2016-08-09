# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProjectIssueConfiguration(models.TransientModel):
    _inherit = 'project.config.settings'

    module_project_issue_sheet = fields.Selection([
            (0, "Do not track working hours on issues"),
            (1, "Activate timesheets on issues")
            ], string="Timesheets on Issues",
            help='Provides timesheet support for the issues/bugs management in project.\n'
                 '-This installs the module project_issue_sheet.')
    module_rating_project_issue = fields.Selection([
        (0, "No customer rating"),
        (1, 'Track customer satisfaction on issues')
        ], "Rating on issue",
        help="This allows customers to give rating on issue")
