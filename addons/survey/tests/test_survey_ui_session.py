# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import tagged, HttpCase


@tagged('post_install', '-at_install')
class TestUiSession(HttpCase):

    def test_admin_survey_session(self):
        """ This method tests a full 'survey session' flow.
        Break down of different steps:
        - Create the test data
          - A scored survey
          - A nickname question
          - "Simple" type questions (text, date, datetime)
          - A regular simple choice
          - A scored simple choice
          - A scored AND timed multiple choice
        - Create a new survey session
        - Register 3 attendees to it
        - Open the session manager to check that our attendees are accounted for
        - Create some answers to our survey questions.
        - Then run the 'big' manage session tour (see JS doc for details)
        - And finally check that our session and attendees inputs are correctly closed. """

        # =======================
        # CREATE SURVEY TEST DATA
        # =======================

        test_start_time = fields.Datetime.now()

        survey_session = self.env['survey.survey'].create({
            'title': 'User Session Survey',
            'access_token': 'b137640d-14d4-4748-9ef6-344caaaaafe',
            'access_mode': 'public',
            'users_can_go_back': False,
            'questions_layout': 'page_per_question',
            'scoring_type': 'scoring_without_answers'
        })

        nickname_question = self.env['survey.question'].create({
            'survey_id': survey_session.id,
            'title': 'Nickname',
            'save_as_nickname': True,
            'sequence': 1,
            'question_type': 'char_box',
        })
        text_question = self.env['survey.question'].create({
            'survey_id': survey_session.id,
            'title': 'Text Question',
            'sequence': 2,
            'question_type': 'char_box',
        })
        date_question = self.env['survey.question'].create({
            'survey_id': survey_session.id,
            'title': 'Date Question',
            'sequence': 3,
            'question_type': 'date',
        })
        datetime_question = self.env['survey.question'].create({
            'survey_id': survey_session.id,
            'title': 'Datetime Question',
            'sequence': 4,
            'question_type': 'datetime',
        })
        scale_question = self.env['survey.question'].create({
            'survey_id': survey_session.id,
            'title': 'Scale Question',
            'sequence': 50,
            'question_type': 'scale',
        })
        simple_choice_answer_1 = self.env['survey.question.answer'].create({
            'value': 'First'
        })
        simple_choice_answer_2 = self.env['survey.question.answer'].create({
            'value': 'Second'
        })
        simple_choice_answer_3 = self.env['survey.question.answer'].create({
            'value': 'Third'
        })
        simple_choice_question = self.env['survey.question'].create({
            'survey_id': survey_session.id,
            'title': 'Regular Simple Choice',
            'sequence': 60,
            'question_type': 'simple_choice',
            'suggested_answer_ids': [
                (4, simple_choice_answer_1.id),
                (4, simple_choice_answer_2.id),
                (4, simple_choice_answer_3.id)],
        })
        scored_choice_answer_1 = self.env['survey.question.answer'].create({
            'value': 'Correct',
            'is_correct': True,
            'answer_score': 30
        })
        scored_choice_answer_2 = self.env['survey.question.answer'].create({
            'value': 'Incorrect 1'
        })
        scored_choice_answer_3 = self.env['survey.question.answer'].create({
            'value': 'Incorrect 2'
        })
        scored_choice_answer_4 = self.env['survey.question.answer'].create({
            'value': 'Incorrect 3'
        })
        scored_choice_question = self.env['survey.question'].create({
            'survey_id': survey_session.id,
            'title': 'Scored Simple Choice',
            'sequence': 70,
            'question_type': 'simple_choice',
            'suggested_answer_ids': [
                (4, scored_choice_answer_1.id),
                (4, scored_choice_answer_2.id),
                (4, scored_choice_answer_3.id),
                (4, scored_choice_answer_4.id)],
        })
        timed_scored_choice_answer_1 = self.env['survey.question.answer'].create({
            'value': 'Correct',
            'is_correct': True,
            'answer_score': 30
        })
        timed_scored_choice_answer_2 = self.env['survey.question.answer'].create({
            'value': 'Also correct but less points',
            'is_correct': True,
            'answer_score': 10
        })
        timed_scored_choice_answer_3 = self.env['survey.question.answer'].create({
            'value': 'Incorrect',
            'answer_score': -40
        })
        timed_scored_choice_question = self.env['survey.question'].create({
            'survey_id': survey_session.id,
            'title': 'Timed Scored Multiple Choice',
            'sequence': 80,
            'question_type': 'multiple_choice',
            'is_time_limited': True,
            'time_limit': 1,
            'suggested_answer_ids': [
                (4, timed_scored_choice_answer_1.id),
                (4, timed_scored_choice_answer_2.id),
                (4, timed_scored_choice_answer_3.id)],
        })

        def action_open_session_manager_mock(self):
            """ Mock original method to ensure we are not using another tab
            as it creates issues with automated tours. """
            return {
                'type': 'ir.actions.act_url',
                'name': "Open Session Manager",
                'target': 'self',
                'url': '/survey/session/manage/%s' % self.access_token
            }

        # =======================
        # PART 1 : CREATE SESSION
        # =======================

        survey_session.action_start_session()
        # tricky part: we only take into account answers created after the session_start_time
        # the create_date of the answers we just saved is set to the beginning of the test.
        # but the session_start_time is set after that.
        # So we cheat on the session start date to be able to count answers properly.
        survey_session.write({'session_start_time': test_start_time - relativedelta(minutes=10)})

        attendee_1 = survey_session._create_answer()
        attendee_2 = survey_session._create_answer()
        attendee_3 = survey_session._create_answer()
        all_attendees = [attendee_1, attendee_2, attendee_3]

        self.assertEqual('ready', survey_session.session_state)
        self.assertTrue(all(attendee.is_session_answer for attendee in all_attendees),
            "Created answers should be within the session.")
        self.assertTrue(all(attendee.state == 'new' for attendee in all_attendees),
            "Created answers should be in the 'new' state.")

        # =========================================
        # PART 2 : OPEN SESSION AND CHECK ATTENDEES
        # =========================================

        with patch('odoo.addons.survey.models.survey_survey.Survey.action_open_session_manager', action_open_session_manager_mock):
            self.start_tour('/odoo', 'test_survey_session_start_tour', login='admin')

        self.assertEqual('in_progress', survey_session.session_state)
        self.assertTrue(bool(survey_session.session_start_time))

        # ========================================
        # PART 3 : CREATE ANSWERS & MANAGE SESSION
        # ========================================

        # create a few answers beforehand to avoid having to back and forth too
        # many times between the tours and the python test

        attendee_1._save_lines(nickname_question, 'xxxTheBestxxx')
        attendee_2._save_lines(nickname_question, 'azerty')
        attendee_3._save_lines(nickname_question, 'nicktalope')
        self.assertEqual('xxxTheBestxxx', attendee_1.nickname)
        self.assertEqual('azerty', attendee_2.nickname)
        self.assertEqual('nicktalope', attendee_3.nickname)

        attendee_1._save_lines(text_question, 'Attendee 1 is the best')
        attendee_2._save_lines(text_question, 'Attendee 2 rulez')
        attendee_3._save_lines(text_question, 'Attendee 3 will crush you')
        attendee_1._save_lines(date_question, '2010-10-10')
        attendee_2._save_lines(date_question, '2011-11-11')
        attendee_2._save_lines(datetime_question, '2010-10-10 10:00:00')
        attendee_3._save_lines(datetime_question, '2011-11-11 15:55:55')
        attendee_1._save_lines(simple_choice_question, simple_choice_answer_1.id)
        attendee_2._save_lines(simple_choice_question, simple_choice_answer_1.id)
        attendee_3._save_lines(simple_choice_question, simple_choice_answer_2.id)
        attendee_1._save_lines(scored_choice_question, scored_choice_answer_1.id)
        attendee_2._save_lines(scored_choice_question, scored_choice_answer_2.id)
        attendee_3._save_lines(scored_choice_question, scored_choice_answer_3.id)
        attendee_1._save_lines(timed_scored_choice_question,
            [timed_scored_choice_answer_1.id, timed_scored_choice_answer_3.id])
        attendee_2._save_lines(timed_scored_choice_question,
            [timed_scored_choice_answer_1.id, timed_scored_choice_answer_2.id])
        attendee_3._save_lines(timed_scored_choice_question,
            [timed_scored_choice_answer_2.id])
        attendee_1._save_lines(scale_question, '5')
        attendee_2._save_lines(scale_question, '5')
        attendee_3._save_lines(scale_question, '6')

        with patch('odoo.addons.survey.models.survey_survey.Survey.action_open_session_manager', action_open_session_manager_mock):
            self.start_tour('/odoo', 'test_survey_session_manage_tour', login='admin')

        self.assertFalse(bool(survey_session.session_state))
        self.assertTrue(all(answer.state == 'done' for answer in all_attendees))
