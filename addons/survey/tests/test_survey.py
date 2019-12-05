# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from collections import Counter
from itertools import product
from werkzeug import urls

from odoo import _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.survey.tests import common
from odoo.tests.common import users


class TestSurveyInternals(common.TestSurveyCommon):

    @users('survey_manager')
    def test_answer_validation_mandatory(self):
        """ For each type of question check that mandatory questions correctly check for complete answers """
        for (question_type, text) in self.env['survey.question']._fields['question_type'].selection:
            kwargs = {}
            if question_type == 'multiple_choice':
                kwargs['labels'] = [{'value': 'MChoice0'}, {'value': 'MChoice1'}]
            elif question_type == 'simple_choice':
                kwargs['labels'] = []
            elif question_type == 'matrix':
                kwargs['labels'] = [{'value': 'Column0'}, {'value': 'Column1'}]
                kwargs['labels_2'] = [{'value': 'Row0'}, {'value': 'Row1'}]
            question = self._add_question(self.page_0, 'Q0', question_type, **kwargs)

            self.assertDictEqual(
                question.validate_question(''),
                {question.id: 'TestError'}
            )

    @users('survey_manager')
    def test_answer_validation_date(self):
        question = self._add_question(
            self.page_0, 'Q0', 'date', validation_required=True,
            validation_min_date='2015-03-20', validation_max_date='2015-03-25', validation_error_msg='ValidationError')

        self.assertEqual(
            question.validate_question('Is Alfred an answer ?'),
            {question.id: _('This is not a date')}
        )

        self.assertEqual(
            question.validate_question('2015-03-19'),
            {question.id: 'ValidationError'}
        )

        self.assertEqual(
            question.validate_question('2015-03-26'),
            {question.id: 'ValidationError'}
        )

        self.assertEqual(
            question.validate_question('2015-03-25'),
            {}
        )

    @users('survey_manager')
    def test_answer_validation_numerical(self):
        question = self._add_question(
            self.page_0, 'Q0', 'numerical_box', validation_required=True,
            validation_min_float_value=2.2, validation_max_float_value=3.3, validation_error_msg='ValidationError')

        self.assertEqual(
            question.validate_question('Is Alfred an answer ?'),
            {question.id: _('This is not a number')}
        )

        self.assertEqual(
            question.validate_question('2.0'),
            {question.id: 'ValidationError'}
        )

        self.assertEqual(
            question.validate_question('4.0'),
            {question.id: 'ValidationError'}
        )

        self.assertEqual(
            question.validate_question('2.9'),
            {}
        )

    @users('survey_manager')
    def test_answer_validation_char_box_email(self):
        question = self._add_question(self.page_0, 'Q0', 'char_box', validation_email=True)

        self.assertEqual(
            question.validate_question('not an email'),
            {question.id: _('This answer must be an email address')}
        )

        self.assertEqual(
            question.validate_question('email@example.com'),
            {}
        )

    @users('survey_manager')
    def test_answer_validation_char_box_length(self):
        question = self._add_question(
            self.page_0, 'Q0', 'char_box', validation_required=True,
            validation_length_min=2, validation_length_max=8, validation_error_msg='ValidationError')

        self.assertEqual(
            question.validate_question('l'),
            {question.id: 'ValidationError'}
        )

        self.assertEqual(
            question.validate_question('waytoomuchlonganswer'),
            {question.id: 'ValidationError'}
        )

        self.assertEqual(
            question.validate_question('valid'),
            {}
        )

    @users('survey_manager')
    def test_result_data_simple_multiple_choice(self):
        question = self._add_question(
            self.page_0, 'Q0', 'simple_choice',
            labels=[{'value': 'Choice0'}, {'value': 'Choice1'}]
        )
        for i in range(3):
            answer = self._add_answer(self.survey, False, email='public@example.com')
            self._add_answer_line(
                question, answer, random.choice(question.suggested_answer_ids.ids),
                answer_type='suggestion', answer_fname='suggested_answer_id')
        lines = [line.suggested_answer_id.id for line in question.user_input_line_ids]
        answers = [{'text': label.value, 'count': lines.count(label.id), 'answer_id': label.id, 'answer_score': label.answer_score} for label in question.suggested_answer_ids]
        prp_result = self.env['survey.survey'].prepare_result(question)['answers']
        self.assertItemsEqual(prp_result, answers)

    @users('survey_manager')
    def test_result_data_matrix(self):
        question = self._add_question(
            self.page_0, 'Q0', 'matrix', matrix_subtype='simple',
            labels=[{'value': 'Column0'}, {'value': 'Column1'}],
            labels_2=[{'value': 'Row0'}, {'value': 'Row1'}]
        )
        for i in range(3):
            answer = self._add_answer(self.survey, False, email='public@example.com')
            self._add_answer_line(
                question, answer, random.choice(question.suggested_answer_ids.ids),
                answer_type='suggestion', answer_fname='suggested_answer_id', matrix_row_id=random.choice(question.matrix_row_ids.ids)
            )
        lines = [(line.matrix_row_id.id, line.suggested_answer_id.id) for line in question.user_input_line_ids]
        res = {}
        for i in product(question.matrix_row_ids.ids, question.suggested_answer_ids.ids):
            res[i] = lines.count((i))
        self.assertEqual(self.env['survey.survey'].prepare_result(question)['result'], res)

    @users('survey_manager')
    def test_result_data_numeric_box(self):
        question = self._add_question(self.page_0, 'Q0', 'numerical_box')
        num = [float(n) for n in random.sample(range(1, 100), 3)]
        nsum = sum(num)
        for i in range(3):
            answer = self._add_answer(self.survey, False, email='public@example.com')
            self._add_answer_line(question, answer, num[i])
        exresult = {
            'average': round((nsum / len(num)), 2), 'max': round(max(num), 2),
            'min': round(min(num), 2), 'sum': nsum, 'most_common': Counter(num).most_common(5)}
        result = self.env['survey.survey'].prepare_result(question)
        for key in exresult:
            self.assertEqual(result[key], exresult[key])
