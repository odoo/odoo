# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class HrContract(models.Model):
    _inherit = 'hr.contract'

    def _preprocess_work_hours_data(self, work_data, date_from, date_to):
        """
        Removes extra hours from attendance work data and add a new entry for extra hours
        """
        attendance_contracts = self.filtered(lambda c: c.work_entry_source == 'attendance' and c.wage_type == 'hourly')
        overtime_work_entry_type = self.env.ref('hr_work_entry.overtime_work_entry_type', False)
        default_work_entry_type = self.structure_type_id.default_work_entry_type_id
        if not attendance_contracts or not overtime_work_entry_type or len(default_work_entry_type) != 1:
            return
        overtime_hours = self.env['hr.attendance.overtime']._read_group(
            [('employee_id', 'in', self.employee_id.ids),
                ('date', '>=', date_from), ('date', '<=', date_to)],
            [], ['duration:sum'],
        )[0][0]
        if not overtime_hours or overtime_hours < 0:
            return
        work_data[default_work_entry_type.id] -= overtime_hours
        work_data[overtime_work_entry_type.id] = overtime_hours
