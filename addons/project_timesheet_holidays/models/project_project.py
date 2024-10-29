from odoo import models, api, _
from odoo.exceptions import ValidationError

class ProjectProject(models.Model):
    _inherit = "project.project"

    @api.constrains('company_id')
    def _check_company_change(self):
        time_off_type_data = dict(self.env['hr.leave.type']._read_group(
            [('timesheet_project_id', 'in', self.filtered('company_id').ids)],
            ['timesheet_project_id'],
            ['id:recordset']))
        for project in self:
            time_off_types = time_off_type_data.get(project, {})
            for time_off_type in time_off_types:
                if time_off_type.company_id and time_off_type.company_id != project.company_id:
                    raise ValidationError(_("You can't change the project's company because it's linked to a time off type in another company. Either match the time off type's company to the project's or leave both unset."))
