# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from markupsafe import Markup, escape

from odoo import Command, api, fields, models
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
                start_date = date(wizard.year, 1, 1)
                end_date = date(wizard.year, 12, 31)
                prepared_public_holidays = self.env['resource.calendar.leaves']._prepare_public_holidays_data(start_date, end_date)
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
                start_date = date(wizard.year, 1, 1)
                end_date = date(wizard.year, 12, 31)
                prepared_public_holidays = self.env['resource.calendar.leaves']._prepare_public_holidays_data(start_date, end_date)
                preview_values = [
                    public_holiday_value
                    for company_data in prepared_public_holidays['prepared_public_holidays'].values()
                    for public_holiday_value in company_data
                ]
                commands.extend(
                    Command.create({
                        'name': preview_value['name'],
                        'start_date': preview_value['date_from'],
                        'company_id': preview_value['company_id'],
                    })
                    for preview_value in preview_values
                )
            wizard.line_ids = commands

    def action_add_public_holidays(self):
        self.ensure_one()
        if self.line_ids.filtered(lambda line: not line.work_entry_type_id):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': self.env._("Please select a work entry type for all public holidays before adding them."),
                },
            }
        start_date = date(self.year, 1, 1)
        end_date = date(self.year, 12, 31)
        prepared_public_holidays = self.env['resource.calendar.leaves']._prepare_public_holidays_data(start_date, end_date)
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
