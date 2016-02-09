# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrHolidaysSummaryDept(models.TransientModel):
    _name = 'hr.holidays.summary.dept'
    _description = 'HR Leaves Summary Report By Department'

    def _default_date_from(self):
        today_date = fields.Date.from_string(fields.Date.today())
        return fields.Date.to_string(today_date + relativedelta(day=1))

    date_from = fields.Date('From', required=True, default=_default_date_from)
    depts = fields.Many2many('hr.department', 'summary_dept_rel', 'sum_id', 'dept_id', 'Department(s)')
    holiday_type = fields.Selection([('Approved','Approved'),('Confirmed','Confirmed'),('both','Both Approved and Confirmed')], 'Leave Type', required=True, default='Approved')

    @api.multi
    def print_report(self):
        data = self.read()[0]
        if not data['depts']:
            raise UserError(_('You have to select at least one Department. And try again.'))
        datas = {'ids': [], 'model': 'hr.department', 'form': data}
        return self.env['report'].get_action(self, 'hr_holidays.report_holidayssummary', data=datas)
