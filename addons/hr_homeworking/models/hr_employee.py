# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta
from dateutil.rrule import rrule, WEEKLY

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
            ('start_date', '=', today),
            ('weekly', '=', False)
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

    def _get_worklocation(self, start_date, end_date):
        worklocations = self.env['hr.employee.location'].search([
            ('employee_id', 'in', self.ids),
            '|',
                '&', '&',
                    ('start_date', '<=', end_date),
                    ('start_date', '>=', start_date),
                    ('weekly', '=', False),
                '&', '&',
                    ('start_date', '<=', end_date),
                    '|',
                        ('end_date', '>=', start_date),
                        ('end_date', '=', False),
                    ('weekly', '=', True),
        ], order='start_date ASC')
        worklocation_default = worklocations.filtered('weekly')
        worklocations_exception = worklocations - worklocation_default
        week_start = int(self.env['res.lang']._lang_get(self.env.user.lang).week_start) - 1  # week_start is 1 indexed

        # 1. Get all exceptional dates in the range
        worklocation_data = defaultdict(list)
        date_exception = defaultdict(set)
        for index, worklocation in enumerate(worklocations_exception):
            if not worklocation.removed:
                worklocation_data[worklocation.employee_id.id].append({
                    'resModel': "hr.employee.location",
                    'idInDB': worklocation.id,
                    'id': index,
                    'title': worklocation.work_location_name,
                    'date': worklocation.start_date,
                    'location_id': worklocation.work_location_id.id,
                    'weekly': False,
                    'icon': worklocation.work_location_type,
                    'userId': worklocation.employee_id.user_id.id,
                    'partner_id': [worklocation.employee_id.work_contact_id.id]  # frontend expects a list (google_calendar)
                })
            date_exception[worklocation.employee_id.id].add(worklocation.start_date)

        # 2. Get all weekly (default) dates in the range
        index = len(worklocations_exception.ids)
        start_date = fields.Datetime.to_datetime(start_date).date()
        end_date = fields.Datetime.to_datetime(end_date).date()
        for worklocation in worklocation_default:
            start = max(worklocation.start_date, start_date)  # the recurring location might have been set before our date_range, discard locations before that
            end = worklocation.end_date or end_date
            days_list = list(rrule(WEEKLY, start, byweekday=worklocation.start_date.weekday(), wkst=week_start, until=end))
            if not days_list:
                continue
            days_list = [x.date() for x in days_list]
            final_days_list = []
            for day in days_list:
                if day not in date_exception[worklocation.employee_id.id]:
                    final_days_list.append(day)
            for index_intern, final_day in enumerate(final_days_list):
                worklocation_data[worklocation.employee_id.id].append({
                    'resModel': "hr.employee.location",
                    'idInDB': worklocation.id,
                    'id': index_intern + index,
                    'title': worklocation.work_location_name,
                    'date': final_day,
                    'location_id': worklocation.work_location_id.id,
                    'weekly': True,
                    'icon': worklocation.work_location_type,
                    'userId': worklocation.employee_id.user_id.id,
                    'partner_id': [worklocation.employee_id.work_contact_id.id]
                })
            index += len(final_days_list)

        for employee in worklocation_data:
            worklocation_data[employee].sort(key=lambda wl: (wl['title'], wl['date']))
        return worklocation_data

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        today = fields.Date.today()
        homeworking_vals = []
        for employee in res:
            for day_index, field_name in enumerate(DAYS):
                if not employee[field_name]:
                    continue
                day_offset = (day_index - today.weekday() + 7) % 7
                date = today + timedelta(days=day_offset)
                homeworking_vals.append({
                    'employee_id': employee.id,
                    'work_location_id': employee[field_name].id,
                    'weekly': True,
                    'start_date': date
                })
        self.env['hr.employee.location'].create(homeworking_vals)
        return res

    def write(self, values):
        if self.env.context.get('no_loop'):
            return super().write(values)
        homeworking_vals = []
        employee_locations_to_remove = defaultdict(set)
        today = fields.Date.today()
        for day_index, field_name in enumerate(DAYS):
            if field_name not in values:
                continue
            if not values[field_name]:
                for employee in self:
                    employee_locations_to_remove[employee.id].add(day_index)
            else:
                day_offset = (day_index - today.weekday() + 7) % 7
                date = today + timedelta(days=day_offset)
                for employee in self:
                    homeworking_vals.append({
                        'employee_id': employee.id,
                        'work_location_id': values[field_name],
                        'weekly': True,
                        'start_date': date
                    })
        if homeworking_vals:
            self.env['hr.employee.location'].create(homeworking_vals)
        if employee_locations_to_remove:
            read_group = self.env['hr.employee.location']._read_group([
                ('current_location', '=', True), ('employee_id', 'in', list(employee_locations_to_remove.keys()))],
                groupby=['employee_id'], aggregates=['id:recordset']
            )
            for employee, locations in read_group:
                if employee.id in employee_locations_to_remove:
                    locations.filtered(lambda l: l.weekday in employee_locations_to_remove[employee.id]).delete_default_worklocation()
        return super().write(values)
