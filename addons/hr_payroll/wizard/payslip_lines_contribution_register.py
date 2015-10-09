# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models

class PayslipLinesContributionRegister(models.TransientModel):
    _name = 'payslip.lines.contribution.register'
    _description = 'PaySlip Lines by Contribution Registers'

    date_from = fields.Date(required=True, default=lambda *a: time.strftime('%Y-%m-01'))
    date_to = fields.Date(required=True, default=lambda *a: str(fields.Datetime.from_string(fields.Datetime.now()) + relativedelta(months=+1, day=1, days=-1))[:10])

    @api.multi
    def print_report(self):
        datas = {
             'ids': self.env.context.get('active_ids', []),
             'model': 'hr.contribution.register',
             'form': {'date_to': self.date_to, 'date_from': self.date_from, 'display_name': self._name}
        }
        return self.env['report'].get_action(self, 'hr_payroll.report_contributionregister', data=datas)
