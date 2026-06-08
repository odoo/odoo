# Part of Odoo. See LICENSE file for full copyright and licensing details.

import csv
from collections import defaultdict
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from markupsafe import Markup, escape

from odoo import Command, api, fields, models
from odoo.tools import file_open, file_path
from odoo.tools.date_utils import convert_timezone


class LoadPublicHolidaysWizard(models.TransientModel):
    _name = 'load.public.holiday.wizard'
    _description = 'Public Holiday Preview Wizard'

    year = fields.Integer(required=True, default=lambda self: fields.Date.context_today(self).year)
    warning_message = fields.Html(compute='_compute_warning_message')
    line_ids = fields.One2many(
        'load.public.holiday.wizard.line', 'wizard_id',
        string="Public Holidays", compute='_compute_line_ids', store=True, readonly=False,
    )

    @api.depends('year')
    def _compute_warning_message(self):
        for wizard in self:
            wizard.warning_message = False
            if wizard.year and wizard.year > 0:
                prepared_public_holidays = wizard._prepare_public_holidays_data()
                warning_messages = wizard._get_warning_messages(prepared_public_holidays)
                if warning_messages:
                    wizard.warning_message = Markup('<ul class="mb-0">%s</ul>') % Markup('').join(
                        Markup('<li>%s</li>') % escape(warning_message)
                        for warning_message in warning_messages
                    )

    @api.depends('year')
    def _compute_line_ids(self):
        for wizard in self:
            commands = [Command.clear()]
            if wizard.year and 2025 < wizard.year < 9999:
                prepared_public_holidays = wizard._prepare_public_holidays_data()
                preview_values = [
                    public_holiday_value
                    for company_data in prepared_public_holidays['prepared_public_holidays'].values()
                    for public_holiday_value in company_data
                ]
                commands.extend(
                    Command.create({
                        'name': preview_value['name'],
                        'start_date': preview_value['start_date'],
                        'company_id': preview_value['company_id'],
                    })
                    for preview_value in preview_values
                )
            wizard.line_ids = commands

    def action_add_public_holidays(self):
        self.ensure_one()
        prepared_public_holidays = self._prepare_public_holidays_data()
        warning_messages = self._get_warning_messages(prepared_public_holidays)
        notification_messages = []
        convert_datetime = self.env.context.get('public_holiday_convert_datetime', True)
        for company_id, create_values in self._get_create_values_by_company().items():
            company = self.env['res.company'].browse(company_id)
            created_leaves = self.env['resource.calendar.leaves'].with_context(convert_datetime=convert_datetime).create(create_values)
            if created_leaves:
                notification_messages.append(self.env._(
                    'Created %(count)s public holiday(s) for %(company)s.',
                    count=len(created_leaves),
                    company=company.name,
                ))
        notification_messages.extend(warning_messages)
        next_action = {'type': 'ir.actions.act_window_close'}
        if self.env.context.get('params', {}).get('view_type') == 'list':
            next_action = {'type': 'ir.actions.client', 'tag': 'reload'}
        notification_type = 'success' if notification_messages and not warning_messages else 'warning'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': notification_type,
                'message': '\n'.join(notification_messages) or self.env._("No public holidays were added."),
                'next': next_action,
            },
        }

    def _prepare_public_holidays_data(self):
        companies = self.env.companies
        prepared_public_holidays = {}
        companies_without_country = self.env['res.company']
        companies_without_public_holidays = self.env['res.company']
        companies_with_all_existing_holidays = self.env['res.company']
        existing_holidays_dict = dict(self.env["resource.calendar.leaves"]._read_group(
            domain=[
                ('company_id', 'in', companies.ids),
                ('date_from', '<=', datetime(self.year, 12, 31, 0, 0, 0)),
                ('date_to', '>=', datetime(self.year, 1, 1, 0, 0, 0)),
                ('resource_id', '=', False),
            ],
            groupby=['company_id'],
            aggregates=['id:recordset'],
        ))

        for company in companies:
            if not company.country_code:
                companies_without_country |= company
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
                    if holiday_date.year > self.year:
                        break
                    if holiday_date.year != self.year:
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
                            'start_date': holiday_date,
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

    def _get_warning_messages(self, prepared_public_holidays):
        self.ensure_one()
        warning_messages = []
        if prepared_public_holidays['companies_with_all_existing_holidays']:
            warning_messages.append(self.env._(
                "All public holidays for %(year)s are already present for: %(companies)s.",
                year=self.year,
                companies=', '.join(prepared_public_holidays['companies_with_all_existing_holidays'].mapped('name')),
            ))
        if prepared_public_holidays['companies_without_country']:
            warning_messages.append(self.env._(
                "These companies do not have a country set: %(companies)s.",
                companies=', '.join(prepared_public_holidays['companies_without_country'].mapped('name')),
            ))
        if prepared_public_holidays['companies_without_public_holidays']:
            warning_messages.append(self.env._(
                "Public holiday data is not available for %(year)s for: %(companies)s.",
                year=self.year,
                companies=', '.join(prepared_public_holidays['companies_without_public_holidays'].mapped('name')),
            ))
        return warning_messages

    def _get_create_values_by_company(self):
        self.ensure_one()
        values_by_company = defaultdict(list)
        companies = self.env.companies
        for line in self.line_ids:
            company = line.company_id
            if company not in companies:
                continue
            company_tz = ZoneInfo(company.tz or 'UTC')
            create_values = {
                'name': line.name,
                'date_from': convert_timezone(datetime.combine(line.start_date, time.min), UTC, company_tz),
                'date_to': convert_timezone(datetime.combine(line.start_date, time.max), UTC, company_tz),
                'company_id': company.id,
            }
            work_entry_type = line.work_entry_type_id
            if work_entry_type:
                create_values.update({
                    'work_entry_type_id': work_entry_type.id,
                    'count_as': work_entry_type.count_as,
                    'elligible_for_accrual_rate': work_entry_type.elligible_for_accrual_rate,
                })
            values_by_company[company.id].append(create_values)
        return values_by_company
