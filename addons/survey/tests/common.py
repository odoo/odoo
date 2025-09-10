# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import re

from collections import Counter
from contextlib import contextmanager

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import common


class SurveyCase(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(SurveyCase, cls).setUpClass()

        """ Some custom stuff to make the matching between questions and answers
          :param dict _type_match: dict
            key: question type
            value: (answer type, answer field_name)
        """
        cls._type_match = {
            'text_box': ('text_box', 'value_text_box'),
            'char_box': ('char_box', 'value_char_box'),
            'numerical_box': ('numerical_box', 'value_numerical_box'),
            'date': ('date', 'value_date'),
            'datetime': ('datetime', 'value_datetime'),
            'simple_choice': ('suggestion', 'suggested_answer_id'),  # TDE: still unclear
            'multiple_choice': ('suggestion', 'suggested_answer_id'),  # TDE: still unclear
            'matrix': ('suggestion', ('suggested_answer_id', 'matrix_row_id')),  # TDE: still unclear
        }

    # ------------------------------------------------------------
    # ASSERTS
    # ------------------------------------------------------------

    def assertAnswer(self, answer, state, page):
        self.assertEqual(answer.state, state)
        self.assertEqual(answer.last_displayed_page_id, page)

    def assertAnswerLines(self, page, answer, answer_data):
        """ Check answer lines.

          :param dict answer_data:
            key = question ID
            value = {'value': [user input]}
        """
        lines = answer.user_input_line_ids.filtered(lambda l: l.page_id == page)
        answer_count = sum(len(user_input['value']) for user_input in answer_data.values())
        self.assertEqual(len(lines), answer_count)
        for qid, user_input in answer_data.items():
            answer_lines = lines.filtered(lambda l: l.question_id.id == qid)
            question = answer_lines[0].question_id  # TDE note: might have several answers for a given question
            if question.question_type == 'multiple_choice':
                values = user_input['value']
                answer_fname = self._type_match[question.question_type][1]
                self.assertEqual(
                    Counter(getattr(line, answer_fname).id for line in answer_lines),
                    Counter(values))
            elif question.question_type == 'simple_choice':
                [value] = user_input['value']
                answer_fname = self._type_match[question.question_type][1]
                self.assertEqual(getattr(answer_lines, answer_fname).id, value)
            elif question.question_type == 'matrix':
                [value_col, value_row] = user_input['value']
                answer_fname_col = self._type_match[question.question_type][1][0]
                answer_fname_row = self._type_match[question.question_type][1][1]
                self.assertEqual(getattr(answer_lines, answer_fname_col).id, value_col)
                self.assertEqual(getattr(answer_lines, answer_fname_row).id, value_row)
            else:
                [value] = user_input['value']
                answer_fname = self._type_match[question.question_type][1]
                if question.question_type == 'numerical_box':
                    self.assertEqual(getattr(answer_lines, answer_fname), float(value))
                else:
                    self.assertEqual(getattr(answer_lines, answer_fname), value)

    def assertResponse(self, response, status_code, text_bits=None):
        self.assertEqual(response.status_code, status_code)
        for text in text_bits or []:
            self.assertIn(text, response.text)

    # ------------------------------------------------------------
    # DATA CREATION
    # ------------------------------------------------------------

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
                    'is_correct': label.get('is_correct', False)
                }) for label in kwargs.pop('labels')
            ]
        elif qtype == 'matrix':
            base_qvalues['matrix_subtype'] = kwargs.pop('matrix_subtype', 'simple')
            base_qvalues['suggested_answer_ids'] = [
                (0, 0, {'value': label['value'], 'answer_score': label.get('answer_score', 0)})
                for label in kwargs.pop('labels')
            ]
            base_qvalues['matrix_row_ids'] = [
                (0, 0, {'value': label['value'], 'answer_score': label.get('answer_score', 0)})
                for label in kwargs.pop('labels_2')
            ]
        else:
            pass
        base_qvalues.update(kwargs)
        question = self.env['survey.question'].create(base_qvalues)
        return question

    def _add_answer(self, survey, partner, **kwargs):
        base_avals = {
            'survey_id': survey.id,
            'partner_id': partner.id if partner else False,
            'email': kwargs.pop('email', False),
        }
        base_avals.update(kwargs)
        return self.env['survey.user_input'].create(base_avals)

    def _add_answer_line(self, question, answer, answer_value, **kwargs):
        qtype = self._type_match.get(question.question_type, (False, False))
        answer_type = kwargs.pop('answer_type', qtype[0])
        answer_fname = kwargs.pop('answer_fname', qtype[1])
        if question.question_type == 'matrix':
            answer_fname = qtype[1][0]

        base_alvals = {
            'user_input_id': answer.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': answer_type,
        }
        base_alvals[answer_fname] = answer_value
        if 'answer_value_row' in kwargs:
            answer_value_row = kwargs.pop('answer_value_row')
            base_alvals[qtype[1][1]] = answer_value_row

        base_alvals.update(kwargs)
        return self.env['survey.user_input.line'].create(base_alvals)

    # ------------------------------------------------------------
    # UTILS / CONTROLLER ENDPOINTS FLOWS
    # ------------------------------------------------------------

    def _access_start(self, survey):
        return self.url_open('/survey/start/%s' % survey.access_token)

    def _access_page(self, survey, token):
        return self.url_open('/survey/%s/%s' % (survey.access_token, token))

    def _access_begin(self, survey, token):
        url = survey.get_base_url() + '/survey/begin/%s/%s' % (survey.access_token, token)
        return self.opener.post(url=url, json={})

    def _access_submit(self, survey, token, post_data):
        url = survey.get_base_url() + '/survey/submit/%s/%s' % (survey.access_token, token)
        return self.opener.post(url=url, json={'params': post_data})

    def _find_csrf_token(self, text):
        csrf_token_re = re.compile("(input.+csrf_token.+value=\")([a-f0-9]{40}o[0-9]*)", re.MULTILINE)
        return csrf_token_re.search(text).groups()[1]

    def _prepare_post_data(self, question, answers, post_data):
        values = answers if isinstance(answers, list) else [answers]
        if question.question_type == 'multiple_choice':
            for value in values:
                value = str(value)
                if question.id in post_data:
                    if isinstance(post_data[question.id], list):
                        post_data[question.id].append(value)
                    else:
                        post_data[question.id] = [post_data[question.id], value]
                else:
                    post_data[question.id] = value
        else:
            [values] = values
            post_data[question.id] = str(values)
        return post_data

    def _answer_question(self, question, answer, answer_token, csrf_token, button_submit='next'):
        # Employee submits the question answer
        post_data = self._format_submission_data(question, answer, {'csrf_token': csrf_token, 'token': answer_token, 'button_submit': button_submit})
        response = self._access_submit(question.survey_id, answer_token, post_data)
        self.assertResponse(response, 200)

        # Employee is redirected on next question
        response = self._access_page(question.survey_id, answer_token)
        self.assertResponse(response, 200)

    def _answer_page(self, page, answers, answer_token, csrf_token):
        post_data = {}
        for question, answer in answers.items():
            post_data[question.id] = answer.id
        post_data['page_id'] = page.id
        post_data['csrf_token'] = csrf_token
        post_data['token'] = answer_token
        response = self._access_submit(page.survey_id, answer_token, post_data)
        self.assertResponse(response, 200)
        response = self._access_page(page.survey_id, answer_token)
        self.assertResponse(response, 200)

    def _format_submission_data(self, question, answer, additional_post_data):
        post_data = {}
        post_data['question_id'] = question.id
        post_data.update(self._prepare_post_data(question, answer, post_data))
        if question.page_id:
            post_data['page_id'] = question.page_id.id
        post_data.update(**additional_post_data)
        return post_data

    # ------------------------------------------------------------
    # UTILS / TOOLS
    # ------------------------------------------------------------

    def _assert_skipped_question(self, question, survey_user):
        statistics = question._prepare_statistics(survey_user.user_input_line_ids)
        question_data = next(
            (question_data
            for question_data in statistics
            if question_data.get('question') == question),
            False
        )
        self.assertTrue(bool(question_data))
        self.assertEqual(len(question_data.get('answer_input_skipped_ids')), 1)

    def _create_one_question_per_type(self):
        all_questions = self.env['survey.question']
        for (question_type, dummy) in self.env['survey.question']._fields['question_type'].selection:
            kwargs = {}
            if question_type == 'multiple_choice':
                kwargs['labels'] = [{'value': 'MChoice0'}, {'value': 'MChoice1'}]
            elif question_type == 'simple_choice':
                kwargs['labels'] = [{'value': 'SChoice0'}, {'value': 'SChoice1'}]
            elif question_type == 'matrix':
                kwargs['labels'] = [{'value': 'Column0'}, {'value': 'Column1'}]
                kwargs['labels_2'] = [{'value': 'Row0'}, {'value': 'Row1'}]
            all_questions |= self._add_question(self.page_0, 'Q0', question_type, **kwargs)

        return all_questions

    def _create_one_question_per_type_with_scoring(self):
        all_questions = self.env['survey.question']
        for (question_type, dummy) in self.env['survey.question']._fields['question_type'].selection:
            kwargs = {}
            kwargs['question_type'] = question_type
            if question_type == 'numerical_box':
                kwargs['answer_score'] = 1
                kwargs['answer_numerical_box'] = 5
            elif question_type == 'date':
                kwargs['answer_score'] = 2
                kwargs['answer_date'] = datetime.date(2023, 10, 16)
            elif question_type == 'datetime':
                kwargs['answer_score'] = 3
                kwargs['answer_datetime'] = datetime.datetime(2023, 11, 17, 8, 0, 0)
            elif question_type == 'multiple_choice':
                kwargs['answer_score'] = 4
                kwargs['labels'] = [
                    {'value': 'MChoice0', 'is_correct': True},
                    {'value': 'MChoice1', 'is_correct': True},
                    {'value': 'MChoice2'}
                ]
            elif question_type == 'simple_choice':
                kwargs['answer_score'] = 5
                kwargs['labels'] = [
                    {'value': 'SChoice0', 'is_correct': True},
                    {'value': 'SChoice1'}
                ]
            elif question_type == 'matrix':
                kwargs['labels'] = [{'value': 'Column0'}, {'value': 'Column1'}]
                kwargs['labels_2'] = [{'value': 'Row0'}, {'value': 'Row1'}]
            all_questions |= self._add_question(self.page_0, 'Q0', question_type, **kwargs)

        return all_questions


