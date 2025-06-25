# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields

from .hr_homeworking import DAYS


class ResUsers(models.Model):
    _inherit = 'res.users'

    monday_location_id = fields.Many2one("hr.work.location", related="employee_id.monday_location_id", readonly=False, string='Mondays')
    tuesday_location_id = fields.Many2one("hr.work.location", related="employee_id.tuesday_location_id", readonly=False, string='Tuesdays')
    wednesday_location_id = fields.Many2one("hr.work.location", related="employee_id.wednesday_location_id", readonly=False, string='Wednesdays')
    thursday_location_id = fields.Many2one("hr.work.location", related="employee_id.thursday_location_id", readonly=False, string='Thursdays')
    friday_location_id = fields.Many2one("hr.work.location", related="employee_id.friday_location_id", readonly=False, string='Fridays')
    saturday_location_id = fields.Many2one("hr.work.location", related="employee_id.saturday_location_id", readonly=False, string='Saturdays')
    sunday_location_id = fields.Many2one("hr.work.location", related="employee_id.sunday_location_id", readonly=False, string='Sundays')

    def _get_employee_fields_to_sync(self):
        return super()._get_employee_fields_to_sync() + DAYS

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + DAYS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + DAYS

    def _compute_im_status(self):
        super()._compute_im_status()
        dayfield = self.env['hr.employee']._get_current_day_location_field()
        for user in self:
            location_type = user[dayfield].location_type
            if not location_type:
                continue
            im_status = user.im_status
            if im_status in ["online", "away", "busy", "offline"]:
                user.im_status = "presence_" + location_type + "_" + im_status
