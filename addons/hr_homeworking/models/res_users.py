# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields

from .hr_homeworking import DAYS

class User(models.Model):
    _inherit = ['res.users']

    monday_location_id = fields.Many2one("hr.work.location", related="employee_id.monday_location_id", readonly=False, string='Monday')
    tuesday_location_id = fields.Many2one("hr.work.location", related="employee_id.tuesday_location_id", readonly=False, string='Tuesday')
    wednesday_location_id = fields.Many2one("hr.work.location", related="employee_id.wednesday_location_id", readonly=False, string='Wednesday')
    thursday_location_id = fields.Many2one("hr.work.location", related="employee_id.thursday_location_id", readonly=False, string='Thursday')
    friday_location_id = fields.Many2one("hr.work.location", related="employee_id.friday_location_id", readonly=False, string='Friday')
    saturday_location_id = fields.Many2one("hr.work.location", related="employee_id.saturday_location_id", readonly=False, string='Saturday')
    sunday_location_id = fields.Many2one("hr.work.location", related="employee_id.sunday_location_id", readonly=False, string='Sunday')

    def _get_employee_by_user(self):
        Employee = self.env["hr.employee"].with_context(active_test=True)
        employees = Employee.search([("user_id", "in", self.ids)], order="id desc")
        employee_by_user = dict.fromkeys(self, Employee)
        for user, user_employees in employees.grouped("user_id").items():
            # the same employee for every viewer: the one of the user's company, else the newest one
            employee_by_user[user] = next(
                (employee for employee in user_employees if employee.company_id == user.company_id),
                user_employees[:1],
            )
        return employee_by_user

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
        # sudo: hr.employee - can read the location of users, exceptions included, to show IM status
        employee_by_user = self.sudo()._get_employee_by_user()
        for user in self:
            employee = employee_by_user[user]
            location_type = (employee.exceptional_location_id or employee[dayfield]).location_type
            if not location_type:
                continue
            im_status = user.im_status
            if im_status == "online" or im_status == "away" or im_status == "offline":
                user.im_status = "presence_" + location_type + "_" + im_status

    def _is_user_available(self):
        location_types = self.env['hr.work.location']._fields['location_type'].get_values(self.env)
        return self.im_status in ['online'] + [f'presence_{location_type}_online' for location_type in location_types]
