#-*- coding:utf-8 -*-

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PayslipReport(models.AbstractModel):
    _name = 'report.hr_payroll.report_payslip'

    def get_payslip_lines(self, payslip_lines):
        return payslip_lines.filtered(lambda x: x.appears_on_payslip)

    @api.multi
    def render_html(self, data=None):
        Report = self.env['report']
        report = Report._get_report_from_name('hr_payroll.report_payslip')
        payslip = self.env['hr.payslip'].browse(self.ids)
        docargs = {
            'doc_ids': self.ids,
            'doc_model': report.model,
            'docs': payslip,
            'data': data,
            'get_payslip_lines': self.get_payslip_lines(payslip.line_ids),
        }
        return Report.render('hr_payroll.report_payslip', docargs)
