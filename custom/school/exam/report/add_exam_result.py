# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import time
from odoo import models, api


class ReportAddExamResult(models.AbstractModel):
    _name = 'report.exam.exam_result_report'

    @api.model
    def _get_result_detail(self, subject_ids, result):
        sub_list = []
        result_data = []
        for sub in subject_ids:
            sub_list.append(sub.id)
        sub_obj = self.env['exam.subject']
        subject_exam_ids = sub_obj.search([('id', 'in', sub_list),
                                           ('exam_id', '=', result.id)])
        for subject in subject_exam_ids:
            subj = subject.subject_id and subject.subject_id.name or ''
            result_data.append({'subject': subj,
                                'max_mark': subject.maximum_marks or '',
                                'mini_marks': subject.minimum_marks or '',
                                'obt_marks': subject.obtain_marks or ''})
        return result_data

    @api.model
    def render_html(self, docids, data=None):
        self.model = self.env.context.get('active_model')

        docs = self.env[self.model].browse(self.env.context.get('active_ids',
                                                                []))
        docargs = {
            'doc_ids': docids,
            'doc_model': self.model,
            'docs': docs,
            'time': time,
            'get_result_detail': self._get_result_detail,
        }
        render_model = 'exam.exam_result_report'
        return self.env['report'].render(render_model, docargs)
