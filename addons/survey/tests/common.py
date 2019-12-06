# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo.addons.mail.tests import common as mail_common
from odoo.tests import common


class TestSurveyCommon(common.BaseCase):
    """ Some custom stuff to make the matching between questions and answers
      :param dict _type_match: dict
        key: question type
        value: (answer type, answer field_name)
    """
    _type_match = {
        'text_box': ('text_box', 'value_text_box'),
        'char_box': ('char_box', 'value_char_box'),
        'numerical_box': ('numerical_box', 'value_numerical_box'),
        'date': ('date', 'value_date'),
        'answer_selection': ('suggestion', 'suggested_answer_id'),  # TDE: still unclear
        'answer_matrix': ('suggestion', ('suggested_answer_id', 'matrix_row_id')),  # TDE: still unclear
    }

    # ------------------------------------------------------------
    # ASSERTS
    # ------------------------------------------------------------

    def assertPageAnswered(self, page, user_input, expected_values):
        """ Check answer lines.

          :param dict expected:
            key = question ID
            value = {'value': [user input]}
        """
        lines = user_input.user_input_line_ids.filtered(lambda l: l.page_id == page)
        # self.assertEqual(len(lines), len(expected_values.keys()))
        for question, expected in expected_values.items():
            answer_lines = lines.filtered(lambda l: l.question_id == question)
            if question.question_type == 'answer_selection' and question.selection_mode == 'multiple':
                self.assertEqual(set(answer_lines.mapped('suggested_answer_id').ids), set(expected))
                self.assertTrue(all(line.answer_type == 'suggestion' for line in answer_lines))
            elif question.question_type == 'answer_selection' and question.selection_mode == 'single':
                self.assertEqual(set(answer_lines.mapped('suggested_answer_id').ids), set([expected]))
                self.assertTrue(all(line.answer_type == 'suggestion' for line in answer_lines))
            elif question.question_type == 'answer_matrix':
                [value_col, value_row] = user_input['value']
                answer_fname_col = self._type_match[question.question_type][1][0]
                answer_fname_row = self._type_match[question.question_type][1][1]
                self.assertEqual(getattr(answer_lines, answer_fname_col).id, value_col)
                self.assertEqual(getattr(answer_lines, answer_fname_row).id, value_row)
            else:
                answer_fname = self._type_match[question.question_type][1]
                if question.question_type == 'numerical_box':
                    self.assertEqual(answer_lines[answer_fname], float(expected))
                else:
                    self.assertEqual(answer_lines[answer_fname], expected)

    def assertResponse(self, response, status_code, text_bits=None):
        self.assertEqual(response.status_code, status_code)
        for text in text_bits or []:
            self.assertIn(text, response.text)

    # ------------------------------------------------------------
    # HELPERS FOR DATA CREATIONS
    # ------------------------------------------------------------

    def _add_question(self, title, qtype, **kwargs):
        constr_mandatory = kwargs.pop('constr_mandatory', True)
        constr_error_msg = kwargs.pop('constr_error_msg', 'TestError')

        sequence = kwargs.pop('sequence', False)
        page = kwargs.pop('page', False)
        if not sequence and page:
            sequence = page.question_ids[-1].sequence + 1 if page.question_ids else page.sequence + 1
        if 'survey_id' not in kwargs and page:
            kwargs['survey_id'] = page.survey_id.id

        base_qvalues = {
            'sequence': sequence,
            'title': title,
            'question_type': qtype,
            'constr_mandatory': constr_mandatory,
            'constr_error_msg': constr_error_msg,
        }
        if qtype in ('answer_selection', 'answer_matrix'):
            base_qvalues['selection_mode'] = kwargs.pop('selection_mode', 'single')
            base_qvalues['suggested_answer_ids'] = [
                (0, 0, {
                    'value': answer['value'],
                    'answer_score': answer.get('answer_score', 0),
                    'is_correct': answer.get('is_correct', False)
                }) for answer in kwargs.pop('suggested_answers')
            ]
            if qtype == 'answer_matrix':
                base_qvalues['matrix_row_ids'] = [
                    (0, 0, {'value': answer['value'], 'answer_score': answer.get('answer_score', 0)})
                    for answer in kwargs.pop('matrix_rows')
                ]
        else:
            pass
        base_qvalues.update(kwargs)
        return self.env['survey.question'].create(base_qvalues)

    def _add_answer(self, survey, partner, **kwargs):
        base_avals = {
            'survey_id': survey.id,
            'partner_id': partner.id if partner else False,
            'email': kwargs.pop('email', False),
        }
        base_avals.update(kwargs)
        return self.env['survey.user_input'].create(base_avals)

    def _add_answer_line(self, question, user_input, answer_value, **kwargs):
        qtype = self._type_match.get(question.question_type, (False, False))
        answer_type = kwargs.pop('answer_type', qtype[0])
        answer_fname = kwargs.pop('answer_fname', qtype[1])

        base_alvals = {
            'user_input_id': user_input.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': answer_type,
        }
        base_alvals[answer_fname] = answer_value
        base_alvals.update(kwargs)
        return self.env['survey.user_input.line'].create(base_alvals)

    # ------------------------------------------------------------
    # HELPERS FOR FRONTEND
    # ------------------------------------------------------------

    def _access_start(self, survey):
        return self.url_open('/survey/start/%s' % survey.access_token)

    def _access_page(self, survey, token):
        response = self.url_open('/survey/fill/%s/%s' % (survey.access_token, token))
        self.assertResponse(response, 200)
        csrf_token = self._find_csrf_token(response.text)
        return response, csrf_token

    def _access_submit(self, survey, token, post_data):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/survey/submit/%s/%s' % (survey.access_token, token)
        return self.opener.post(url=url, json={'params': post_data})

    def _find_csrf_token(self, text):
        csrf_token_re = re.compile("(input.+csrf_token.+value=\")([_a-zA-Z0-9]{51})", re.MULTILINE)
        check = csrf_token_re.search(text)
        if check:
            return check.groups()[1]
        return False

    def _prepare_question_post_data(self, question, user_answers):
        post_data = {}
        if question.question_type== 'answer_selection' and question.selection_mode == 'multiple':
            user_answers = user_answers if isinstance(user_answers, list) else [user_answers]
            for value in user_answers:
                values = post_data.get('%s' % question.id, [])
                values.append(str(value))
                post_data['%s' % question.id] = values
        else:
            post_data['%s' % question.id] = str(user_answers)
        return post_data

    def _format_submission_data(self, questions, user_answers, additional_post_data=None, page=None):
        post_data = {}
        if questions[0].survey_id.questions_layout == 'page_per_section':
            page = page or questions[0].page_id
            post_data['page_id'] = page.id
        if questions[0].survey_id.questions_layout == 'page_per_question':
            post_data['question_id'] = questions[0].id

        for question in questions:
            question_user_answer = user_answers[question]
            post_data.update(self._prepare_question_post_data(question, question_user_answer))
        if additional_post_data:
            post_data.update(**additional_post_data)
        return post_data

    def _answer_questions(self, questions, user_answers, answer_token, csrf_token):
        """ Answers several questions on a given page """
        if not isinstance(user_answers, dict) and len(questions) == 1:
            user_answers = {questions[0]: user_answers}
        post_data = self._format_submission_data(
            questions, user_answers,
            additional_post_data={'csrf_token': csrf_token, 'token': answer_token}
        )
        response = self._access_submit(questions[0].survey_id, answer_token, post_data)
        self.assertResponse(response, 200, ['/survey/fill/%s/%s' % (questions[0].survey_id.access_token, answer_token)])
        return response


