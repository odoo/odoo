# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import models
from odoo.addons.resource.models.utils import HOURS_PER_DAY
from odoo.tools import float_round


class HrContract(models.Model):
    _inherit = 'hr.contract'

    def _preprocess_work_hours_data_split_half(self, work_data, date_from, date_to):
        """
        Takes care of removing the extra hours from the work_data aswell as
         adding the necessary data for extra hours lines.
        """
        attendance_contracts = self.filtered(lambda c: c.work_entry_source == 'attendance' and c.wage_type == 'hourly')
        default_work_entry_type = self.structure_type_id.default_work_entry_type_id
        if not attendance_contracts or len(default_work_entry_type) != 1:
            return
        overtime_work_entry_type = self.env.ref('hr_work_entry.overtime_work_entry_type', False)
        if not overtime_work_entry_type:
            return
        overtimes = self.env['hr.attendance.overtime'].sudo().search(
            [('employee_id', 'in', self.employee_id.ids), ('duration', '>', 0),
                ('date', '>=', date_from), ('date', '<=', date_to)],
            order='date asc',
        )
        if not overtimes:
            return

        # Comment to remove, issue with previous version:
        # - next raise StopIteration when iter of work_data become empty (no catch of it)
        # - sum(overtime.duration) should crash......
        # Not sure I get it :D, shouldn't just remove it ???
        work_data_index_by_date = {
            date_start_day: i
            for i, [date_start_day, work_entry_type, __] in enumerate(work_data)
            if work_entry_type.id != default_work_entry_type.id
        }
        total_overtime_not_match = 0
        for overtime in overtimes:
            if overtime.date in work_data_index_by_date:
                row_work_data_index = work_data_index_by_date[overtime.date]
                date_start_day, work_entry_type, hours = work_data[row_work_data_index]
                work_data[work_data_index_by_date[overtime.date]] = (date_start_day, work_entry_type, hours - overtime.duration)
            else:
                total_overtime_not_match += overtime.duration
        work_data.append((False, overtime_work_entry_type, total_overtime_not_match))

    def _get_work_hours_split_half(self, date_from, date_to, domain=None):
        res = super()._get_work_hours_split_half(date_from, date_to, domain=domain)
        overtime_work_entry_type = self.env.ref('hr_work_entry.overtime_work_entry_type', False)
        if not overtime_work_entry_type:
            return res
        overtime_hours = 0
        new_res = res.copy()
        for work_type, dummy in res.items():
            if work_type[1] == overtime_work_entry_type.id:
                dummy, hours = new_res.pop(work_type)
                overtime_hours += hours
        hours_per_day = self.resource_calendar_id.hours_per_day or self.company_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY
        overtime_days = float_round(overtime_hours / hours_per_day, precision_rounding=1, rounding_method='UP')
        if overtime_hours:
            new_res[('full', overtime_work_entry_type.id)] = [overtime_days, overtime_hours]
        return new_res
