# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HrHolidaysSummaryEmployee(models.TransientModel):
    _name = 'hr.holidays.summary.employee'
    _description = 'HR Leaves Summary Report By Employee'

    def _default_date_from(self):
        today_date = fields.Date.from_string(fields.Date.today())
        return fields.Date.to_string(today_date + relativedelta(day=1))

    date_from = fields.Date('From', required=True, default=_default_date_from)
    emp = fields.Many2many('hr.employee', 'summary_emp_rel', 'sum_id', 'emp_id', 'Employee(s)')
    holiday_type = fields.Selection([('Approved','Approved'),('Confirmed','Confirmed'),('both','Both Approved and Confirmed')], 'Select Leave Type', required=True, default='Approved')

    @api.multi
    def print_report(self):
        data = self.read()[0]
        data['emp'] = self.env.context.get('active_ids', [])
        datas = {'ids': [], 'model': 'hr.employee', 'form': data}
        return self.env['report'].get_action(self, 'hr_holidays.report_holidayssummary', data=datas)
