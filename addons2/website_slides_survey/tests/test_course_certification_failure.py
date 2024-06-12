# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.survey.tests.common import TestSurveyCommon


class TestCourseCertificationFailureFlow(TestSurveyCommon):
    def test_course_certification_failure_flow(self):
        # Step 1: create a simple certification
        # --------------------------------------------------
        with self.with_user('survey_user'):
            certification = self.env['survey.survey'].create({
                'title': 'Small course certification',
                'access_mode': 'public',
                'users_login_required': True,
                'scoring_type': 'scoring_with_answers',
                'certification': True,
                'is_attempts_limited': True,
                'scoring_success_min': 100.0,
                'attempts_limit': 2,
            })

            self._add_question(
                None, 'Question 1', 'simple_choice',
                sequence=1,
                survey_id=certification.id,
                labels=[
                    {'value': 'Wrong answer'},
                    {'value': 'Correct answer', 'is_correct': True, 'answer_score': 1.0}
                ])

            self._add_question(
                None, 'Question 2', 'simple_choice',
                sequence=2,
                survey_id=certification.id,
                labels=[
                    {'value': 'Wrong answer'},
                    {'value': 'Correct answer', 'is_correct': True, 'answer_score': 1.0}
                ])

        # Step 1.1: create a simple channel
        self.channel = self.env['slide.channel'].sudo().create({
            'name': 'Test Channel',
            'channel_type': 'training',
            'enroll': 'public',
            'visibility': 'public',
            'is_published': True,
        })

        # Step 2: link the certification to a slide of category 'certification'
        self.slide_certification = self.env['slide.slide'].sudo().create({
            'name': 'Certification slide',
            'channel_id': self.channel.id,
            'slide_category': 'certification',
            'survey_id': certification.id,
            'is_published': True,
        })
        # Step 3: add portal user as member of the channel
        self.channel._action_add_members(self.user_portal.partner_id)
        # forces recompute of partner_ids as we create directly in relation
        self.channel.invalidate_model()
        slide_partner = self.slide_certification._action_set_viewed(self.user_portal.partner_id)
        self.slide_certification.with_user(self.user_portal)._generate_certification_url()

        self.assertEqual(1, len(slide_partner.user_input_ids), 'A user input should have been automatically created upon slide view')

        first_attempt_in_first_pool = slide_partner.user_input_ids[0]
        # Step 4: fill in the created user_input with wrong answers
        self.fill_in_answer(slide_partner.user_input_ids[0], certification.question_ids)

        self.assertFalse(slide_partner.survey_scoring_success, 'Quizz should not be marked as passed with wrong answers')
        # forces recompute of partner_ids as we delete directly in relation
        self.channel.invalidate_model()
        self.assertIn(self.user_portal.partner_id, self.channel.partner_ids, 'Portal user should still be a member of the course because they still have attempts left')
        certification_urls = self.slide_certification.with_user(self.user_portal)._generate_certification_url()
        self.assertEqual(certification_urls[self.slide_certification.id],
                         slide_partner.user_input_ids[0].get_start_url(),
                         "Make sure that the url generated is the same even if we enter again the certification without doing retry.")
        # Step 5: simulate a 'retry'
        retry_user_input = self.slide_certification.survey_id.sudo()._create_answer(
            partner=self.user_portal.partner_id,
            **{
                'slide_id': self.slide_certification.id,
                'slide_partner_id': slide_partner.id
            },
            invite_token=slide_partner.user_input_ids[0].invite_token
        )
        second_attempt_in_first_pool = retry_user_input
        # Step 6: fill in the new user_input with wrong answers again
        self.fill_in_answer(retry_user_input, certification.question_ids)
        # forces recompute of partner_ids as we delete directly in relation
        self.channel.invalidate_model()
        channel_partner = self.env['slide.channel.partner'].with_context(active_test=False).search([
            ('channel_id', 'in', self.channel.ids),
            ('partner_id', 'in', slide_partner.partner_id.ids),
        ])
        self.assertFalse(channel_partner.active, 'Portal user membership should have been archived from the course attendee because he failed his last attempt')

        # Step 7: add portal user as member of the channel once again
        self.channel._action_add_members(self.user_portal.partner_id)
        # forces recompute of partner_ids as we create directly in relation
        self.channel.invalidate_model()

        self.slide_certification.with_user(self.user_portal)._generate_certification_url()
        self.assertTrue(channel_partner.active, 'Portal user membership should be a unarchived upon joining the course once again')
        self.assertEqual(1, len(slide_partner.user_input_ids), 'A new user input should have been automatically created upon slide view')
        first_attempt_in_second_pool = slide_partner.user_input_ids[0]
        # Step 8: fill in the created user_input with correct answers this time
        self.fill_in_answer(slide_partner.user_input_ids, certification.question_ids, good_answers=True)
        self.assertTrue(slide_partner.survey_scoring_success, 'Quizz should be marked as passed with correct answers')
        # forces recompute of partner_ids as we delete directly in relation
        self.channel.invalidate_model()
        self.assertIn(self.user_portal.partner_id, self.channel.partner_ids, 'Portal user should still be a member of the course')
        # Checking the attempts numbers
        self.assertEqual(1, first_attempt_in_first_pool.attempts_number,
                         'The first attempt of the first pool should be number 1')
        self.assertEqual(2, second_attempt_in_first_pool.attempts_number,
                         'The second attempt of the first pool should be number 2')
        self.assertEqual(1, first_attempt_in_second_pool.attempts_number,
                         'The first attempt of the second pool should be number 1')

    def fill_in_answer(self, answer, questions, good_answers=False):
        """ Fills in the user_input with answers for all given questions.
        You can control whether the answer will be correct or not with the 'good_answers' param.
        (It's assumed that wrong answers are at index 0 of question.suggested_answer_ids and good answers at index 1) """
        answer.write({
            'state': 'done',
            'user_input_line_ids': [
                (0, 0, {
                    'question_id': question.id,
                    'answer_type': 'suggestion',
                    'answer_score': 1 if good_answers else 0,
                    'suggested_answer_id': question.suggested_answer_ids[1 if good_answers else 0].id
                }) for question in questions
            ]
        })
