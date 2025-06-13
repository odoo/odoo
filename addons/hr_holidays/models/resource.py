# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
import warnings
from datetime import datetime, time

from odoo import api, fields, models, _
from odoo.fields import Domain
from odoo.exceptions import ValidationError
from odoo.tools.date_utils import convert_timezone

warnings.filterwarnings("ignore", category=DeprecationWarning)
import holidays  # noqa: E402


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    holiday_id = fields.Many2one("hr.leave", string='Time Off Request')

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
        leaves.sudo().write({
            'state': 'confirm',
        })
        self.env.add_to_compute(self.env['hr.leave']._fields['number_of_days'], leaves)
        self.env.add_to_compute(self.env['hr.leave']._fields['duration_display'], leaves)
        sick_time_status = self.env.ref('hr_holidays.leave_type_sick_time_off', raise_if_not_found=False)
        leaves_to_recreate = self.env['hr.leave']
        for previous_duration, leave, state in zip(previous_durations, leaves, previous_states):
            duration_difference = previous_duration - leave.number_of_days
            message = False
            if duration_difference > 0 and leave.holiday_status_id.requires_allocation:
                message = _("Due to a change in global time offs, you have been granted %s day(s) back.", duration_difference)
            if leave.number_of_days > previous_duration\
                    and (not sick_time_status or leave.holiday_status_id not in sick_time_status):
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

    def _convert_timezone(self, utc_naive_datetime, tz_from, tz_to):
        """
            Convert a naive date to another timezone that initial timezone
            used to generate the date.
            :param utc_naive_datetime: utc date without tzinfo
            :type utc_naive_datetime: datetime
            :param tz_from: timezone used to obtained `utc_naive_datetime`
            :param tz_to: timezone in which we want the date
            :return: datetime converted into tz_to without tzinfo
            :rtype: datetime
        """
        naive_datetime_from = utc_naive_datetime.astimezone(tz_from).replace(tzinfo=None)
        aware_datetime_to = tz_to.localize(naive_datetime_from)
        utc_naive_datetime_to = aware_datetime_to.astimezone(pytz.utc).replace(tzinfo=None)
        return utc_naive_datetime_to

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

    def _prepare_public_holidays_values(self, vals_list):
        for vals in vals_list:
            # Manage the case of create a Public Time Off in another timezone
            # The datetime created has to be in UTC for the calendar's timezone
            if not vals.get('calendar_id') or vals.get('resource_id') or \
                not isinstance(vals.get('date_from'), (datetime, str)) or \
                not isinstance(vals.get('date_to'), (datetime, str)):
                continue
            user_tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc
            calendar_tz = pytz.timezone(self.env['resource.calendar'].browse(vals['calendar_id']).tz)
            if user_tz != calendar_tz and self.env.context.get('convert_datetime', True):
                datetime_from = self._ensure_datetime(vals['date_from'], '%Y-%m-%d %H:%M:%S')
                datetime_to = self._ensure_datetime(vals['date_to'], '%Y-%m-%d %H:%M:%S')
                if datetime_from and datetime_to:
                    vals['date_from'] = self._convert_timezone(datetime_from, user_tz, calendar_tz)
                    vals['date_to'] = self._convert_timezone(datetime_to, user_tz, calendar_tz)
        return vals_list

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = self._prepare_public_holidays_values(vals_list)
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

    def _generate_public_holidays(self, companies, year_range, convert_datetime=True):
        response = []
        subdivision_per_country_dict = holidays.list_supported_countries(include_aliases=True)
        lang_per_country = holidays.list_localized_countries(include_aliases=True)
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
            if company.country_code not in subdivision_per_country_dict:
                response.append({
                    'title': self.env._('No Public Holidays'),
                    'type': 'danger',
                    'message': self.env._('Public holidays are not available for %(country)s country.', country=company.country_id.name),
                })
                continue

            company_subdiv = company.state_id.code[-2:] if company.state_id else None  # Code is in the format 'XX-YY', where XX is the country code and YY is the subdivision code
            holidays_subdivs = subdivision_per_country_dict.get(company.country_code, None)
            user_lang_iso_code = self.env["res.lang"]._lang_get(self.env.user.lang).iso_code[:2]
            if not user_lang_iso_code or user_lang_iso_code not in lang_per_country.get(company.country_code, []):
                user_lang_iso_code = 'en_US'

            public_holiday_dict = holidays.country_holidays(
                company.country_code,
                subdiv=company_subdiv if company_subdiv and company_subdiv in holidays_subdivs else None,
                years=year_range,
                language=user_lang_iso_code,
                observed=False,
            )

            overlapped_holidays = False
            company_tz = pytz.timezone(company.resource_calendar_id.tz)
            public_holidays_values_dict = {}

            for holiday_date, holiday_name in public_holiday_dict.items():
                holiday_start_utc = convert_timezone(datetime.combine(holiday_date, time.min), pytz.utc, company_tz)
                holiday_end_utc = convert_timezone(datetime.combine(holiday_date, time.max), pytz.utc, company_tz)
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
        if not companies:
            companies = self.env.companies
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
            [('resource_id', '=', False), ('calendar_id', 'in', self.ids)],
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
