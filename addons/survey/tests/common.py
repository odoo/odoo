# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter
from contextlib import contextmanager
from functools import partial

from odoo.tests import common, new_test_user

survey_new_test_user = partial(new_test_user, context={'mail_create_nolog': True, 'mail_create_nosubscribe': True, 'mail_notrack': True, 'no_reset_password': True})


class SurveyCase(common.SavepointCase):

    def setUp(self):
        super(SurveyCase, self).setUp()

        """ Some custom stuff to make the matching between questions and answers
          :param dict _type_match: dict
            key: question type
            value: (answer type, answer field_name)
        """
        self._type_match = {
            'free_text': ('free_text', 'value_free_text'),
            'textbox': ('text', 'value_text'),
            'numerical_box': ('number', 'value_number'),
            'date': ('date', 'value_date'),
            'simple_choice': ('suggestion', 'value_suggested'),  # TDE: still unclear
            'multiple_choice': ('suggestion', 'value_suggested'),  # TDE: still unclear
            'matrix': ('suggestion', ('value_suggested', 'value_suggested_row')),  # TDE: still unclear
        }

        """ Create test data: a survey with some pre-defined questions and various test users for ACL """
        self.survey_manager = survey_new_test_user(
            self.env, name='Gustave Doré', login='survey_manager', email='survey.manager@example.com',
            groups='survey.group_survey_manager,base.group_user'
        )

        self.survey_user = survey_new_test_user(
            self.env, name='Lukas Peeters', login='survey_user', email='survey.user@example.com',
            groups='survey.group_survey_user,base.group_user'
        )

        self.user_emp = survey_new_test_user(
            self.env, name='Eglantine Employee', login='user_emp', email='employee@example.com',
            groups='base.group_user'
        )

        self.user_portal = survey_new_test_user(
            self.env, name='Patrick Portal', login='user_portal', email='portal@example.com',
            groups='base.group_portal'
        )

        self.user_public = survey_new_test_user(
            self.env, name='Pauline Public', login='user_public', email='public@example.com',
            groups='base.group_public'
        )

        self.customer = self.env['res.partner'].create({
            'name': 'Caroline Customer',
            'email': 'customer@example.com',
            'customer': True,
        })

        self.survey = self.env['survey.survey'].sudo(self.survey_manager).create({
            'title': 'Test Survey',
            'auth_required': True,
            'users_can_go_back': False,
        })
        self.page_0 = self.env['survey.page'].sudo(self.survey_manager).create({
            'title': 'First page',
            'survey_id': self.survey.id,
        })
        self.question_ft = self.env['survey.question'].sudo(self.survey_manager).create({
            'question': 'Test Free Text',
            'page_id': self.page_0.id,
            'question_type': 'free_text',
        })
        self.question_num = self.env['survey.question'].sudo(self.survey_manager).create({
            'question': 'Test NUmerical Box',
            'page_id': self.page_0.id,
            'question_type': 'numerical_box',
        })

    @contextmanager
    def sudo(self, user):
        """ Quick sudo environment """
        old_uid = self.uid
        try:
            self.uid = user.id
            self.env = self.env(user=self.uid)
            yield
        finally:
            # back
            self.uid = old_uid
            self.env = self.env(user=self.uid)

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
                self.assertEqual(getattr(answer_lines, answer_fname), value)

    def assertResponse(self, response, status_code, text_bits=None):
        self.assertEqual(response.status_code, status_code)
        for text in text_bits or []:
            self.assertIn(text, response.text)

    def _add_question(self, page, name, qtype, **kwargs):
        constr_mandatory = kwargs.pop('constr_mandatory', True)
        constr_error_msg = kwargs.pop('constr_error_msg', 'TestError')
        base_qvalues = {
            'page_id': page.id,
            'question': name,
            'question_type': qtype,
            'constr_mandatory': constr_mandatory,
            'constr_error_msg': constr_error_msg,
        }
        if qtype in ('simple_choice', 'multiple_choice'):
            base_qvalues['labels_ids'] = [
                (0, 0, {'value': label['value'], 'quizz_mark': label.get('quizz_mark', 0)})
                for label in kwargs.pop('labels')
            ]
        elif qtype == 'matrix':
            base_qvalues['matrix_subtype'] = kwargs.pop('matrix_subtype', 'simple')
            base_qvalues['labels_ids'] = [
                (0, 0, {'value': label['value'], 'quizz_mark': label.get('quizz_mark', 0)})
                for label in kwargs.pop('labels')
            ]
            base_qvalues['labels_ids_2'] = [
                (0, 0, {'value': label['value'], 'quizz_mark': label.get('quizz_mark', 0)})
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
            'input_type': 'manually',
        }
        base_avals.update(kwargs)
        return self.env['survey.user_input'].create(base_avals)

    def _add_answer_line(self, question, answer, answer_value, **kwargs):
        qtype = self._type_match.get(question.question_type, (False, False))
        answer_type = kwargs.pop('answer_type', qtype[0])
        answer_fname = kwargs.pop('answer_fname', qtype[1])

        base_alvals = {
            'user_input_id': answer.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': answer_type,
        }
        base_alvals[answer_fname] = answer_value
        base_alvals.update(kwargs)
        return self.env['survey.user_input_line'].create(base_alvals)
