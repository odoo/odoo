from odoo import api, models


class ProjectCollaborator(models.Model):
    _inherit = "project.collaborator"

    @api.model
    def _update_project_sharing_portal_rules(self, active):
        super()._update_project_sharing_portal_rules(active)
        access = self.env.ref("hr_timesheet.timesheet_line_rule_portal_user").sudo()
        if access.active != active:
            access.write({"active": active})
