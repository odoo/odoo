# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.survey.tests import common
from odoo.exceptions import UserError
from odoo.tests.common import users


class TestSurveyInvite(common.SurveyCase):

    @users('survey_manager')
    def test_survey_invite_action(self):
        # Check correctly configured survey returns an invite wizard action
        action = self.survey.action_send_survey()
        self.assertEqual(action['res_model'], 'survey.invite')

        # Bad cases
        surveys = [
            # no page
            self.env['survey.survey'].create({'title': 'Test survey'}),
            # no questions
            self.env['survey.survey'].create({'title': 'Test survey', 'page_ids': [(0, 0, {'title': 'P0'})]}),
            # closed
            self.env['survey.survey'].sudo(self.survey_manager).create({
                'title': 'S0',
                'stage_id': self.env['survey.stage'].search([('closed', '=', True)]).id,
                'page_ids': [(0, 0, {'title': 'P0', 'question_ids': [(0, 0, {'question': 'Q0', 'question_type': 'free_text'})]})]
            })
        ]
        for survey in surveys:
            with self.assertRaises(UserError):
                survey.action_send_survey()
