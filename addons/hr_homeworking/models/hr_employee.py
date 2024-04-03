# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

from .hr_homeworking import DAYS


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

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
        help='This is the exceptional, non-weekly, location set for today.')
    hr_icon_display = fields.Selection(selection_add=[('presence_home', 'At Home'),
                                                      ('presence_office', 'At Office'),
                                                      ('presence_other', 'At Other')])
    name_work_location_display = fields.Char(compute="_compute_name_work_location_display")
    today_location_name = fields.Char()

    @api.model
    def _get_current_day_location_field(self):
        return DAYS[fields.Date.today().weekday()]

    # hack to allow groupby on today's location. Since there are 7 different fields, we have to use a placeholder
    # in the search view and replace it with the correct field every time the views are fetched.
    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        dayfield = self._get_current_day_location_field()
        if 'search' in res['views']:
            res['views']['search']['arch'] = res['views']['search']['arch'].replace('today_location_name', dayfield)
        if 'list' in res['views']:
            res['views']['list']['arch'] = res['views']['list']['arch'].replace('name_work_location_display', dayfield)
        return res

    @api.depends('exceptional_location_id')
    def _compute_name_work_location_display(self):
        dayfield = self._get_current_day_location_field()
        unspecified = _('Unspecified')
        for employee in self:
            current_location_id = employee.exceptional_location_id or employee[dayfield]
            employee.name_work_location_display = current_location_id.name if current_location_id else unspecified

    def _compute_exceptional_location_id(self):
        today = fields.Date.today()
        current_employee_locations = self.env['hr.employee.location'].search([
            ('employee_id', 'in', self.ids),
            ('date', '=', today),
        ])
        employee_work_locations = {l.employee_id.id: l.work_location_id for l in current_employee_locations}

        for employee in self:
            employee.exceptional_location_id = employee_work_locations.get(employee.id, False)

    @api.depends(*DAYS, 'exceptional_location_id')
    def _compute_presence_icon(self):
        super()._compute_presence_icon()
        dayfield = self._get_current_day_location_field()
        for employee in self:
            today_employee_location_id = employee.exceptional_location_id or employee[dayfield]
            if not today_employee_location_id or employee.hr_icon_display.startswith('presence_holiday'):
                continue
            employee.hr_icon_display = f'presence_{today_employee_location_id.location_type}'
            employee.show_hr_icon_display = True
