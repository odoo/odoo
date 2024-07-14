# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.tests.common import tagged, TransactionCase

@tagged('-at_install', 'post_install')
class TestHrAppraisalFeedback(TransactionCase):

    def setUp(self):
        super(TestHrAppraisalFeedback, self).setUp()

        group = self.env.ref('hr_appraisal.group_hr_appraisal_user').id
        self.user = self.env['res.users'].create({
            'name': 'Test',
            'login': 'test',
            'groups_id': [(6, 0, [group])],
            'notification_type': 'email',
        })

        self.user_employee = self.env['hr.employee'].create({
            'name': 'Me Myself and I',
            'user_id': self.user.id
        })
        self.test_employee = self.env['hr.employee'].create({
            'name': 'John Smith'
        })
        self.manager = self.env['hr.employee'].create({
            'name': 'Mr. Manager'
        })

        self.appraisal = self.env['hr.appraisal'].create({
            'employee_id': self.test_employee.id,
            'manager_ids': [self.manager.id],
            'state': 'pending',
        })

        self.appraisal_survey = self.env['survey.survey'].create({
            'title': 'appraisal feedback',
            'questions_layout': 'one_page',
            'questions_selection': 'all',
            'access_mode': 'public',
            'survey_type': 'appraisal',
        })

    def test_appraisal_feedback_deadline(self):
        feedback = self.env['appraisal.ask.feedback'].create({
            'appraisal_id': self.appraisal.id,
            'employee_ids': [self.user_employee.id],
            'deadline': date.today(),
            'survey_template_id': self.appraisal_survey.id,
        })
        feedback.action_send()
        feedback['deadline'] = date.today() + relativedelta(months=1)
        feedback.action_send()

        survey_input = self.env['survey.user_input'].search([('appraisal_id', '=', self.appraisal.id)])
        self.assertEqual(feedback['deadline'], survey_input['deadline'].date())
