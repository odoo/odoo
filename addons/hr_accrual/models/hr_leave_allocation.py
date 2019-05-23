# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from math import floor

from odoo import api, models, fields
from odoo.addons.resource.models.resource import HOURS_PER_DAY

class HolidaysAllocation(models.Model):
    _inherit = ['hr.leave.allocation']

    def _update_accrual(self):
        """
            Method called by the cron task in order to increment the number_of_days when
            necessary.
        """
        today = fields.Date.from_string(fields.Date.today())
        start_curr_month = today.replace(day=1)

        holidays = self.search([('accrual', '=', True), ('state', '=', 'validate'), ('holiday_type', '=', 'employee'), ('date_from', '<', today),
                                '|', ('date_to', '=', False), ('date_to', '>', fields.Datetime.now()),
                                '|', ('nextcall', '=', False), ('nextcall', '<=', today)])

        for holiday in holidays:
            values = {}

            delta = relativedelta(days=0)

            if holiday.interval_unit == 'weeks':
                delta = relativedelta(weeks=holiday.interval_number)
            if holiday.interval_unit == 'months':
                delta = relativedelta(months=holiday.interval_number)
            if holiday.interval_unit == 'years':
                delta = relativedelta(years=holiday.interval_number)

            values['nextcall'] = (holiday.nextcall if holiday.nextcall else today) + delta

            period_start = datetime.combine(start_curr_month, time(0, 0, 0)) - delta
            period_end = datetime.combine(start_curr_month, time(0, 0, 0))

            # We have to check when the employee has been created
            # in order to not allocate him/her too much leaves
            start_date = holiday.employee_id._get_date_start_work()
            # If employee is created after the period, we cancel the computation
            if period_end <= start_date:
                holiday.write(values)
                continue

            # If employee created during the period, taking the date at which he has been created
            if period_start <= start_date:
                period_start = start_date

            work_entries = self.env['hr.work.entry'].search([
                ('employee_id', '=', holiday.employee_id.id),
                ('state', '=', 'validated'),
                ('date_start', '>=', period_start),
                ('date_stop', '<=', period_end),
            ])

            hours_per_day = (holiday.employee_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY)
            worked = sum(work_entries.filtered(lambda we: we.work_entry_type_id.is_accrual).mapped('duration')) / hours_per_day
            left = sum(work_entries.filtered(lambda we: not we.work_entry_type_id.is_accrual).mapped('duration')) / hours_per_day

            prorata = worked / (left + worked) if worked else 0
            prorata = floor(prorata * 10) / 10  # round down

            days_to_give = holiday.number_per_interval
            if holiday.unit_per_interval == 'hours':
                # As we encode everything in days in the database we need to convert
                # the number of hours into days for this we use the
                # mean number of hours set on the employee's calendar
                days_to_give = days_to_give / hours_per_day

            values['number_of_days'] = holiday.number_of_days + days_to_give * prorata
            if holiday.accrual_limit > 0:
                values['number_of_days'] = min(values['number_of_days'], holiday.accrual_limit)

            holiday.write(values)
