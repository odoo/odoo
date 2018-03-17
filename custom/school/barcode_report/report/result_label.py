# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.


from odoo import api, models


class ReportLabel(models.AbstractModel):

    _name = 'report.barcode_report.result_label'

    def get_student_info(self, standard_id, division_id, medium_id, year_id):
        student_obj = self.env['student.student']
        student_ids = student_obj.search([('standard_id', '=', standard_id),
                                          ('division_id', '=', division_id),
                                          ('medium_id', '=', medium_id),
                                          ('year', '=', year_id)])
        result = []
        for student in student_obj.browse(student_ids):
            result.append(student.pid)
        return result

    @api.model
    def render_html(self, docids, data=None):
        docs = self.env['student.student'].browse(docids)
        docargs = {
            'doc_ids': docids,
            'doc_model': self.env['time.table'],
            'data': data,
            'docs': docs,
            'get_student_info': self.get_student_info,
        }
        return self.env['report'].render('barcode_report.result_label',
                                         docargs)
