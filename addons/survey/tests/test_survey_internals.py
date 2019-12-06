# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.addons.survey.tests import common
from odoo.tests.common import users


class TestValidation(common.TestSurveyWDemoSurvey):

    @users('survey_manager')
    def test_answer_validation_mandatory(self):
        """ For each type of question check that mandatory questions correctly check for complete answers """
        for (question_type, text) in self.env['survey.question']._fields['question_type'].selection:
            kwargs = {'page': self.page_0}
            if question_type == 'answer_selection':
                kwargs['suggested_answers'] = [{'value': 'MChoice0'}, {'value': 'MChoice1'}]
            elif question_type == 'answer_matrix':
                kwargs['suggested_answers'] = [{'value': 'Column0'}, {'value': 'Column1'}]
                kwargs['matrix_rows'] = [{'value': 'Row0'}, {'value': 'Row1'}]
            question = self._add_question('Q0', question_type, **kwargs)

            self.assertDictEqual(
                question.validate_question(''),
                {question.id: 'TestError'}
            )

    @users('survey_manager')
    def test_answer_validation_date(self):
        question = self._add_question(
            'Q0', 'date', validation_required=True, page=self.page_0,
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
            'Q0', 'numerical_box', validation_required=True, page=self.page_0,
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
        question = self._add_question('Q0', 'char_box', validation_email=True, page=self.page_0)

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
            'Q0', 'char_box', validation_required=True, page=self.page_0,
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


class TestQuestionsPages(common.TestSurveyCommonWUsers):

    @classmethod
    def setUpClass(cls):
        super(TestQuestionsPages, cls).setUpClass()
        cls.survey = cls.env['survey.survey'].create({
            'title': 'Test Survey',
            'questions_selection': 'random',
        })

    @users('survey_manager')
    def test_compute_pages_questions(self):
        page_0 = self.env['survey.question'].create({
            'is_page': True,
            'sequence': 1,
            'title': 'P1',
            'survey_id': self.survey.id
        })
        page0_q0 = self._add_question('Q1', 'text_box', page=page_0, survey_id=self.survey.id)
        page0_q1 = self._add_question('Q2', 'text_box', page=page_0, survey_id=self.survey.id)
        page0_q2 = self._add_question('Q3', 'text_box', page=page_0, survey_id=self.survey.id)
        page0_q3 = self._add_question('Q4', 'text_box', page=page_0, survey_id=self.survey.id)
        page0_q4 = self._add_question('Q5', 'text_box', page=page_0, survey_id=self.survey.id)
        page0_q_all = page0_q0 | page0_q1 | page0_q2 | page0_q3 | page0_q4

        page_1 = self.env['survey.question'].create({
            'is_page': True,
            'sequence': 7,
            'title': 'P2',
            'survey_id': self.survey.id,
        })
        page1_q0 = self._add_question('Q6', 'text_box', page=page_1, survey_id=self.survey.id)
        page1_q1 = self._add_question('Q7', 'text_box', page=page_1, survey_id=self.survey.id)
        page1_q2 = self._add_question('Q8', 'text_box', page=page_1, survey_id=self.survey.id)
        page1_q3 = self._add_question('Q9', 'text_box', page=page_1, survey_id=self.survey.id)
        page1_q_all = page1_q0 | page1_q1 | page1_q2 | page1_q3

        self.assertEqual(self.survey.page_ids, page_0 | page_1)
        self.assertEqual(self.survey.question_ids, page0_q_all | page1_q_all)
        self.assertEqual(self.survey.question_and_page_ids, page_0 | page_1 | page0_q_all | page1_q_all)

        self.assertEqual(page_0.question_ids, page0_q_all)
        self.assertEqual(page_1.question_ids, page1_q_all)

        self.assertTrue(all(question.page_id == page_0 for question in page0_q_all))
        self.assertTrue(all(question.page_id == page_1 for question in page1_q_all))

        # move 1 question from page 1 to page 2
        page0_q2.write({'sequence': 12})
        page0_q2.flush()
        self.assertEqual(page0_q2.page_id, page_1, "Question 3 should now belong to page 2")
        self.assertEqual(page_0.question_ids, page0_q_all - page0_q2)
        self.assertEqual(page_1.question_ids, page1_q_all | page0_q2)

    def test_generate_randomized_questions(self):
        """ Use random generate for a survey and verify that questions within the page are selected accordingly """
        Question = self.env['survey.question'].sudo()
        question_and_pages = self.env['survey.question']
        page_1 = Question.create({
            'title': 'Page 1',
            'is_page': True,
            'sequence': 1,
            'random_questions_count': 3
        })
        question_and_pages |= page_1
        for i in range(5):
            question_and_pages |= self._add_question('%s Q%s' % (page_1.title, i + 1), 'text_box', sequence=page_1.sequence + (i + 1))

        page_2 = Question.create({
            'title': 'Page 2',
            'is_page': True,
            'sequence': 100,
            'random_questions_count': 5
        })
        question_and_pages |= page_2
        for i in range(10):
            question_and_pages |= self._add_question('%s Q%s' % (page_2.title, i + 1), 'text_box', sequence=page_2.sequence + (i + 1))

        page_3 = Question.create({
            'title': 'Page 2',
            'is_page': True,
            'sequence': 1000,
            'random_questions_count': 4
        })
        question_and_pages |= page_3
        for i in range(2):
            question_and_pages |= self._add_question('%s Q%s' % (page_3.title, i + 1), 'text_box', sequence=page_3.sequence + (i + 1))

        self.survey.write({
            'question_and_page_ids': [(6, 0, question_and_pages.ids)],
        })

        generated_questions = self.survey._prepare_user_input_predefined_questions()

        self.assertEqual(len(generated_questions.ids), 10, msg="Expected 10 unique questions")
        self.assertEqual(len(generated_questions.filtered(lambda question: question.page_id == page_1)), 3, msg="Expected 3 questions in page 1")
        self.assertEqual(len(generated_questions.filtered(lambda question: question.page_id == page_2)), 5, msg="Expected 5 questions in page 2")
        self.assertEqual(len(generated_questions.filtered(lambda question: question.page_id == page_3)), 2, msg="Expected 2 questions in page 3")
