# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, time, timedelta
from pytz import timezone

from odoo import api, fields, models
from odoo.addons.resource.models.utils import timezone_datetime


class HrLeave(models.Model):
    _inherit = "hr.leave"

    @api.model
    def _gantt_unavailability(self, field, res_ids, start, stop, scale):
        if (field != "employee_id"):
            return super()._gantt_unavailability(field, res_ids, start, stop, scale)

        start_date = fields.Datetime.to_string(start)
        stop_date = fields.Datetime.to_string(stop)
        employees = self.env['hr.employee'].browse(res_ids)
        leaves_mapping = defaultdict(list)
        employee_contracts = self.env['hr.contract'].sudo().search([
            ('state', '!=', 'cancel'),
            ('employee_id', 'in', employees.ids),
            ('date_start', '<=', stop_date),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', start_date),
        ])

        employee_with_contracts = employee_contracts.employee_id
        employees_without_contracts = employees - employee_with_contracts

        # For employees without contracts
        leaves_mapping.update(
            employees_without_contracts.resource_id._get_unavailable_intervals(start, stop))

        # For employees with contracts
        for contract in employee_contracts:
            if not contract.resource_calendar_id:
                continue
            tmp_date_from = max(
                start,
                datetime.combine(contract.date_start, time.min))
            tmp_date_to = min(
                stop,
                datetime.combine(contract.date_end, time.max)) if contract.date_end else stop
            resources_unavailable_intervals = contract.resource_calendar_id._unavailable_intervals_batch(
                timezone_datetime(tmp_date_from),
                timezone_datetime(tmp_date_to),
                contract.employee_id.resource_id,
                tz=timezone(contract.resource_calendar_id.tz))
            for key, value in resources_unavailable_intervals.items():
                leaves_mapping[key] += value

        cell_dt = timedelta(hours=1) if scale in ['day', 'week'] else timedelta(hours=12)

        result = {}
        for employee in employees:
            # remove intervals smaller than a cell, as they will cause half a cell to turn grey
            # ie: when looking at a week, a employee start everyday at 8, so there is a unavailability
            # like: 2019-05-22 20:00 -> 2019-05-23 08:00 which will make the first half of the 23's cell grey
            notable_intervals = filter(lambda interval: interval[1] - interval[0] >= cell_dt, leaves_mapping.get(employee.resource_id.id, []))
            result[employee.id] = [{'start': interval[0], 'stop': interval[1]} for interval in notable_intervals]

        return result
