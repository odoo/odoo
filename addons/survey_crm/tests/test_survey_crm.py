from markupsafe import Markup

from odoo.addons.survey.tests import common
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('-at_install', 'post_install', 'functional')
class TestSurveyCrm(common.TestSurveyCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create lead qualification survey
        cls.survey_crm = cls.env['survey.survey'].with_user(cls.survey_manager).create({
            'access_mode': 'public',
            'questions_layout': 'page_per_question',
            'survey_type': 'survey',
            'title': 'Questionnaire for the position of software developer',
            'users_login_required': False,
        })

        # Create questions
        q01 = cls._add_question(
            cls, None, 'How old are you?', 'simple_choice',
            labels=[
                {'value': '18-30'},
                {'value': '30-50'},
                {'value': '50+'},
            ],
            sequence=1, survey_id=cls.survey_crm.id,
            constr_mandatory=False,
            )
        q01.suggested_answer_ids[2].generate_lead = True

        q02 = cls._add_question(
            cls, None, 'What programming languages do you use on a daily basis?', 'multiple_choice',
            labels=[
                {'value': 'Assembly'},
                {'value': 'Java'},
                {'value': 'C'},
                {'value': 'Python'},
            ],
            sequence=2, survey_id=cls.survey_crm.id,
            constr_mandatory=True, constr_error_msg='Please select an answer',
            )
        q02.suggested_answer_ids[0].generate_lead = True
        q02.suggested_answer_ids[2].generate_lead = True

        q03 = cls._add_question(
            cls, None, 'Please add or verify your email address:', 'char_box',
            sequence=3, survey_id=cls.survey_crm.id,
            validation_email=True, constr_mandatory=True, constr_error_msg='Please select an answer',
            )

        q04 = cls._add_question(
            cls, None, 'Please specify your name:', 'char_box',
            sequence=4, survey_id=cls.survey_crm.id,
            save_as_nickname=True, constr_mandatory=False,
            )

        cls.assertTrue(cls, q01.generate_lead)
        cls.assertTrue(cls, q02.generate_lead)
        cls.assertFalse(cls, q03.generate_lead)
        cls.assertFalse(cls, q04.generate_lead)

    def _test_survey_crm(self, answers=[], login=None, sales_team=False, survey_type='survey'):
        if (sales_team):
            # Add survey manager in a sales team and the survey lead assignment to a sales team
            sales_team = self.env['crm.team'].create({
                'name': 'Odoo Survey Team',
                'use_leads': True
            })
            sales_team.member_ids = [(4, self.survey_manager.id)]
            self.survey_crm.update({'team_id': sales_team.id})
        survey_sudo = self.survey_crm.sudo()  # sudo to avoid access issues on crm.lead when asserting
        self.authenticate(login, login)
        self.survey_crm.update({'survey_type': survey_type})

        # Start page
        self._access_start(self.survey_crm)
        user_input = self.env['survey.user_input'].search([('survey_id', '=', self.survey_crm.id)])
        self.assertEqual(survey_sudo.lead_count, 0)
        answer_token = user_input.access_token

        # First page
        response = self._access_page(self.survey_crm, answer_token)
        csrf_token = self._find_csrf_token(response.text)
        self._access_begin(self.survey_crm, answer_token)

        # Answers
        question_ids = self.survey_crm.question_ids
        self._answer_question(question_ids[0], answers[0].id, answer_token, csrf_token)
        self._answer_question(question_ids[1], answers[1].id, answer_token, csrf_token)
        self._answer_question(question_ids[2], answers[2], answer_token, csrf_token)
        self._answer_question(question_ids[3], answers[3], answer_token, csrf_token, 'submit')

        # Check that a lead was created from the survey
        self.assertEqual(survey_sudo.lead_count, 1)
        lead_created = survey_sudo.lead_ids
        self.assertEqual(lead_created.name, "%(name)s survey results" % {'name': self.survey_user.display_name if login else answers[2]})

        # Ensure that the result values are present in lead description
        description_expected = Markup('%s' % (
        '<div>Answers:</div>'
        '<ul>'
            f'<li>{question_ids[0].title} — {answers[0].value}</li>'
            f'<li>{question_ids[1].title} — {answers[1].value}</li>'
            f'<li>{question_ids[2].title} — {answers[2]}</li>'
            f'<li>{question_ids[3].title} — {answers[3] or "<i>Skipped</i>"}</li>'
        '</ul>'
        ))
        self.assertEqual(description_expected, lead_created.description)

        # Ensure contact, salesperson, medium, source, email and contact name are rights
        self.assertEqual(lead_created.partner_id, self.survey_user.partner_id) if login else self.assertFalse(lead_created.partner_id.id)
        self.assertEqual(lead_created.user_id.id, False if login else self.survey_crm.user_id.id)  # CRM salesperson if survey responsible is from the assigned survey sales team
        self.assertEqual(lead_created.medium_id, self.env['utm.medium']._fetch_or_create_utm_medium('survey'))
        self.assertEqual(lead_created.source_id.name, self.survey_crm.title)
        self.assertEqual(lead_created.email_from, answers[2])
        self.assertEqual(lead_created.contact_name, self.survey_user.partner_id.name if answers[3] else '')

        # Ensure public user created the lead
        self.assertTrue(lead_created.message_ids[0].author_id == self.survey_user.partner_id if login else self.env.ref('base.public_user').partner_id)

    def test_survey_with_lead_generation_logged_in(self):
        question_ids = self.survey_crm.question_ids
        args = {
            'answers': [question_ids[0].suggested_answer_ids[0], question_ids[1].suggested_answer_ids[2], 'beautiful_address@example.com', ''],
            'sales_team': True,
            'survey_type': 'custom',
        }
        self._test_survey_crm(**args)

    def test_survey_with_lead_generation_public(self):
        question_ids = self.survey_crm.question_ids
        args = {
            'answers': [question_ids[0].suggested_answer_ids[0], question_ids[1].suggested_answer_ids[0], self.survey_user.email, "Martin Test"],
            'login': self.survey_user.login,
        }
        self._test_survey_crm(**args)