class TestSurveyCommon(SurveyCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        """ Create test data: a survey with some pre-defined questions and various test users for ACL """
        cls.survey_manager = mail_new_test_user(
            cls.env, name='Gustave Doré', login='survey_manager', email='survey.manager@example.com',
            groups='survey.group_survey_manager,base.group_user', tz='Europe/Brussels',
        )

        cls.survey_user = mail_new_test_user(
            cls.env, name='Lukas Peeters', login='survey_user', email='survey.user@example.com',
            groups='survey.group_survey_user,base.group_user'
        )

        cls.user_emp = mail_new_test_user(
            cls.env, name='Eglantine Employee', login='user_emp', email='employee@example.com',
            groups='base.group_user', password='user_emp'
        )

        cls.user_portal = mail_new_test_user(
            cls.env, name='Patrick Portal', login='user_portal', email='portal@example.com',
            groups='base.group_portal'
        )

        cls.user_public = mail_new_test_user(
            cls.env, name='Pauline Public', login='user_public', email='public@example.com',
            groups='base.group_public'
        )

        cls.customer = cls.env['res.partner'].create({
            'name': 'Caroline Customer',
            'email': 'customer@example.com',
        })

        cls.survey = cls.env['survey.survey'].with_user(cls.survey_manager).create({
            'title': 'Test Survey',
            'access_mode': 'public',
            'users_login_required': True,
            'users_can_go_back': False,
        })
        cls.page_0 = cls.env['survey.question'].with_user(cls.survey_manager).create({
            'title': 'First page',
            'survey_id': cls.survey.id,
            'sequence': 1,
            'is_page': True,
            'question_type': False,
        })
        cls.question_ft = cls.env['survey.question'].with_user(cls.survey_manager).create({
            'title': 'Test Free Text',
            'survey_id': cls.survey.id,
            'sequence': 2,
            'question_type': 'text_box',
        })
        cls.question_num = cls.env['survey.question'].with_user(cls.survey_manager).create({
            'title': 'Test NUmerical Box',
            'survey_id': cls.survey.id,
            'sequence': 3,
            'question_type': 'numerical_box',
        })


class TestSurveyResultsCommon(SurveyCase):

    @classmethod
    def setUpClass(cls):
        super(TestSurveyResultsCommon, cls).setUpClass()
        cls.survey_manager = mail_new_test_user(
            cls.env, name='Gustave Doré', login='survey_manager', email='survey.manager@example.com',
            groups='survey.group_survey_manager,base.group_user'
        )

        # Create survey with questions
        cls.survey = cls.env['survey.survey'].create({
            'title': 'Test Survey Results',
            'questions_layout': 'one_page'
        })
        cls.question_char_box = cls._add_question(
            cls, None, 'What is your name', 'char_box', survey_id=cls.survey.id, sequence='1')
        cls.question_numerical_box = cls._add_question(
            cls, None, 'What is your age', 'numerical_box', survey_id=cls.survey.id, sequence='2')
        cls.question_sc = cls._add_question(
            cls, None, 'Are you a cat or a dog person', 'simple_choice', survey_id=cls.survey.id,
            sequence='3', labels=[{'value': 'Cat'},
                                    {'value': 'Dog'}])
        cls.question_mc = cls._add_question(
            cls, None, 'What do you like most in our tarte al djotte', 'multiple_choice', survey_id=cls.survey.id,
            sequence='4', labels=[{'value': 'The gras'},
                                    {'value': 'The bette'},
                                    {'value': 'The tout'},
                                    {'value': 'The regime is fucked up'}])
        cls.question_mx1 = cls._add_question(
            cls, None, 'When do you harvest those fruits', 'matrix', survey_id=cls.survey.id, sequence='5',
            labels=[{'value': 'Spring'}, {'value': 'Summer'}],
            labels_2=[{'value': 'Apples'},
                        {'value': 'Strawberries'}])
        cls.question_mx2 = cls._add_question(
            cls, None, 'How often should you water those plants', 'matrix', survey_id=cls.survey.id, sequence='6',
            labels=[{'value': 'Once a month'}, {'value': 'Once a week'}],
            labels_2=[{'value': 'Cactus'},
                        {'value': 'Ficus'}])

        # Question answers ids
        [cls.cat_id, cls.dog_id] = cls.question_sc.suggested_answer_ids.ids
        [cls.gras_id, cls.bette_id, _, _] = cls.question_mc.suggested_answer_ids.ids
        [cls.apples_row_id, cls.strawberries_row_id] = cls.question_mx1.matrix_row_ids.ids
        [cls.spring_id, cls.summer_id] = cls.question_mx1.suggested_answer_ids.ids
        [cls.cactus_row_id, cls.ficus_row_id] = cls.question_mx2.matrix_row_ids.ids
        [cls.once_a_month_id, cls.once_a_week_id] = cls.question_mx2.suggested_answer_ids.ids

        # Populate survey with answers
        cls.user_input_1 = cls._add_answer(cls, cls.survey, cls.survey_manager.partner_id)
        cls.answer_lukas = cls._add_answer_line(cls, cls.question_char_box, cls.user_input_1, 'Lukas')
        cls.answer_24 = cls._add_answer_line(cls, cls.question_numerical_box, cls.user_input_1, 24)
        cls.answer_cat = cls._add_answer_line(cls, cls.question_sc, cls.user_input_1, cls.cat_id)
        cls._add_answer_line(cls, cls.question_mc, cls.user_input_1, cls.gras_id)
        cls._add_answer_line(cls, cls.question_mx1, cls.user_input_1, cls.summer_id, **{'answer_value_row': cls.apples_row_id})
        cls._add_answer_line(cls, cls.question_mx1, cls.user_input_1, cls.spring_id, **{'answer_value_row': cls.strawberries_row_id})
        cls._add_answer_line(cls, cls.question_mx2, cls.user_input_1, cls.once_a_month_id, **{'answer_value_row': cls.cactus_row_id})
        cls._add_answer_line(cls, cls.question_mx2, cls.user_input_1, cls.once_a_week_id, **{'answer_value_row': cls.ficus_row_id})
        cls.user_input_1.state = 'done'

        cls.user_input_2 = cls._add_answer(cls, cls.survey, cls.survey_manager.partner_id)
        cls.answer_pauline = cls._add_answer_line(cls, cls.question_char_box, cls.user_input_2, 'Pauline')
        cls._add_answer_line(cls, cls.question_numerical_box, cls.user_input_2, 24)
        cls.answer_dog = cls._add_answer_line(cls, cls.question_sc, cls.user_input_2, cls.dog_id)
        cls._add_answer_line(cls, cls.question_mc, cls.user_input_2, cls.gras_id)
        cls._add_answer_line(cls, cls.question_mc, cls.user_input_2, cls.bette_id)
        cls._add_answer_line(cls, cls.question_mx1, cls.user_input_2, cls.spring_id, **{'answer_value_row': cls.apples_row_id})
        cls._add_answer_line(cls, cls.question_mx1, cls.user_input_2, cls.spring_id, **{'answer_value_row': cls.strawberries_row_id})
        cls._add_answer_line(cls, cls.question_mx2, cls.user_input_2, cls.once_a_month_id, **{'answer_value_row': cls.cactus_row_id})
        cls._add_answer_line(cls, cls.question_mx2, cls.user_input_2, cls.once_a_month_id, **{'answer_value_row': cls.ficus_row_id})
        cls.user_input_2.state = 'done'
