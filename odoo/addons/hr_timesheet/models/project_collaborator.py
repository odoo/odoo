# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProjectCollaborator(models.Model):
    _inherit = 'project.collaborator'

    @api.model
    def _toggle_project_sharing_portal_rules(self, active):
        super()._toggle_project_sharing_portal_rules(active)
        # ir.model.access
        access_timesheet_portal = self.env.ref('hr_timesheet.access_account_analytic_line_portal_user').sudo()
        if access_timesheet_portal.active != active:
            access_timesheet_portal.write({'active': active})

        # ir.rule
        timesheet_portal_ir_rule = self.env.ref('hr_timesheet.timesheet_line_rule_portal_user').sudo()
        if timesheet_portal_ir_rule.active != active:
            timesheet_portal_ir_rule.write({'active': active})
