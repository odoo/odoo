# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class HrAttendanceOvertime(models.Model):
    _name = "hr.attendance.overtime"
    _description = "Attendance Overtime"
    _rec_name = 'employee_id'
    _order = 'date desc'

    def _default_employee(self):
        return self.env.user.employee_id

    employee_id = fields.Many2one(
        'hr.employee', string="Employee", default=_default_employee,
        required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='employee_id.company_id')

    date = fields.Date(string='Day')
    duration = fields.Float(string='Extra Hours', default=0.0, required=True)
    duration_real = fields.Float(
        string='Extra Hours (Real)', default=0.0,
        help="Extra-hours including the threshold duration")
    adjustment = fields.Boolean(default=False)
    active = fields.Boolean(compute='_compute_active', search='_search_active', store=False)

    def init(self):
        # Allows only 1 overtime record per employee per day unless it's an adjustment
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS hr_attendance_overtime_unique_employee_per_day
            ON %s (employee_id, date)
            WHERE adjustment is false""" % (self._table))

    @api.depends('date', 'company_id.overtime_start_date')
    def _compute_active(self):
        for overtime in self:
            start_date = overtime.company_id.overtime_start_date
            overtime.active = start_date and overtime.date >= start_date

    @api.model
    def _search_active(self, operator, value):
        if operator not in ('=', '!='):
            raise UserError(_("Operation not supported"))
        is_true = (operator, bool(value)) in (('=', True), ('!=', False))
        operator = 'inselect' if is_true else 'not inselect'
        subquery = """
            SELECT ot.id FROM hr_attendance_overtime ot
            LEFT JOIN hr_employee emp ON emp.id = ot.employee_id
            LEFT JOIN res_company com ON com.id = emp.company_id
            WHERE ot.date >= com.overtime_start_date"""
        return [('id', operator, (subquery, []))]
