# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime

from odoo.tools import amount_to_text_en
from odoo import api, models


class payroll_advice_report(models.AbstractModel):
    _name = 'report.l10n_in_hr_payroll.report_payrolladvice'

    def get_month(self, input_date):
        res = {
               'from_name': '', 'to_name': ''
               }
        slip = self.env['hr.payslip'].search([('date_from', '<=', input_date), ('date_to', '>=', input_date)], limit=1)
        if slip:
            from_date = datetime.strptime(slip.date_from, '%Y-%m-%d')
            to_date = datetime.strptime(slip.date_to, '%Y-%m-%d')
            res['from_name'] = from_date.strftime('%d') + '-' + from_date.strftime('%B') + '-' + from_date.strftime('%Y')
            res['to_name'] = to_date.strftime('%d') + '-' + to_date.strftime('%B') + '-' + to_date.strftime('%Y')
        return res

    def convert(self, amount, cur):
        return amount_to_text_en.amount_to_text(amount, 'en', cur)

    def get_bysal_total(self):
        return self.total_bysal

    def get_detail(self, line_ids):
        result = []
        self.total_bysal = 0.00
        for l in line_ids:
            res = {}
            res.update({
                    'name': l.employee_id.name,
                    'acc_no': l.name,
                    'ifsc_code': l.ifsc_code,
                    'bysal': l.bysal,
                    'debit_credit': l.debit_credit,
                    })
            self.total_bysal += l.bysal
            result.append(res)
        return result

    @api.model
    def get_report_values(self, docids, data=None):
        advice = self.env['hr.payroll.advice'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hr.payroll.advice',
            'data': data,
            'docs': advice,
            'time': time,
            'get_month': self.get_month,
            'convert': self.convert,
            'get_detail': self.get_detail,
            'get_bysal_total': self.get_bysal_total,
        }
