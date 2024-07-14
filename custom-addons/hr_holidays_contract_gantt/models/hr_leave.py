# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, time, timedelta
from pytz import timezone

from odoo import api, fields, models
from odoo.addons.resource.models.utils import timezone_datetime
from odoo.addons.hr_holidays_gantt.models.hr_leave import tag_employee_rows, traverse


class HrLeave(models.Model):
    _inherit = "hr.leave"

    @api.model
    def gantt_unavailability(self, start_date, end_date, scale, group_bys=None, rows=None):
        start_datetime = fields.Datetime.from_string(start_date)
        end_datetime = fields.Datetime.from_string(end_date)
        employee_ids = tag_employee_rows(rows)
        employees = self.env['hr.employee'].browse(employee_ids)

        employee_contracts = self.env['hr.contract'].sudo().search([
            ('state', '!=', 'cancel'),
            ('employee_id', 'in', employees.ids),
            ('date_start', '<=', end_date),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', start_date),
        ])
        if not employee_contracts:
            leaves_mapping = employees.mapped('resource_id')._get_unavailable_intervals(start_datetime, end_datetime)
        else:
            leaves_mapping = defaultdict(lambda: [])
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
            for contract in employee_contracts:
                tmp_date_from = max(
                    start_datetime,
                    datetime.combine(contract.date_start, time.min))
                tmp_date_to = min(
                    end_datetime,
                    datetime.combine(contract.date_end, time.max)) if contract.date_end else end_datetime
                resources_unavailable_intervals = contract.resource_calendar_id._unavailable_intervals_batch(
                    timezone_datetime(tmp_date_from),
                    timezone_datetime(tmp_date_to),
                    contract.employee_id.resource_id,
                    tz=timezone(contract.resource_calendar_id.tz))
                for key, value in resources_unavailable_intervals.items():
                    leaves_mapping[key] += value

        cell_dt = timedelta(hours=1) if scale in ['day', 'week'] else timedelta(hours=12)

        # for a single row, inject unavailability data
        def inject_unvailabilty(row):
            new_row = dict(row)

            if row.get('employee_id'):
                employee_id = self.env['hr.employee'].browse(row['employee_id'])
                if employee_id:
                    # remove intervals smaller than a cell, as they will cause half a cell to turn grey
                    # ie: when looking at a week, a employee start everyday at 8, so there is a unavailability
                    # like: 2019-05-22 20:00 -> 2019-05-23 08:00 which will make the first half of the 23's cell grey
                    notable_intervals = filter(lambda interval: interval[1] - interval[0] >= cell_dt, leaves_mapping[employee_id.resource_id.id])
                    new_row['unavailabilities'] = [{'start': interval[0], 'stop': interval[1]} for interval in notable_intervals]
            return new_row

        return [traverse(inject_unvailabilty, row) for row in rows]
