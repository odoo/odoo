# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.survey.tests.common import SurveyCase


class TestCourseCertificationFailureFlow(SurveyCase):
    def test_course_certification_failure_flow(self):
        # Step 1: create a simple certification
        # --------------------------------------------------
        with self.with_user(self.survey_user):
            certification = self.env['survey.survey'].create({
                'title': 'Small course certification',
                'access_mode': 'public',
                'users_login_required': True,
                'scoring_type': 'scoring_with_answers',
                'certificate': True,
                'is_attempts_limited': True,
                'passing_score': 100.0,
                'attempts_limit': 2,
                'state': 'open',
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

        # Step 2: link the certification to a slide of type 'certification'
        self.slide_certification = self.env['slide.slide'].sudo().create({
            'name': 'Certification slide',
            'channel_id': self.channel.id,
            'slide_type': 'certification',
            'survey_id': certification.id,
            'is_published': True,
        })
        # Step 3: add public user as member of the channel
        self.channel._action_add_members(self.user_public.partner_id)
        # forces recompute of partner_ids as we create directly in relation
        self.channel.invalidate_cache()
        slide_partner = self.slide_certification._action_set_viewed(self.user_public.partner_id)
        self.slide_certification.with_user(self.user_public)._generate_certification_url()

        self.assertEqual(1, len(slide_partner.user_input_ids), 'A user input should have been automatically created upon slide view')

        # Step 4: fill in the created user_input with wrong answers
        self.fill_in_answer(slide_partner.user_input_ids[0], certification.question_ids)

        self.assertFalse(slide_partner.survey_quizz_passed, 'Quizz should not be marked as passed with wrong answers')
        # forces recompute of partner_ids as we delete directly in relation
        self.channel.invalidate_cache()
        self.assertIn(self.user_public.partner_id, self.channel.partner_ids, 'Public user should still be a member of the course because he still has attempts left')

        # Step 5: simulate a 'retry'
        retry_user_input = self.slide_certification.survey_id.sudo()._create_answer(
            partner=self.user_public.partner_id,
            **{
                'slide_id': self.slide_certification.id,
                'slide_partner_id': slide_partner.id
            },
            invite_token=slide_partner.user_input_ids[0].invite_token
        )
        # Step 6: fill in the new user_input with wrong answers again
        self.fill_in_answer(retry_user_input, certification.question_ids)
        # forces recompute of partner_ids as we delete directly in relation
        self.channel.invalidate_cache()
        self.assertNotIn(self.user_public.partner_id, self.channel.partner_ids, 'Public user should have been kicked out of the course because he failed his last attempt')

        # Step 7: add public user as member of the channel once again
        self.channel._action_add_members(self.user_public.partner_id)
        # forces recompute of partner_ids as we create directly in relation
        self.channel.invalidate_cache()

        self.assertIn(self.user_public.partner_id, self.channel.partner_ids, 'Public user should be a member of the course once again')
        new_slide_partner = self.slide_certification._action_set_viewed(self.user_public.partner_id)
        self.slide_certification.with_user(self.user_public)._generate_certification_url()
        self.assertEqual(1, len(new_slide_partner.user_input_ids.filtered(lambda user_input: user_input.state != 'done')), 'A new user input should have been automatically created upon slide view')

        # Step 8: fill in the created user_input with correct answers this time
        self.fill_in_answer(new_slide_partner.user_input_ids.filtered(lambda user_input: user_input.state != 'done')[0], certification.question_ids, good_answers=True)
        self.assertTrue(new_slide_partner.survey_quizz_passed, 'Quizz should be marked as passed with correct answers')
        # forces recompute of partner_ids as we delete directly in relation
        self.channel.invalidate_cache()
        self.assertIn(self.user_public.partner_id, self.channel.partner_ids, 'Public user should still be a member of the course')

    def fill_in_answer(self, answer, questions, good_answers=False):
        """ Fills in the user_input with answers for all given questions.
        You can control whether the answer will be correct or not with the 'good_answers' param.
        (It's assumed that wrong answers are at index 0 of question.labels_ids and good answers at index 1) """
        answer.write({
            'state': 'done',
            'user_input_line_ids': [
                (0, 0, {
                    'question_id': question.id,
                    'answer_type': 'suggestion',
                    'answer_score': 1 if good_answers else 0,
                    'value_suggested': question.labels_ids[1 if good_answers else 0].id
                }) for question in questions
            ]
        })
