# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo import models, api


class ReportStudentPayslip(models.AbstractModel):
    _name = 'report.school_fees.student_payslip'

    @api.multi
    def get_month(self, indate):
        new_date = datetime.strptime(indate, '%Y-%m-%d')
        out_date = new_date.strftime('%B') + '-' + new_date.strftime('%Y')
        return out_date

    @api.model
    def render_html(self, docids, data=None):
        ans = self.env['student.payslip'].search([('id', 'in', docids)])
        docargs = {
            'doc_ids': docids,
            'doc_model': ans,
            'docs': ans,
            'get_month': self.get_month,
        }
        render_model = 'school_fees.student_payslip'
        return self.env['report'].render(render_model, docargs)
