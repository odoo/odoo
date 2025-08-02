from markupsafe import Markup

from odoo.addons.survey.tests import common
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('-at_install', 'post_install', 'functional')
class TestCrmSurvey(common.TestSurveyCommon, HttpCase):
    """
    These tests will check:
    - 1st case: if logged in user's inputs contains "Create lead" answers, then a lead is created successfully
    - 2nd case: if logged in user's inputs do not contain "Create lead" answers, then no lead is created
    - 3rd case: if public user's inputs contains "Create lead" answers, then a lead is created with his email answer
    """
    def _create_lead_qualification_survey(self, survey_type="survey"):
        # Create lead qualification survey
        survey = self.env['survey.survey'].with_user(self.survey_manager).create({
            'title': 'Questionnaire for the position of software developer',
            'survey_type': survey_type,
            'questions_layout': 'page_per_question',
            'access_mode': 'public',
            'users_login_required': False,
        })

        # Create questions
        q01 = self._add_question(
            None, 'How old are you?', 'simple_choice',
            sequence=1,
            constr_mandatory=False, survey_id=survey.id,
            labels=[
                {'value': '18-30'},
                {'value': '30-50'},
                {'value': '50+'},
            ])
        q01.suggested_answer_ids[2].is_create_lead = True

        q02 = self._add_question(
            None, 'What programming languages do you use on a daily basis?', 'multiple_choice',
            sequence=2,
            constr_mandatory=True, constr_error_msg='Please select an answer', survey_id=survey.id,
            labels=[
                {'value': 'Assembly'},
                {'value': 'Java'},
                {'value': 'C'},
                {'value': 'Python'},
            ])
        q02.suggested_answer_ids[0].is_create_lead = True
        q02.suggested_answer_ids[2].is_create_lead = True

        q03 = self._add_question(
            None, 'Please add or verify your email address:', 'char_box',
            sequence=3,
            validation_email=True,
            constr_mandatory=True, constr_error_msg='Please select an answer', survey_id=survey.id,
            )

        self.assertTrue(q01.is_lead_generating)
        self.assertTrue(q02.is_lead_generating)
        self.assertFalse(q03.is_lead_generating)

        return survey

    def test_survey_with_lead_generation_logged_in(self):
        survey = self._create_lead_qualification_survey(survey_type="custom")
        survey_sudo = survey.sudo()  # sudo to avoid access issues on crm.lead when asserting
        self.authenticate(self.survey_user.login, self.survey_user.login)

        # Start page
        self._access_start(survey)
        user_input = survey_sudo.user_input_ids
        self.assertEqual(survey_sudo.lead_count, 0)
        answer_token = user_input.access_token

        # First page
        response = self._access_page(survey, answer_token)
        csrf_token = self._find_csrf_token(response.text)
        self._access_begin(survey, answer_token)

        # Answers
        question_ids = survey.question_ids
        self._answer_question(question_ids[0], question_ids[0].suggested_answer_ids.ids[0], answer_token, csrf_token)
        self._answer_question(question_ids[1], question_ids[1].suggested_answer_ids.ids[0], answer_token, csrf_token)
        self._answer_question(question_ids[2], self.survey_user.email, answer_token, csrf_token, 'submit')

        # Check that a lead was created from the survey
        self.assertEqual(survey_sudo.lead_count, 1)
        lead_created = survey_sudo.lead_ids
        self.assertEqual(lead_created.name, f"{self.survey_user.display_name}'s survey results")

        # Ensure that the result values are present in lead description
        description_expected = Markup("%s" % (
        "<div>Answers:</div>"
        "<ul>"
            f"<li>{question_ids[0].title} — {question_ids[0].suggested_answer_ids[0].value}</li>"
            f"<li>{question_ids[1].title} — {question_ids[1].suggested_answer_ids[0].value}</li>"
            f"<li>{question_ids[2].title} — {self.survey_user.email}</li>"
        "</ul>"
        ))
        self.assertEqual(description_expected, lead_created.description)

        # Ensure contact, salesperson, medium, source, email and the contact name are rights
        self.assertEqual(lead_created.partner_id, self.survey_user.partner_id)
        self.assertFalse(lead_created.user_id.id)
        self.assertEqual(lead_created.medium_id.name, "Survey")
        self.assertEqual(lead_created.source_id.name, survey.title)
        self.assertEqual(lead_created.email_from, self.survey_user.email)
        self.assertEqual(lead_created.contact_name, self.survey_user.partner_id.name)

        # Ensure Odoobot created the lead
        self.assertTrue(all(m.author_id.id == self.env.ref('base.user_root').partner_id.id for m in lead_created.message_ids))

    def test_survey_with_lead_generation_public(self):
        # Before, add survey manager in a sales team
        sales_team = self.env['crm.team'].create({
            'name': 'Odoo Survey Team',
            'use_leads': True
        })
        sales_team.member_ids = [(4, self.survey_manager.id)]
        survey = self._create_lead_qualification_survey()
        survey_sudo = survey.sudo()  # sudo to avoid access issues on crm.lead when asserting
        self.authenticate(None, None)

        # Start page
        self._access_start(survey)
        user_input = self.env['survey.user_input'].search([('survey_id', '=', survey.id)])
        self.assertEqual(survey_sudo.lead_count, 0)
        answer_token = user_input.access_token

        # First page
        response = self._access_page(survey, answer_token)
        csrf_token = self._find_csrf_token(response.text)
        self._access_begin(survey, answer_token)

        # Answers
        question_ids = survey.question_ids
        self._answer_question(question_ids[0], question_ids[0].suggested_answer_ids.ids[0], answer_token, csrf_token)
        self._answer_question(question_ids[1], [question_ids[1].suggested_answer_ids.ids[0], question_ids[1].suggested_answer_ids.ids[1]],
                              answer_token, csrf_token)
        user_email_answer = "beautiful_address@example.com"
        self._answer_question(question_ids[2], user_email_answer, answer_token, csrf_token, 'submit')

        # Check that a lead was created from the survey
        self.assertEqual(survey_sudo.lead_count, 1)
        lead_created = survey_sudo.lead_ids
        self.assertEqual(lead_created.name, f"{user_email_answer}'s survey results")

        # Ensure that the result values are present in lead description
        description_expected = Markup("%s" % (
        "<div>Answers:</div>"
        "<ul>"
            f"<li>{question_ids[0].title} — {question_ids[0].suggested_answer_ids[0].value}</li>"
            f"<li>{question_ids[1].title} — {question_ids[1].suggested_answer_ids[0].value}, {question_ids[1].suggested_answer_ids[1].value}</li>"
            f"<li>{question_ids[2].title} — {user_email_answer}</li>"
        "</ul>"
        ))
        self.assertEqual(description_expected, lead_created.description)

        # Ensure contact, salesperson, medium, source, email and contact name are rights
        self.assertFalse(lead_created.partner_id.id)  # Public user
        self.assertEqual(lead_created.user_id.id, survey.user_id.id)  # Survey created by a sales team person
        self.assertEqual(lead_created.medium_id.name, "Survey")
        self.assertEqual(lead_created.source_id.name, survey.title)
        self.assertEqual(lead_created.email_from, user_email_answer)
        self.assertEqual('', lead_created.contact_name)

        # Ensure Odoobot created the lead
        self.assertTrue(all(m.author_id.id == self.env.ref('base.user_root').partner_id.id for m in lead_created.message_ids))

    def test_survey_without_lead_generation_logged_in(self):
        survey = self._create_lead_qualification_survey("live_session")
        survey_sudo = survey.sudo()  # sudo to avoid access issues on crm.lead when asserting
        self.authenticate(self.survey_user.login, self.survey_user.login)

        # Start page
        self._access_start(survey)
        user_input = self.env['survey.user_input'].search([('survey_id', '=', survey.id)])
        self.assertEqual(survey_sudo.lead_count, 0)
        answer_token = user_input.access_token

        # First page
        response = self._access_page(survey, answer_token)
        csrf_token = self._find_csrf_token(response.text)
        self._access_begin(survey, answer_token)

        # Answers
        question_ids = survey.question_ids
        self._answer_question(question_ids[0], question_ids[0].suggested_answer_ids.ids[0], answer_token, csrf_token)
        self._answer_question(question_ids[1], question_ids[1].suggested_answer_ids.ids[3], answer_token, csrf_token)
        self._answer_question(question_ids[2], self.survey_user.email, answer_token, csrf_token, 'submit')

        # Check that no lead was created
        self.assertEqual(survey_sudo.lead_count, 0)
