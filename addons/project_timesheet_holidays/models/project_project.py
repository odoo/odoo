# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import RedirectWarning


class ProjectProject(models.Model):
    _inherit = 'project.project'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_timeoff_project(self):
        timeoff_projects = self.env['res.company'].sudo().search([
            ('internal_project_id', 'in', self.ids),
        ]).internal_project_id
        if timeoff_projects:
            raise RedirectWarning(
                self.env._(
                    "The following projects are used to generate time off timesheets and cannot be deleted: %(projects)s. "
                    "Set another Project in the Timesheets settings first.",
                    projects=timeoff_projects.mapped('display_name'),
                ),
                self.env.ref('hr_timesheet.hr_timesheet_config_settings_action').id,
                self.env._("Go to Settings"),
            )
