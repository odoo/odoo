# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

import pytz

from odoo import models


def employee_tz_to_utc(dt, employee):
    return pytz.timezone(employee.tz or 'UTC').localize(dt).astimezone(pytz.utc)


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    def _get_employee_calendar(self, employee=None, date_from=None, date_to=None):
        calendars = super()._get_employee_calendar(employee=employee, date_from=date_from, date_to=date_to)

        if not date_from and not date_to:
            return calendars

        # Remove tzinfo from dates to use with open
        if date_from.tzinfo not in (None, pytz.utc) or date_to.tzinfo not in (None, pytz.utc):
            raise RuntimeError('Dates need to be in utc')

        date_from = date_from.replace(tzinfo=None)
        date_to = date_to.replace(tzinfo=None)

        if not employee:
            self.ensure_one()
            employee = self.employee_id

        # Overwrite calendars to split by contract
        contract_calendars = []

        # Find employee contract for the given date
        contracts = employee.sudo().contract_ids.filtered_domain([
            ('date_start', '<=', date_to),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', date_from),
        ])

        contract_calendars = sorted(
            [{
                'from': employee_tz_to_utc(datetime.combine(contract.date_start, datetime.min.time()), employee),
                'to': contract.date_end and employee_tz_to_utc(datetime.combine(contract.date_end, datetime.min.time()), employee),
                'calendar': contract.resource_calendar_id,
            } for contract in contracts],
            key=lambda x: x['from'],
        )

        if contract_calendars:
            return contract_calendars

        return calendars
