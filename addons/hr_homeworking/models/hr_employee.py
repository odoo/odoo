# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from .hr_homeworking import DAYS


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    monday_location_id = fields.Many2one('hr.work.location', string='Monday')
    tuesday_location_id = fields.Many2one('hr.work.location', string='Tuesday')
    wednesday_location_id = fields.Many2one('hr.work.location', string='Wednesday')
    thursday_location_id = fields.Many2one('hr.work.location', string='Thursday')
    friday_location_id = fields.Many2one('hr.work.location', string='Friday')
    saturday_location_id = fields.Many2one('hr.work.location', string='Saturday')
    sunday_location_id = fields.Many2one('hr.work.location', string='Sunday')
    exceptional_location_id = fields.Many2one(
        'hr.work.location', string='Current',
        compute='_compute_exceptional_location_id',
        help='This is the exceptional, non-weekly, location set for today.', groups="hr.group_hr_user")
    hr_icon_display = fields.Selection(selection_add=[('presence_home', 'At Home'),
                                                      ('presence_office', 'At Office'),
                                                      ('presence_other', 'At Other')])
    today_actual_location_id = fields.Many2one(
        'hr.work.location',
        string="Today's Location",
        compute='_compute_today_actual_location',
        store=True,
    )
    today_location_name = fields.Char()

    def _compute_exceptional_location_id(self):
        today = fields.Date.today()
        current_employee_locations = self.env['hr.employee.location'].search([
            ('employee_id', 'in', self.ids),
            ('date', '=', today),
        ])
        employee_work_locations = {l.employee_id.id: l.work_location_id for l in current_employee_locations}

        for employee in self:
            employee.exceptional_location_id = employee_work_locations.get(employee.id, False)

    @api.depends('work_location_id', *DAYS)
    def _compute_today_actual_location(self):
        dayfield = self._get_current_day_location_field()
        for employee in self:
            specific_location = employee[dayfield]
            employee.today_actual_location_id = specific_location or employee.work_location_id

    @api.depends(*DAYS, 'exceptional_location_id')
    def _compute_presence_icon(self):
        super()._compute_presence_icon()
        dayfield = self._get_current_day_location_field()
        for employee in self:
            today_employee_location_id = employee.sudo().exceptional_location_id or employee[dayfield]
            if not today_employee_location_id:
                continue
            employee.hr_icon_display = f'presence_{today_employee_location_id.location_type}'
            employee.show_hr_icon_display = True

    @api.depends(*DAYS, "exceptional_location_id")
    def _compute_work_location_name(self):
        dayfield = self.env['hr.employee'].today_actual_location_id
        for employee in self:
            current_location = employee.exceptional_location_id or dayfield
            employee.work_location_name = current_location.name

    @api.depends(*DAYS, "exceptional_location_id")
    def _compute_work_location_type(self):
        dayfield = self.env['hr.employee'].today_actual_location_id
        for employee in self:
            current_location = employee.exceptional_location_id or dayfield
            employee.work_location_type = current_location.location_type

    @api.model
    def _get_current_day_location_field(self):
        return DAYS[fields.Date.today().weekday()]

    @api.model
    def _cron_update_today_location(self):
        """ Method triggered by the cron job every night at midnight to refresh the day """
        # We search for all employees who have a schedule set (or simply all active)
        employees = self.search([('active', '=', True)])

        # Triggering the compute method to refresh the stored column in the database
        employees._compute_today_actual_location()
