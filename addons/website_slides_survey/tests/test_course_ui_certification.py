# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@odoo.tests.common.tagged('post_install', '-at_install')
class TestCourseUiCertification(HttpCaseWithUserDemo):

    def setUp(self):
        super().setUp()

        self.survey_certification = self.env['survey.survey'].create({
            'access_mode': 'token',
            'access_token': 'y137640d-14d4-4748-9ef6-344caaaaaae',
            'certification': True,
            'questions_layout': 'one_page',
            'question_and_page_ids': [
                (0, 0, {
                    'title': 'Question',
                    'sequence': 1,
                    'question_type': 'simple_choice',
                    'constr_mandatory': True,
                    'suggested_answer_ids': [
                        (0, 0, {
                            'value': 'Correct Answer',
                            'sequence': 1,
                            'is_correct': True,
                            'answer_score': 1,
                        }),
                        (0, 0, {
                            'value': 'Incorrect Answer',
                            'sequence': 2,
                        })
                    ]
                })
            ],
            'scoring_type': 'scoring_with_answers',
            'title': 'Certification',
            'users_login_required': True,
        })

        self.course = self.env['slide.channel'].create({
            'channel_type': 'training',
            'enroll': 'public',
            'is_published': True,
            'name': 'Certifying Course',
            'slide_ids': [(0, 0, {
                'name': 'Certification Slide',
                'slide_type': 'certification',
                'survey_id': self.survey_certification.id,
            })],
        })
        self.course._action_add_members(self.env.ref('base.user_demo').partner_id)

    def test_course_certification_tour(self):
        """ To ease the tour we start directly from the survey. """
        survey_access_token = self.survey_certification.access_token
        answer = self.survey_certification.sudo()._create_answer(
            user=self.env.ref('base.user_demo'),
            access_token='z137640d-14d4-4748-9ef6-344caaaaaae',
            slide_id=self.survey_certification.slide_ids[0].id,
        )
        self.start_tour(
            "/survey/start/%s?answer_token=%s" % (survey_access_token, answer.access_token),
            'test_course_certification',
            login="demo"
        )
