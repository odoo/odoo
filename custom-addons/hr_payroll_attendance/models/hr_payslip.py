#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from datetime import datetime
import pytz

from odoo import api, fields, models, _
from odoo.osv import expression

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    attendance_count = fields.Integer(compute='_compute_attendance_count')

    def _get_attendance_by_payslip(self):
        """
            Find all attendances linked to payslips.

            Note: An attendance is linked to a payslip if it has
            the same employee and the time periods correspond.

            :return: dict with:
                        - key = payslip record
                        - value = attendances recordset linked to payslip
        """
        attendance_by_payslip = defaultdict(lambda: self.env['hr.attendance'])
        slip_by_employee = defaultdict(lambda: self.env['hr.payslip'])
        attendance_domain = []
        for slip in self:
            if slip.contract_id.work_entry_source != 'attendance':
                continue
            slip_by_employee[slip.employee_id.id] |= slip
            attendance_domain = expression.OR([
                attendance_domain,
                [
                    ('employee_id', '=', slip.employee_id.id),
                    ('check_in', '<=', slip.date_to),
                    ('check_out', '>=', slip.date_from),
                ]
            ])
        attendance_group = self.env['hr.attendance']._read_group(attendance_domain, groupby=['employee_id', 'check_in:day'], aggregates=['id:recordset'])
        for employee, check_in, attendance in attendance_group:
            for slip in slip_by_employee[employee.id]:
                if slip.date_from <= check_in.date() <= slip.date_to:
                    attendance_by_payslip[slip] |= attendance
        return attendance_by_payslip

    @api.depends('date_from', 'date_to', 'contract_id')
    def _compute_attendance_count(self):
        attendance_by_payslip = self._get_attendance_by_payslip()
        for slip in self:
            slip.attendance_count = len(attendance_by_payslip[slip])

    def action_open_attendances(self):
        self.ensure_one()
        attendance = self._get_attendance_by_payslip()[self]
        return {
            "type": "ir.actions.act_window",
            "name": _("Attendances"),
            "res_model": "hr.attendance",
            "views": [[False, "tree"]],
            "context": {
                "create": 0
            },
            "domain": [('id', 'in', attendance.ids)]
        }
