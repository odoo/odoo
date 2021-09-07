# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import pytz

from odoo import models
from odoo.addons.resource.models.resource import datetime_to_string

class HrContract(models.Model):
    _inherit = 'hr.contract'

    def _get_contract_work_entries_values(self, date_start, date_stop):
        # Add the work entries difference for french payroll
        # Work entries by default are not generated on days the employee does not work
        # So we have to fill the gaps with work entries for those periods
        result = super()._get_contract_work_entries_values(date_start, date_stop)
        start_dt = pytz.utc.localize(date_start) if not date_start.tzinfo else date_start
        end_dt = pytz.utc.localize(date_stop) if not date_stop.tzinfo else date_stop
        fr_contracts = self.filtered(lambda c: c.company_id.country_id.code == 'FR')
        # l10n_fr_date_to is False when no adjustment had to be done
        all_leaves = self.env['hr.leave'].search([
            ('employee_id', 'in', fr_contracts.employee_id.ids),
            ('state', '=', 'validate'),
            ('date_from', '<=', datetime_to_string(end_dt)),
            ('l10n_fr_date_to', '>=', datetime_to_string(start_dt)),
        ]) if fr_contracts else []
        leaves_per_employee = defaultdict(lambda: self.env['hr.leave'])
        for leave in all_leaves:
            leaves_per_employee[leave.employee_id] |= leave
        for contract in fr_contracts:
            if contract.company_id.country_id.code != 'FR':
                continue
            employee = contract.employee_id
            employee_calendar = contract.resource_calendar_id
            company = contract.company_id
            company_calendar = company.time_off_reference_calendar
            resource = employee.resource_id
            tz = pytz.timezone(employee_calendar.tz)

            for leave in leaves_per_employee[employee]:
                leave_start_dt = max(start_dt, leave.date_from.astimezone(tz))
                leave_end_dt = min(end_dt, leave.date_to.astimezone(tz))
                leave_end_dt_fr = min(end_dt, leave.l10n_fr_date_to.astimezone(tz))

                # Compute the attendances for the company calendar and the employee calendar
                # and then compute and keep the difference between those two
                employee_attendances = employee_calendar._attendance_intervals_batch(
                    leave_start_dt, leave_end_dt, resources=resource, tz=tz,
                )[resource.id]
                company_attendances = company_calendar._attendance_intervals_batch(
                    leave_start_dt, leave_end_dt_fr, resources=resource, tz=tz,
                )[resource.id]
                # Dates on which work entries should already be generated
                employee_dates = set()
                for interval in employee_attendances:
                    employee_dates.add(interval[0].date())
                    employee_dates.add(interval[1].date())
                leave_work_entry_type = leave.holiday_status_id.work_entry_type_id
                result += [{
                    'name': '%s%s' % (leave_work_entry_type.name + ': ' if leave_work_entry_type else "", employee.name),
                    'date_start': interval[0].astimezone(pytz.utc).replace(tzinfo=None),
                    'date_stop': interval[1].astimezone(pytz.utc).replace(tzinfo=None),
                    'work_entry_type_id': leave_work_entry_type.id,
                    'employee_id': employee.id,
                    'company_id': contract.company_id.id,
                    'state': 'draft',
                    'contract_id': contract.id,
                    'leave_id': leave.id,
                } for interval in company_attendances if interval[0].date() not in employee_dates]

        return result
