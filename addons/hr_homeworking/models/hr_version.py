# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from .hr_homeworking import DAYS


class HrVersion(models.Model):
    _inherit = 'hr.version'

    @api.depends(lambda self: ["employee_id." + day_field for day_field in DAYS] + ["employee_id.exceptional_location_id"])
    def _compute_work_location_name_type(self):
        dayfield = self.env['hr.employee']._get_current_day_location_field()
        for version in self:
            current_location_id = version.employee_id.exceptional_location_id or version.employee_id[dayfield] or\
                version.employee_id.work_location_id
            version.work_location_name = current_location_id.name or None
            version.work_location_type = current_location_id.location_type or 'other'
