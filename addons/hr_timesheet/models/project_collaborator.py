# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProjectCollaborator(models.Model):
    _inherit = 'project.collaborator'

    @api.model
    def _toggle_project_sharing_portal_rules(self, active):
        super()._toggle_project_sharing_portal_rules(active)
        # ir.access
        access_timesheet_portal = self.env.ref('hr_timesheet.access_account_analytic_line_group_portal').sudo()
        if access_timesheet_portal.active != active:
            access_timesheet_portal.active = active
