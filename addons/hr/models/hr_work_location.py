# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError

from .hr_employee_location import DAYS


class HrWorkLocation(models.Model):
    _name = 'hr.work.location'
    _description = "Work Location"
    _order = 'name'

    _latitude_range = models.Constraint(
        'CHECK(latitude IS NULL OR (latitude >= -90 AND latitude <= 90))',
        'Latitude must be between -90 and 90 degrees.',
    )
    _longitude_range = models.Constraint(
        'CHECK(longitude IS NULL OR (longitude >= -180 AND longitude <= 180))',
        'Longitude must be between -180 and 180 degrees.',
    )

    active = fields.Boolean(default=True)
    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    location_type = fields.Selection([
        ('home', 'Home'),
        ('office', 'Office'),
        ('other', 'Other')], string='Location Type', default='office', required=True)
    location_number = fields.Char()
    latitude = fields.Float(string="Latitude", digits=(10, 7))
    longitude = fields.Float(string="Longitude", digits=(10, 7))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_by_employee(self):
        """Prevent deletion of work locations currently assigned to employees."""
        for day_field in DAYS:
            if self.env['hr.employee'].search_count([(day_field, 'in', self.ids)], limit=1):
                raise UserError(
                    self.env._("You cannot delete work locations that are currently assigned to employees. "
                              "Please reassign employees to different locations first.")
                )

        if self.env['hr.employee'].search_count([('work_location_id', 'in', self.ids)], limit=1):
            raise UserError(
                self.env._("You cannot delete work locations that are currently assigned to employees. "
                          "Please reassign employees to different locations first.")
            )

    def open_location_map(self):
        return {
            "type": "ir.actions.client",
            "tag": "open_location_map",
            "target": "new",
            "name": "Select the Location",
            "context": {
                "location_res_id": self.id,
                "location_latitude": self.latitude,
                "location_longitude": self.longitude,
                "footer": False,
            },
        }
