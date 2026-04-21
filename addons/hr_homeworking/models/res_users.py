# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields
from odoo.addons.hr.models.res_users import field_employee

from .hr_homeworking import DAYS


class ResUsers(models.Model):
    _inherit = 'res.users'

    monday_location_id = field_employee(fields.Many2one, 'monday_location_id', comodel_name='hr.work.location', string='Mondays', user_writeable=True)
    tuesday_location_id = field_employee(fields.Many2one, 'tuesday_location_id', comodel_name='hr.work.location', string='Tuesdays', user_writeable=True)
    wednesday_location_id = field_employee(fields.Many2one, 'wednesday_location_id', comodel_name='hr.work.location', string='Wednesdays', user_writeable=True)
    thursday_location_id = field_employee(fields.Many2one, 'thursday_location_id', comodel_name='hr.work.location', string='Thursdays', user_writeable=True)
    friday_location_id = field_employee(fields.Many2one, 'friday_location_id', comodel_name='hr.work.location', string='Fridays', user_writeable=True)
    saturday_location_id = field_employee(fields.Many2one, 'saturday_location_id', comodel_name='hr.work.location', string='Saturdays', user_writeable=True)
    sunday_location_id = field_employee(fields.Many2one, 'sunday_location_id', comodel_name='hr.work.location', string='Sundays', user_writeable=True)

    def _get_employee_fields_to_sync(self):
        return super()._get_employee_fields_to_sync() + DAYS

    def _compute_im_status(self):
        super()._compute_im_status()
        dayfield = self.env['hr.employee']._get_current_day_location_field()
        for user in self:
            location_type = user[dayfield].location_type
            if not location_type:
                continue
            im_status = user.im_status
            if im_status in ["online", "away", "busy", "offline"]:
                user.im_status = location_type + "_" + im_status
