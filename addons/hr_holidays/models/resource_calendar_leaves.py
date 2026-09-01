# Part of Odoo. See LICENSE file for full copyright and licensing details.

import csv
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from odoo import api, fields, models, modules
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import config, file_open, file_path
from odoo.tools.date_utils import convert_timezone


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    holiday_id = fields.Many2one("hr.leave", string='Time Off Request')
    elligible_for_accrual_rate = fields.Boolean(string='Eligible for Accrual Rate', default=False,
        help="If checked, this time type will be taken into account for accruals computation.")

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
                    existing_leaves = existing_leaves.filtered(
                        lambda leave: not leave.calendar_id or leave.calendar_id == record.calendar_id)
                if existing_leaves:
                    raise ValidationError(self.env._('Two public holidays cannot overlap each other for the same working hours.'))

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
            'company_id': record.company_id.id,
            'date_from': record.date_from,
            'date_to': record.date_to,
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
        leaves.sudo().write({
            'state': 'confirm',
        })
        sick_time_status = self.env['hr.work.entry.type'].search([('code', '=', '013.00')])
        leaves_to_recreate = self.env['hr.leave']
        for previous_duration, leave, state in zip(previous_durations, leaves, previous_states):
            duration_difference = previous_duration - leave.number_of_days
            message = False
            if duration_difference > 0 and leave.work_entry_type_id.requires_allocation:
                message = self.env._(
                    "Due to a change in global time offs, you have been granted %s day(s) back.",
                    duration_difference)
            if leave.number_of_days > previous_duration\
                    and (not sick_time_status or leave.work_entry_type_id not in sick_time_status):
                message = self.env._(
                    "Due to a change in global time offs, %s extra day(s) have been taken from your allocation. Please review this leave if you need it to be changed.",
                    (-1 * duration_difference))
            try:
                leave.sudo().write({'state': state})  # sudo in order to skip _check_approval_update
                leave._check_validity()
                if leave.state == 'validate':
                    # recreate the resource leave that were removed by writing state to draft
                    leaves_to_recreate |= leave
            except ValidationError:
                leave.action_refuse()
                message = self.env._(
                    "Due to a change in global time offs, this leave no longer has the required amount of available allocation and has been set to refused. Please review this leave.")
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
        if isinstance(datetime_representation, str) and date_format:
            return datetime.strptime(datetime_representation, date_format)
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

    def load_public_holidays(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Load Public Holidays'),
            'res_model': 'load.public.holiday.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def _prepare_public_holidays_data(self, start_date, end_date):
        companies = self.env.companies
        prepared_public_holidays = {}
        companies_without_country = self.env['res.company']
        companies_without_public_holidays = self.env['res.company']
        companies_with_all_existing_holidays = self.env['res.company']
        existing_holidays_dict = dict(self.env["resource.calendar.leaves"]._read_group(
            domain=[
                ('company_id', 'in', companies.ids),
                ('date_from', '<=', end_date),
                ('date_to', '>=', start_date),
                ('resource_id', '=', False),
            ],
            groupby=['company_id'],
            aggregates=['id:recordset'],
        ))

        for company in companies:
            if not company.country_code:
                companies_without_country |= company
                continue

            if not self.sudo().env['hr.work.entry.type'].search([('code', '=', '006.00'), ('country_code', '!=', company.country_code)], limit=1):
                continue
            try:
                csv_file_path = file_path(f"hr_holidays/data/public_holidays/public_holidays_{company.country_code.lower()}.csv")
            except FileNotFoundError:
                companies_without_public_holidays |= company
                continue

            company_tz = ZoneInfo(company.tz or self.env.user.tz or 'UTC')
            public_holidays_values_dict = {}
            has_holidays_for_year = False
            with file_open(csv_file_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row.get("date") or not row.get("holiday"):
                        continue
                    holiday_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
                    if holiday_date > end_date:
                        break
                    if holiday_date < start_date:
                        continue

                    has_holidays_for_year = True
                    holiday_start_utc = convert_timezone(datetime.combine(holiday_date, time.min), UTC, company_tz)
                    holiday_end_utc = convert_timezone(datetime.combine(holiday_date, time.max), UTC, company_tz)
                    overlapping = any(
                        holiday.date_from <= holiday_end_utc and holiday.date_to >= holiday_start_utc
                        for holiday in existing_holidays_dict.get(company, [])
                    )
                    if overlapping:
                        continue

                    holiday_name = row["holiday"].strip()
                    if holiday_date in public_holidays_values_dict:
                        public_holidays_values_dict[holiday_date]['name'] += f" / {holiday_name}"
                    else:
                        public_holidays_values_dict[holiday_date] = {
                            'name': holiday_name,
                            'date_from': holiday_date,
                            'date_to': holiday_date,
                            'company_id': company.id,
                        }

            if public_holidays_values_dict:
                prepared_public_holidays[company.id] = list(public_holidays_values_dict.values())
            elif not has_holidays_for_year:
                companies_without_public_holidays += company
            else:
                companies_with_all_existing_holidays += company

        return {
            'prepared_public_holidays': prepared_public_holidays,
            'companies_without_country': companies_without_country,
            'companies_without_public_holidays': companies_without_public_holidays,
            'companies_with_all_existing_holidays': companies_with_all_existing_holidays,
        }

    def _cron_generate_public_holidays(self):
        if config['test_enable'] or modules.module.current_test:
            return
        start_date = fields.Date.today()
        end_date = fields.Date.add(fields.Date.today(), years=1)
        prepared_public_holidays = self._prepare_public_holidays_data(start_date, end_date)['prepared_public_holidays']
        if prepared_public_holidays:
            create_values = [
                public_holiday_value
                for company_data in prepared_public_holidays.values()
                for public_holiday_value in company_data
            ]
            self.env['resource.calendar.leaves'].sudo().create(create_values)
