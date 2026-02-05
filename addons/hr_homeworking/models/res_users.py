# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields

from .hr_homeworking import DAYS


class ResUsers(models.Model):
    _inherit = 'res.users'

    monday_location_id = fields.Many2one("hr.work.location", related="employee_id.monday_location_id", readonly=False, string='Mondays', user_writeable=True)
    tuesday_location_id = fields.Many2one("hr.work.location", related="employee_id.tuesday_location_id", readonly=False, string='Tuesdays', user_writeable=True)
    wednesday_location_id = fields.Many2one("hr.work.location", related="employee_id.wednesday_location_id", readonly=False, string='Wednesdays', user_writeable=True)
    thursday_location_id = fields.Many2one("hr.work.location", related="employee_id.thursday_location_id", readonly=False, string='Thursdays', user_writeable=True)
    friday_location_id = fields.Many2one("hr.work.location", related="employee_id.friday_location_id", readonly=False, string='Fridays', user_writeable=True)
    saturday_location_id = fields.Many2one("hr.work.location", related="employee_id.saturday_location_id", readonly=False, string='Saturdays', user_writeable=True)
    sunday_location_id = fields.Many2one("hr.work.location", related="employee_id.sunday_location_id", readonly=False, string='Sundays', user_writeable=True)

    def _get_employee_fields_to_sync(self):
        return super()._get_employee_fields_to_sync() + DAYS
