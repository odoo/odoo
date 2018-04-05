# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.datetime import date


class HolidaysSummaryDept(models.TransientModel):

    _name = 'hr.holidays.summary.dept'
    _description = 'HR Leaves Summary Report By Department'

    date_from = fields.Date(string='From', required=True, default=lambda *a: date.today().start_of('month'))
    depts = fields.Many2many('hr.department', 'summary_dept_rel', 'sum_id', 'dept_id', string='Department(s)')
    holiday_type = fields.Selection([
        ('Approved', 'Approved'),
        ('Confirmed', 'Confirmed'),
        ('both', 'Both Approved and Confirmed')
    ], string='Leave Type', required=True, default='Approved')

    @api.multi
    def print_report(self):
        self.ensure_one()
        [data] = self.read()
        if not data.get('depts'):
            raise UserError(_('You have to select at least one Department. And try again.'))
        departments = self.env['hr.department'].browse(data['depts'])
        datas = {
            'ids': [],
            'model': 'hr.department',
            'form': data
        }
        return self.env.ref('hr_holidays.action_report_holidayssummary').with_context(from_transient_model=True).report_action(departments, data=datas)
