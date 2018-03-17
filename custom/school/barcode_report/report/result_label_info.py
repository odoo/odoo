# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.


from odoo import api, models


class ReportLabelInfo(models.AbstractModel):
    _name = 'report.barcode_report.result_label_info'

    def get_student_all_info(self, standard_id, division_id, medium_id,
                             year_id):
        student_obj = self.env['student.student']
        student_ids = student_obj.search([('standard_id', '=', standard_id),
                                          ('division_id', '=', division_id),
                                          ('medium_id', '=', medium_id),
                                          ('year', '=', year_id)])
        result = []
        for student in student_obj.browse(student_ids):
            name = (student.name + " " + student.middle or '' + " " +
                    student.last or '')
            result.append({'name': name,
                           'roll_no': student.roll_no, 'pid': student.pid})
        return result

    @api.model
    def render_html(self, docids, data=None):
        docs = self.env['student.student'].browse(docids)
        docargs = {
            'doc_ids': docids,
            'doc_model': self.env['time.table'],
            'data': data,
            'docs': docs,
            'get_student_all_info': self.get_student_all_info,
        }
        return self.env['report'].render('barcode_report.result_label_info',
                                         docargs)
