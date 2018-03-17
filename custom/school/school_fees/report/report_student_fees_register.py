# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo import models, api


class ReportStudentFeesRegister(models.AbstractModel):
    _name = 'report.school_fees.student_fees_register'

    @api.multi
    def get_month(self, indate):
        new_date = datetime.strptime(indate, '%Y-%m-%d')
        out_date = new_date.strftime('%B') + '-' + new_date.strftime('%Y')
        return out_date

    @api.model
    def render_html(self, docids, data=None):
        ans1 = self.env['student.fees.register'].search([('id', 'in', docids)])
        docargs = {
            'doc_ids': docids,
            'doc_model': ans1,
            'docs': ans1,
            'get_month': self.get_month,
        }
        render_model = 'school_fees.student_fees_register'
        return self.env['report'].render(render_model, docargs)
