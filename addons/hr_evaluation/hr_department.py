# -*- coding: utf-8 -*-
from openerp import api, fields, models


class hr_department(models.Model):
    _inherit = 'hr.department'

    @api.multi
    def _compute_interview_request(self):
        Interview = self.env['hr.evaluation.interview']
        for department in self:
            department.interview_request_count = Interview.search_count([
                ('user_to_review_id.department_id', '=', department.id),
                ('state', '=', 'waiting_answer')
            ])

    @api.multi
    def _compute_appraisal_to_start(self):
        Evaluation = self.env['hr_evaluation.evaluation']
        for department in self:
            department.appraisal_to_start_count = Evaluation.search_count([
                ('employee_id.department_id', '=', department.id),
                ('state', '=', 'draft')
            ])

    appraisal_to_start_count = fields.Integer(
        compute='_compute_appraisal_to_start', string='Appraisal to Start')
    interview_request_count = fields.Integer(
        compute='_compute_interview_request', string='Interview Request')
