# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.survey.tests import common
from odoo.tests import tagged
from odoo.tests.common import HttpCase
from odoo.addons.mail.tests.common import MockEmail


@tagged('-at_install', 'post_install', 'functional')
class TestCrmSurvey(common.TestSurveyCommon, MockEmail, HttpCase):
    """
    These tests will check:
    - 1st case: if connected user's inputs contains "Create lead" answers, then a lead is created successfully
    - 2nd case: if connected user's inputs not contain "Create lead" answers, a lead isn't created anymore
    - 3rd case: if not connected user's inputs contains "Create lead" answers, then a lead is created with his email answer
    """
    def _create_lead_qualification_survey(self, is_in_sales_team=False, survey_name=None, survey_type="survey"):
        login = "survey_manager"
        # Adding in a sales team
        if is_in_sales_team:
            sales_team = self.env['crm.team'].create({
                'name': 'Odoo Survey Team',
                'use_leads': True
            })
            user = self.env['res.users'].search([('login', '=', login)])
            sales_team.member_ids = [(4, user.id)]

        with self.with_user(login):
            # Create lead qualification survey
            if survey_name is None:
                survey_name = 'Questionnaire for the position of software developer'
            survey = self.env['survey.survey'].create({
                'title': survey_name,
                'survey_type': survey_type,
                'questions_layout': 'page_per_question',
                'access_mode': 'public',
                'users_login_required': False,
            })

            # Create questions
            q01 = self._add_question(
                None, 'How old are you?', 'simple_choice',
                sequence=1,
                constr_mandatory=True, constr_error_msg='Please select an answer', survey_id=survey.id,
                labels=[
                    {'value': '18-30', 'create_lead': False},
                    {'value': '30-50', 'create_lead': False},
                    {'value': '50+', 'create_lead': False},
                ])

            q02 = self._add_question(
                None, 'What programming languages do you use on a daily basis?', 'multiple_choice',
                sequence=2,
                constr_mandatory=True, constr_error_msg='Please select an answer', survey_id=survey.id,
                labels=[
                    {'value': 'Assembly', 'create_lead': True},
                    {'value': 'Java', 'create_lead': False},
                    {'value': 'C', 'create_lead': False},
                    {'value': 'Python', 'create_lead': False},
                ])

            q03 = self._add_question(
                None, 'How many years of experience do you have in this position?', 'simple_choice',
                sequence=3,
                constr_mandatory=True, constr_error_msg='Please select an answer', survey_id=survey.id,
                labels=[
                    {'value': '0-1 year', 'create_lead': True},  # Newbie power
                    {'value': '2-5 years', 'create_lead': False},
                    {'value': '6+ years', 'create_lead': False},
                ])

            q04 = self._add_question(
                None, 'Please skip this one', 'simple_choice',
                sequence=4,
                constr_mandatory=False, survey_id=survey.id,
                labels=[
                    {'value': 'No.', 'create_lead': False},
                    {'value': 'NO', 'create_lead': False},
                    {'value': 'OK, btw', 'create_lead': False},
                ])

            q05 = self._add_question(
                None, 'Please add or verify your email address :', 'char_box',
                sequence=5,
                validation_email=True,
                constr_mandatory=True, constr_error_msg='Please select an answer', survey_id=survey.id,
                )

        self.assertFalse(q01.is_lead_generating)
        self.assertTrue(q02.is_lead_generating)
        self.assertTrue(q03.is_lead_generating)
        self.assertFalse(q04.is_lead_generating)
        self.assertFalse(q05.is_lead_generating)

        return survey

    def test_connected_account_access_with_lead_generation_answer(self):
        # Step 1 : Connected access + lead generation
        survey = self._create_lead_qualification_survey(survey_type="custom")

        # Account connection
        login_password = 'survey_user'
        user = self.env['res.users'].search([('login', '=', login_password)])

        with self.with_user(login_password):
            # Start page
            self._access_start(survey)
            user_inputs = self.env['survey.user_input'].search([('survey_id', '=', survey.id)])
            user_inputs.partner_id = user.partner_id
            answer_token = user_inputs.access_token

            # First page
            response = self._access_page(survey, answer_token)
            csrf_token = self._find_csrf_token(response.text)
            self._access_begin(survey, answer_token)

            # Answers
            question_ids = list(survey.question_ids)
            self._answer_question(question_ids[0], question_ids[0].suggested_answer_ids.ids[0], answer_token, csrf_token)
            self._answer_question(question_ids[1], question_ids[1].suggested_answer_ids.ids[0], answer_token, csrf_token)
            self._answer_question(question_ids[2], question_ids[2].suggested_answer_ids.ids[0], answer_token, csrf_token)
            self._answer_question(question_ids[3], question_ids[3].suggested_answer_ids.ids[0], answer_token, csrf_token)
            self._answer_question(question_ids[4], user.email, answer_token, csrf_token)

        ### Check if the last created lead was from the survey
        last_lead_created = self.env['crm.lead'].search([], order='create_date desc', limit=1)
        self.assertTrue(last_lead_created)
        self.assertEqual(last_lead_created.name, f"{user.display_name}'s survey results")

        # Ensure that the result values are present in lead description
        description = last_lead_created.description
        for answer in user_inputs.user_input_line_ids:
            self.assertIn(answer._get_answer_value(), description)

        # Ensure contact, salesperson, medium, source, email and the contact name are rights
        self.assertEqual(last_lead_created.partner_id, user.partner_id)
        self.assertFalse(last_lead_created.user_id.id)
        self.assertEqual(last_lead_created.medium_id.name, "Survey")
        self.assertEqual(last_lead_created.source_id.name, survey.title)
        self.assertEqual(last_lead_created.email_from, user.email)
        self.assertEqual(last_lead_created.contact_name, user.partner_id.name)

        # Ensure Odoobot created the lead
        for message in last_lead_created.message_ids:
            self.assertEqual(message.author_id.name, self.env.ref('base.user_root').name)

    def test_connected_account_access_without_lead_generation_answer(self):
        # Step 2 : Connected access + no lead generation
        survey = self._create_lead_qualification_survey(survey_name="Not important survey")

        # Account connection
        login_password = 'survey_user'
        user = self.env['res.users'].search([('login', '=', login_password)])

        # Start page
        self._access_start(survey)
        user_inputs = self.env['survey.user_input'].search([('survey_id', '=', survey.id)])
        answer_token = user_inputs.access_token

        # First page
        response = self._access_page(survey, answer_token)
        csrf_token = self._find_csrf_token(response.text)
        self._access_begin(survey, answer_token)

        # Answers
        with self.with_user(login_password):
            question_ids = list(survey.question_ids)
            self._answer_question(question_ids[0], question_ids[0].suggested_answer_ids.ids[2], answer_token, csrf_token)
            self._answer_question(question_ids[1], question_ids[1].suggested_answer_ids.ids[2], answer_token, csrf_token)
            self._answer_question(question_ids[2], question_ids[2].suggested_answer_ids.ids[2], answer_token, csrf_token)
            self._answer_question(question_ids[3], question_ids[3].suggested_answer_ids.ids[2], answer_token, csrf_token)
            self._answer_question(question_ids[4], user.email, answer_token, csrf_token)

        ### Check if the last created lead was from the survey
        last_lead_created = self.env['crm.lead'].search([], order='create_date desc', limit=1)
        self.assertNotEqual(last_lead_created.name, f"{user.display_name}'s survey results")

    def test_not_connected_account_access_with_lead_generation_answer(self):
        # Step 3 : Public access + lead generation
        survey = self._create_lead_qualification_survey(is_in_sales_team=True)

        # Start page
        self._access_start(survey)
        user_inputs = self.env['survey.user_input'].search([('survey_id', '=', survey.id)])
        answer_token = user_inputs.access_token

        # First page
        response = self._access_page(survey, answer_token)
        csrf_token = self._find_csrf_token(response.text)
        self._access_begin(survey, answer_token)

        # Answers
        with self.with_user('survey_user'):
            question_ids = list(survey.question_ids)
            self._answer_question(question_ids[0], question_ids[0].suggested_answer_ids.ids[0], answer_token, csrf_token)
            self._answer_question(question_ids[1], question_ids[1].suggested_answer_ids.ids[0], answer_token, csrf_token)
            self._answer_question(question_ids[2], question_ids[2].suggested_answer_ids.ids[0], answer_token, csrf_token)
            self._answer_question(question_ids[3], question_ids[3].suggested_answer_ids.ids[0], answer_token, csrf_token)
            self._answer_question(question_ids[4], "harry@potter.poudlard", answer_token, csrf_token)

        ### Check if the last created lead was from the survey
        last_lead_created = self.env['crm.lead'].search([], order='create_date desc', limit=1)
        self.assertEqual(last_lead_created.name, "harry@potter.poudlard's survey results")

        # Ensure that the result values are present in lead description
        description = last_lead_created.description
        for answer in user_inputs.user_input_line_ids:
            self.assertIn(answer._get_answer_value(), description)

        # Ensure contact, salesperson, medium, source, email and contact name are rights
        self.assertFalse(last_lead_created.partner_id.id)  # Public user
        self.assertEqual(last_lead_created.user_id.id, survey.user_id.id)  # Survey created by a sales team person
        self.assertEqual(last_lead_created.medium_id.name, "Survey")
        self.assertEqual(last_lead_created.source_id.name, survey.title)
        self.assertEqual(last_lead_created.email_from, "harry@potter.poudlard")
        self.assertIn("Participant#", last_lead_created.contact_name)

        # Ensure Odoobot created the lead
        for message in last_lead_created.message_ids:
            self.assertEqual(message.author_id.name, self.env.ref('base.user_root').name)

    # Override common test survey class for adding "create_lead" attribute
    def _add_question(self, page, name, qtype, **kwargs):
        constr_mandatory = kwargs.pop('constr_mandatory', True)
        constr_error_msg = kwargs.pop('constr_error_msg', 'TestError')

        sequence = kwargs.pop('sequence', False)
        if not sequence:
            sequence = page.question_ids[-1].sequence + 1 if page.question_ids else page.sequence + 1

        base_qvalues = {
            'sequence': sequence,
            'title': name,
            'question_type': qtype,
            'constr_mandatory': constr_mandatory,
            'constr_error_msg': constr_error_msg,
        }
        if qtype in ('simple_choice', 'multiple_choice'):
            base_qvalues['suggested_answer_ids'] = [
                (0, 0, {
                    'value': label['value'],
                    'answer_score': label.get('answer_score', 0),
                    'is_correct': label.get('is_correct', False),
                    'create_lead': label.get('create_lead', False)
                }) for label in kwargs.pop('labels')
            ]
        elif qtype == 'matrix':
            base_qvalues['matrix_subtype'] = kwargs.pop('matrix_subtype', 'simple')
            base_qvalues['suggested_answer_ids'] = [
                (0, 0, {'value': label['value'], 'answer_score': label.get('answer_score', 0), 'create_lead': label.get('create_lead', False)})
                for label in kwargs.pop('labels')
            ]
            base_qvalues['matrix_row_ids'] = [
                (0, 0, {'value': label['value'], 'answer_score': label.get('answer_score', 0), 'create_lead': label.get('create_lead', False)})
                for label in kwargs.pop('labels_2')
            ]
        base_qvalues.update(kwargs)
        question = self.env['survey.question'].create(base_qvalues)
        return question
