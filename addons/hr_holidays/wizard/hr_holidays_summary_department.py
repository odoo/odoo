# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class HrHolidaysSummaryDepartmentWizard(models.TransientModel):
    _name = 'hr.holidays.summary.department'
    _description = 'HR Leaves Summary Report By Department'

    date_from = fields.Date(string='From', required=True,
        default=lambda self: time.strftime('%Y-%m-01'))
    depts = fields.Many2many('hr.department', 'summary_dept_rel', 'sum_id', 'dept_id',
        string='Department(s)')
    holiday_type = fields.Selection([
        ('approved', 'Approved'),
        ('confirmed', 'Confirmed'),
        ('both', 'Both Approved and Confirmed')
    ], string='Leave Type', required=True, default='approved')

    @api.multi
    def print_report(self):
        record = self.read()[0]
        if not record['depts']:
            raise UserError(_('You have to select at least one Department. And try again.'))
        datas = {
            'model': 'hr.department',
            'form': record
        }
        return self.env['report'].get_action(self,
            'hr_holidays.report_holidayssummary', data=datas)
