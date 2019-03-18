# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from datetime import time, datetime
from collections import defaultdict
from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    meal_voucher_count = fields.Integer('Number of meal vouchers', compute='_compute_meal_voucher_count', store=True)

    @api.depends('employee_id', 'date_from', 'date_to', 'state')
    def _compute_meal_voucher_count(self):
        """
        Compute the number of meal voucher. One meal voucher is granted for each
        day with more than 4 hours of work.
        """
        # TODO write a test
        datetime_from = datetime.combine(min(self.mapped('date_from')), time.min)
        datetime_to = datetime.combine(max(self.mapped('date_to')), time.max)
        attendance_work_entry_type = self.env.ref('hr_payroll.benefit_type_attendance', raise_if_not_found=False)
        if not attendance_work_entry_type:
            self.write({'meal_voucher_count': 0})
            return

        work_entries = self.env['hr.benefit'].search([
            ('employee_id', 'in', self.mapped('employee_id').ids),
            ('date_start', '<=', datetime_to),
            ('date_stop', '>=', datetime_from),
            ('state', '=', 'validated'),
            ('benefit_type_id.code', '=', attendance_work_entry_type.code),
        ])

        meal_voucher_counts = defaultdict(lambda: defaultdict(int))
        for work_entry in work_entries:
            meal_voucher_counts[work_entry.employee_id][work_entry.date_start.date()] += work_entry.duration  # work entry is supposed to be within a single day

        for payslip in self:
            payslip.meal_voucher_count = sum([
                1
                for day, hours in meal_voucher_counts[payslip.employee_id].items()
                if hours >= 4 and (payslip.date_from <= day <= payslip.date_to)
            ])
