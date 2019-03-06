# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, models


class payroll_advice_report(models.AbstractModel):
    _name = 'report.l10n_in_hr_payroll.report_payrolladvice'
    _description = "Indian Payroll Advice Report"

    def get_month(self, input_date):
        res = {
               'from_name': '', 'to_name': ''
               }
        slip = self.env['hr.payslip'].search([('date_from', '<=', input_date), ('date_to', '>=', input_date)], limit=1)
        if slip:
            from_date = slip.date_from
            to_date = slip.date_to
            res['from_name'] = from_date.strftime('%d') + '-' + from_date.strftime('%B') + '-' + from_date.strftime('%Y')
            res['to_name'] = to_date.strftime('%d') + '-' + to_date.strftime('%B') + '-' + to_date.strftime('%Y')
        return res

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
    def _get_report_values(self, docids, data=None):
        advice = self.env['hr.payroll.advice'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hr.payroll.advice',
            'data': data,
            'docs': advice,
            'time': time,
            'get_month': self.get_month,
            'get_detail': self.get_detail,
            'get_bysal_total': self.get_bysal_total,
        }
