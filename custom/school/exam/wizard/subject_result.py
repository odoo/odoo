# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class SubjectResultWiz(models.TransientModel):
    _name = 'subject.result.wiz'
    _description = 'Subject Wise Result'

    result_ids = fields.Many2many("exam.subject", 'subject_result_wiz_rel',
                                  'result_id', "exam_id", "Exam Subjects")

    @api.model
    def default_get(self, fields):
        '''Override default method to get default subjects'''
        res = super(SubjectResultWiz, self).default_get(fields)
        exams = self.env['exam.result'].browse(self._context.get('active_id'))
        subjectlist = [rec.subject_id.id for rec in exams.result_ids]
        res.update({'result_ids': subjectlist})
        return res

    @api.multi
    def result_report(self):
        data = self.read()[0]
        return self.env['report'].get_action(self, 'exam.exam_result_report',
                                             data=data)
