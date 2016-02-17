# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models

class ProjectConfigSettings(models.TransientModel):
    _inherit = 'project.config.settings'

    module_rating_project_issue = fields.Selection([
        (0, "No customer rating"),
        (1, 'Track customer satisfaction on issues')
        ], "Rating on issue",
        help="This allows customers to give rating on issue")