class TestSurveyCommonWUsers(TestSurveyCommon, common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestSurveyCommonWUsers, cls).setUpClass()

        """ Create test data: a survey with some pre-defined questions and various test users for ACL """
        cls.survey_manager = mail_common.mail_new_test_user(
            cls.env, name='Gustave Doré', login='survey_manager', email='survey.manager@example.com',
            groups='survey.group_survey_manager,base.group_user'
        )

        cls.survey_user = mail_common.mail_new_test_user(
            cls.env, name='Lukas Peeters', login='survey_user', email='survey.user@example.com',
            groups='survey.group_survey_user,base.group_user'
        )

        cls.user_emp = mail_common.mail_new_test_user(
            cls.env, name='Eglantine Employee', login='user_emp', email='employee@example.com',
            groups='base.group_user', password='user_emp'
        )

        cls.user_portal = mail_common.mail_new_test_user(
            cls.env, name='Patrick Portal', login='user_portal', email='portal@example.com',
            groups='base.group_portal'
        )

        cls.user_public = mail_common.mail_new_test_user(
            cls.env, name='Pauline Public', login='user_public', email='public@example.com',
            groups='base.group_public'
        )

        cls.customer = cls.env['res.partner'].create({
            'name': 'Caroline Customer',
            'email': 'customer@example.com',
        })


class TestSurveyCommonHttp(TestSurveyCommon, common.HttpCase):

    def setUp(self):
        super(TestSurveyCommonHttp, self).setUp()

        self.survey_manager = mail_common.mail_new_test_user(
            self.env, name='Gustave Doré', login='survey_manager', email='survey.manager@example.com',
            groups='survey.group_survey_manager,base.group_user'
        )

        self.user_emp = mail_common.mail_new_test_user(
            self.env, name='Eglantine Employee', login='user_emp', email='employee@example.com',
            groups='base.group_user', password='user_emp'
        )


class TestSurveyWDemoSurvey(TestSurveyCommonWUsers):

    @classmethod
    def setUpClass(cls):
        super(TestSurveyWDemoSurvey, cls).setUpClass()
        cls.survey = cls.env['survey.survey'].with_user(cls.survey_manager).create({
            'title': 'Test Survey',
            'access_mode': 'public',
            'users_login_required': True,
            'users_can_go_back': False,
            'state': 'open',
        })
        cls.page_0 = cls.env['survey.question'].with_user(cls.survey_manager).create({
            'title': 'First page',
            'survey_id': cls.survey.id,
            'sequence': 1,
            'is_page': True,
        })
        cls.question_nb_0 = cls._add_question(cls, 'Numerical Box', 'numerical_box', survey_id=cls.survey.id)
        cls.question_tb_0 = cls._add_question(cls, 'Text Box', 'text_box', survey_id=cls.survey.id)
