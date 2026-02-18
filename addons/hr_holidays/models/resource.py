# Part of Odoo. See LICENSE file for full copyright and licensing details.

import csv
from datetime import datetime, time, UTC
from zoneinfo import ZoneInfo

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import babel_locale_parse, file_open, file_path
from odoo.tools.date_utils import convert_timezone, weeknumber


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    holiday_id = fields.Many2one("hr.leave", string='Time Off Request')
    elligible_for_accrual_rate = fields.Boolean(string='Eligible for Accrual Rate', default=False,
        help="If checked, this time off type will be taken into account for accruals computation.")

    @api.constrains('date_from', 'date_to', 'calendar_id')
    def _check_compare_dates(self):
        all_existing_leaves = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('company_id', 'in', self.company_id.ids),
            ('date_from', '<=', max(self.mapped('date_to'))),
            ('date_to', '>=', min(self.mapped('date_from'))),
        ])
        for record in self:
            if not record.resource_id:
                existing_leaves = all_existing_leaves.filtered(lambda leave:
                        record.id != leave.id
                        and record['company_id'] == leave['company_id']
                        and record['date_from'] <= leave['date_to']
                        and record['date_to'] >= leave['date_from'])
                if record.calendar_id:
                    existing_leaves = existing_leaves.filtered(lambda l: not l.calendar_id or l.calendar_id == record.calendar_id)
                if existing_leaves:
                    raise ValidationError(_('Two public holidays cannot overlap each other for the same working hours.'))

    def _get_domain(self, time_domain_dict):
        return Domain.OR(
            [
                ('employee_company_id', '=', date['company_id']),
                ('date_to', '>', date['date_from']),
                ('date_from', '<', date['date_to']),
            ]
            for date in time_domain_dict
        ) & Domain('state', 'not in', ['refuse', 'cancel'])

    def _get_time_domain_dict(self):
        return [{
            'company_id' : record.company_id.id,
            'date_from' : record.date_from,
            'date_to' : record.date_to
        } for record in self if not record.resource_id]

    def _reevaluate_leaves(self, time_domain_dict):
        if not time_domain_dict:
            return

        domain = self._get_domain(time_domain_dict)
        leaves = self.env['hr.leave'].search(domain)
        if not leaves:
            return

        previous_durations = leaves.mapped('number_of_days')
        previous_states = leaves.mapped('state')
        self.env.add_to_compute(self.env['hr.leave']._fields['number_of_days'], leaves)
        self.env.add_to_compute(self.env['hr.leave']._fields['duration_display'], leaves)
        leaves.sudo().write({
            'state': 'confirm',
        })
        sick_time_status = self.env['hr.work.entry.type'].search([('code', '=', 'LEAVE110')])
        leaves_to_recreate = self.env['hr.leave']
        for previous_duration, leave, state in zip(previous_durations, leaves, previous_states):
            duration_difference = previous_duration - leave.number_of_days
            message = False
            if duration_difference > 0 and leave.work_entry_type_id.requires_allocation:
                message = _("Due to a change in global time offs, you have been granted %s day(s) back.", duration_difference)
            if leave.number_of_days > previous_duration\
                    and (not sick_time_status or leave.work_entry_type_id not in sick_time_status):
                message = _("Due to a change in global time offs, %s extra day(s) have been taken from your allocation. Please review this leave if you need it to be changed.", -1 * duration_difference)
            try:
                leave.sudo().write({'state': state})  # sudo in order to skip _check_approval_update
                leave._check_validity()
                if leave.state == 'validate':
                    # recreate the resource leave that were removed by writing state to draft
                    leaves_to_recreate |= leave
            except ValidationError:
                leave.action_refuse()
                message = _("Due to a change in global time offs, this leave no longer has the required amount of available allocation and has been set to refused. Please review this leave.")
            if message:
                leave._notify_change(message)
        leaves_to_recreate.sudo()._create_resource_leave()

    def _ensure_datetime(self, datetime_representation, date_format=None):
        """
            Be sure to get a datetime object if we have the necessary information.
            :param datetime_reprentation: object which should represent a datetime
            :rtype: datetime if a correct datetime_represtion, None otherwise
        """
        if isinstance(datetime_representation, datetime):
            return datetime_representation
        elif isinstance(datetime_representation, str) and date_format:
            return datetime.strptime(datetime_representation, date_format)
        else:
            return None

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        time_domain_dict = res._get_time_domain_dict()
        self._reevaluate_leaves(time_domain_dict)
        return res

    def write(self, vals):
        time_domain_dict = self._get_time_domain_dict()
        res = super().write(vals)
        time_domain_dict.extend(self._get_time_domain_dict())
        self._reevaluate_leaves(time_domain_dict)

        return res

    def unlink(self):
        time_domain_dict = self._get_time_domain_dict()
        res = super().unlink()
        self._reevaluate_leaves(time_domain_dict)

        return res

    @api.depends('calendar_id')
    def _compute_company_id(self):
        for leave in self:
            leave.company_id = leave.holiday_id.employee_id.company_id or leave.calendar_id.company_id or leave.company_id or self.env.company

    def _get_holidays_from_csv(self, years, csv_file_path):
        """
            Load holidays for given country and year(s).
            Args:
                years: a single year (int) or iterable of years (e.g. range(2025, 2027))
                file_path: expects file path for  "public_holidays_in.csv" in CSV_DIR

            Returns:
                List of tuples (datetime.date, holiday_name)
        """
        # Normalize to set of years
        year_set = {years} if isinstance(years, int) else set(years)
        holidays = []
        with file_open(csv_file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get("date") or not row.get("holiday"):
                    continue
                dt = datetime.strptime(row["date"], "%Y-%m-%d").date()
                if dt.year > max(year_set):
                    break
                if dt.year in year_set:
                    holidays.append((dt, row["holiday"].strip()))

        return holidays

    def _generate_public_holidays(self, companies, year_range, convert_datetime=True):
        response = []
        existing_holidays_dict = dict(self.env["resource.calendar.leaves"]._read_group(
            domain=[
                ('company_id', 'in', companies.ids),
                ('date_from', '>=', datetime(year_range[0] - 1, 12, 31, 0, 0, 0)),
                ('date_to', '<=', datetime(year_range[-1] + 1, 1, 2, 0, 0, 0)),
                ('resource_id', '=', False),
            ],
            groupby=['company_id'],
            aggregates=['id:recordset'],
        ))

        for company in companies:
            if not company.country_code:
                response.append({
                    'title': self.env._('No Country Code'),
                    'type': 'danger',
                    'message': self.env._('Please select a country in %(company)s to load public holidays.', company=company.name),
                })
                continue

            try:
                csv_file_path = file_path(f"hr_holidays/data/public_holidays/public_holidays_{company.country_code.lower()}.csv")
            except FileNotFoundError:
                response.append({
                    'title': self.env._('No Public Holidays'),
                    'type': 'danger',
                    'message': self.env._('Public holidays are not available for %(country)s', country=company.country_id.name),
                })
                continue

            public_holidays_list = self._get_holidays_from_csv(year_range, csv_file_path)
            overlapped_holidays = False
            company_tz = ZoneInfo(company.tz)
            public_holidays_values_dict = {}

            for holiday_date, holiday_name in public_holidays_list:
                holiday_start_utc = convert_timezone(datetime.combine(holiday_date, time.min), UTC, company_tz)
                holiday_end_utc = convert_timezone(datetime.combine(holiday_date, time.max), UTC, company_tz)
                overlapping = any(
                    holiday.date_from <= holiday_end_utc and
                    holiday.date_to >= holiday_start_utc
                    for holiday in existing_holidays_dict.get(company, [])
                )
                if overlapping:
                    overlapped_holidays = True
                    continue
                if holiday_date in public_holidays_values_dict:
                    public_holidays_values_dict[holiday_date]['name'] += f" / {holiday_name}"
                else:
                    public_holidays_values_dict[holiday_date] = {
                        'name': holiday_name,
                        'date_from': holiday_start_utc,
                        'date_to': holiday_end_utc,
                        'company_id': company.id,
                    }

            new_public_holidays = self.env['resource.calendar.leaves'].with_context(convert_datetime=convert_datetime).create(
                list(public_holidays_values_dict.values()),
            )
            notification = {
                'title': self.env._('Public Holidays Import Notification'),
                'type': 'success',
                'message': self.env._('No new public time off were added as they already exist.'),
            }
            if not new_public_holidays:
                response.append(notification)
            else:
                notification['message'] = self.env._(
                    "Public holidays have been successfully created for %(company)s for the next %(years)s years.",
                    company=company.name, years=len(year_range))
                if overlapped_holidays:
                    notification['message'] += " " + self.env._("Some were overlapping existing ones, not all records have been created.")
                response.append(notification)

        return response

    def load_public_holidays(self, companies=False, convert_datetime=True):
        notifications = []
        current_year = datetime.now().year
        notifications.extend(self._generate_public_holidays(
            year_range=range(current_year, current_year + 5),
            companies=companies or self.env.companies,
            convert_datetime=convert_datetime,
        ))
        for notification in notifications:
            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                notification,
            )

    def _cron_load_current_year_public_holidays(self):
        current_year = datetime.now().year
        self._generate_public_holidays(
            year_range=[current_year, current_year + 1],
            companies=self.env.companies,
            convert_datetime=False,
        )


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    associated_leaves_count = fields.Integer("Time Off Count", compute='_compute_associated_leaves_count')

    def _compute_associated_leaves_count(self):
        leaves_read_group = self.env['resource.calendar.leaves']._read_group(
            [('resource_id', '=', False), '|', ('calendar_id', 'in', self.ids), ('calendar_id', '=', False)],
            ['calendar_id'],
            ['__count'],
        )
        result = {calendar.id if calendar else 'global': count for calendar, count in leaves_read_group}
        global_leave_count = result.get('global', 0)
        for calendar in self:
            calendar.associated_leaves_count = result.get(calendar.id, 0) + global_leave_count


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    leave_date_to = fields.Date(related="user_id.leave_date_to")

    def _format_leave(self, leave, resource_hours_per_day, resource_hours_per_week, ranges_to_remove, start_day, end_day, locale):
        leave_start = leave[0]
        leave_record = leave[2]
        holiday_id = leave_record.holiday_id
        tz = ZoneInfo(self.tz or self.env.user.tz)

        if holiday_id.work_entry_type_request_unit == 'half_day':
            # Half day leaves are limited to half a day within a single day
            leave_day = leave_start.date()
            half_start_datetime = datetime.combine(leave_day, datetime.min.time() if holiday_id.request_date_from_period == "am" else time(12), tzinfo=tz)
            half_end_datetime = datetime.combine(leave_day, time(12) if holiday_id.request_date_from_period == "am" else datetime.max.time(), tzinfo=tz)
            ranges_to_remove.append((half_start_datetime, half_end_datetime, self.env['resource.calendar.attendance']))

            if not self._is_fully_flexible():
                # only days inside the original period
                if start_day <= leave_day <= end_day:
                    resource_hours_per_day[self.id][leave_day] -= holiday_id.number_of_hours
                week = weeknumber(babel_locale_parse(locale), leave_day)
                resource_hours_per_week[self.id][week] -= holiday_id.number_of_hours
        elif holiday_id.work_entry_type_request_unit == 'hour':
            # Custom leaves are limited to a specific number of hours within a single day
            leave_day = leave_start.date()
            range_start_datetime = leave_record.date_from.replace(tzinfo=UTC).astimezone(tz)
            range_end_datetime = leave_record.date_to.replace(tzinfo=UTC).astimezone(tz)
            ranges_to_remove.append((range_start_datetime, range_end_datetime, self.env['resource.calendar.attendance']))

            if not self._is_fully_flexible():
                # only days inside the original period
                if start_day <= leave_day <= end_day:
                    resource_hours_per_day[self.id][leave_day] -= holiday_id.number_of_hours
                week = weeknumber(babel_locale_parse(locale), leave_day)
                resource_hours_per_week[self.id][week] -= holiday_id.number_of_hours
        else:
            super()._format_leave(leave, resource_hours_per_day, resource_hours_per_week, ranges_to_remove, start_day, end_day, locale)
