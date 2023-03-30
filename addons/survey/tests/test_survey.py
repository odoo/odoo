# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import _, fields
from odoo.addons.survey.tests import common
from odoo.tests.common import users


class TestSurveyInternals(common.TestSurveyCommon):

    def test_answer_attempts_count(self):
        """ As 'attempts_number' and 'attempts_count' are computed using raw SQL queries, let us
        test the results. """

        test_survey = self.env['survey.survey'].create({
            'title': 'Test Survey',
            'is_attempts_limited': True,
            'attempts_limit': 4,
        })

        all_attempts = self.env['survey.user_input']
        for _i in range(4):
            all_attempts |= self._add_answer(test_survey, self.survey_user.partner_id, state='done')

        # read both fields at once to allow computing their values in batch
        attempts_results = all_attempts.read(['attempts_number', 'attempts_count'])
        first_attempt = attempts_results[0]
        second_attempt = attempts_results[1]
        third_attempt = attempts_results[2]
        fourth_attempt = attempts_results[3]

        self.assertEqual(first_attempt['attempts_number'], 1)
        self.assertEqual(first_attempt['attempts_count'], 4)

        self.assertEqual(second_attempt['attempts_number'], 2)
        self.assertEqual(second_attempt['attempts_count'], 4)

        self.assertEqual(third_attempt['attempts_number'], 3)
        self.assertEqual(third_attempt['attempts_count'], 4)

        self.assertEqual(fourth_attempt['attempts_number'], 4)
        self.assertEqual(fourth_attempt['attempts_count'], 4)

    @freeze_time("2020-02-15 18:00")
    def test_answer_display_name(self):
        """ The "display_name" field in a survey.user_input.line is a computed field that will
        display the answer label for any type of question.
        Let us test the various question types. """

        questions = self._create_one_question_per_type()
        user_input = self._add_answer(self.survey, self.survey_user.partner_id)

        for question in questions:
            if question.question_type == 'char_box':
                question_answer = self._add_answer_line(question, user_input, 'Char box answer')
                self.assertEqual(question_answer.display_name, 'Char box answer')
            elif question.question_type == 'text_box':
                question_answer = self._add_answer_line(question, user_input, 'Text box answer')
                self.assertEqual(question_answer.display_name, 'Text box answer')
            elif question.question_type == 'numerical_box':
                question_answer = self._add_answer_line(question, user_input, 7)
                self.assertEqual(question_answer.display_name, '7.0')
            elif question.question_type == 'date':
                question_answer = self._add_answer_line(question, user_input, fields.Datetime.now())
                self.assertEqual(question_answer.display_name, '2020-02-15')
            elif question.question_type == 'datetime':
                question_answer = self._add_answer_line(question, user_input, fields.Datetime.now())
                self.assertEqual(question_answer.display_name, '2020-02-15 18:00:00')
            elif question.question_type == 'simple_choice':
                question_answer = self._add_answer_line(question, user_input, question.suggested_answer_ids[0].id)
                self.assertEqual(question_answer.display_name, 'SChoice0')
            elif question.question_type == 'multiple_choice':
                question_answer_1 = self._add_answer_line(question, user_input, question.suggested_answer_ids[0].id)
                self.assertEqual(question_answer_1.display_name, 'MChoice0')
                question_answer_2 = self._add_answer_line(question, user_input, question.suggested_answer_ids[1].id)
                self.assertEqual(question_answer_2.display_name, 'MChoice1')
            elif question.question_type == 'matrix':
                question_answer_1 = self._add_answer_line(question, user_input,
                    question.suggested_answer_ids[0].id, **{'answer_value_row': question.matrix_row_ids[0].id})
                self.assertEqual(question_answer_1.display_name, 'Column0: Row0')
                question_answer_2 = self._add_answer_line(question, user_input,
                    question.suggested_answer_ids[0].id, **{'answer_value_row': question.matrix_row_ids[1].id})
                self.assertEqual(question_answer_2.display_name, 'Column0: Row1')

    @users('survey_manager')
    def test_answer_validation_mandatory(self):
        """ For each type of question check that mandatory questions correctly check for complete answers """
        for question in self._create_one_question_per_type():
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

    def test_partial_scores_simple_choice(self):
        """" Check that if partial scores are given for partially correct answers, in the case of a multiple
        choice question with single choice, choosing the answer with max score gives 100% of points. """

        partial_scores_survey = self.env['survey.survey'].create({
            'title': 'How much do you know about words?',
            'scoring_type': 'scoring_with_answers',
            'scoring_success_min': 90.0,
        })
        [a_01, a_02, a_03] = self.env['survey.question.answer'].create([{
            'value': 'A thing full of letters.',
            'answer_score': 1.0
        }, {
            'value': 'A unit of language, [...], carrying a meaning.',
            'answer_score': 4.0,
            'is_correct': True
        }, {
            'value': '42',
            'answer_score': -4.0
        }])
        q_01 = self.env['survey.question'].create({
            'survey_id': partial_scores_survey.id,
            'title': 'What is a word?',
            'sequence': 1,
            'question_type': 'simple_choice',
            'suggested_answer_ids': [(6, 0, (a_01 | a_02 | a_03).ids)]
        })

        user_input = self.env['survey.user_input'].create({'survey_id': partial_scores_survey.id})
        self.env['survey.user_input.line'].create({
            'user_input_id': user_input.id,
            'question_id': q_01.id,
            'answer_type': 'suggestion',
            'suggested_answer_id': a_02.id
        })

        # Check that scoring is correct and survey is passed
        self.assertEqual(user_input.scoring_percentage, 100)
        self.assertTrue(user_input.scoring_success)

    @users('survey_manager')
    def test_skipped_values(self):
        """ Create one question per type of questions.
        Make sure they are correctly registered as 'skipped' after saving an empty answer for each
        of them. """

        questions = self._create_one_question_per_type()
        survey_user = self.survey._create_answer(user=self.survey_user)

        for question in questions:
            answer = '' if question.question_type in ['char_box', 'text_box'] else None
            survey_user.save_lines(question, answer)

        for question in questions:
            self._assert_skipped_question(question, survey_user)

    @users('survey_manager')
    def test_copy_conditional_question_settings(self):
        """ Create a survey with conditional layout, clone it and verify that the cloned survey has the same conditional
        layout as the original survey.
        The test also check that the cloned survey doesn't reference the original survey.
        """
        def get_question_by_title(survey, title):
            return survey.question_ids.filtered(lambda q: q.title == title)[0]

        # Create the survey questions (! texts of the questions must be unique as they are used to query them)
        q_is_vegetarian_text = 'Are you vegetarian ?'
        q_is_vegetarian = self._add_question(
            self.page_0, q_is_vegetarian_text, 'multiple_choice', survey_id=self.survey.id,
            sequence=100, labels=[{'value': 'Yes'}, {'value': 'No'}])
        q_food_vegetarian_text = 'Choose your green meal'
        self._add_question(self.page_0, q_food_vegetarian_text, 'multiple_choice',
                           is_conditional=True, sequence=101,
                           triggering_question_id=q_is_vegetarian.id,
                           triggering_answer_id=q_is_vegetarian.suggested_answer_ids[0].id,
                           survey_id=self.survey.id,
                           labels=[{'value': 'Vegetarian pizza'}, {'value': 'Vegetarian burger'}])
        q_food_not_vegetarian_text = 'Choose your meal'
        self._add_question(self.page_0, q_food_not_vegetarian_text, 'multiple_choice',
                           is_conditional=True, sequence=102,
                           triggering_question_id=q_is_vegetarian.id,
                           triggering_answer_id=q_is_vegetarian.suggested_answer_ids[1].id,
                           survey_id=self.survey.id,
                           labels=[{'value': 'Steak with french fries'}, {'value': 'Fish'}])

        # Clone the survey
        survey_clone = self.survey.copy()

        # Verify the conditional layout and that the cloned survey doesn't reference the original survey
        q_is_vegetarian_cloned = get_question_by_title(survey_clone, q_is_vegetarian_text)
        q_food_vegetarian_cloned = get_question_by_title(survey_clone, q_food_vegetarian_text)
        q_food_not_vegetarian_cloned = get_question_by_title(survey_clone, q_food_not_vegetarian_text)

        self.assertFalse(q_is_vegetarian_cloned.is_conditional)

        # Vegetarian choice
        self.assertTrue(q_food_vegetarian_cloned)
        # Correct conditional layout
        self.assertEqual(q_food_vegetarian_cloned.triggering_question_id.id, q_is_vegetarian_cloned.id)
        self.assertEqual(q_food_vegetarian_cloned.triggering_answer_id.id,
                         q_is_vegetarian_cloned.suggested_answer_ids[0].id)
        # Doesn't reference the original survey
        self.assertNotEqual(q_food_vegetarian_cloned.triggering_question_id.id, q_is_vegetarian.id)
        self.assertNotEqual(q_food_vegetarian_cloned.triggering_answer_id.id,
                            q_is_vegetarian.suggested_answer_ids[0].id)

        # Not vegetarian choice
        self.assertTrue(q_food_not_vegetarian_cloned.is_conditional)
        # Correct conditional layout
        self.assertEqual(q_food_not_vegetarian_cloned.triggering_question_id.id, q_is_vegetarian_cloned.id)
        self.assertEqual(q_food_not_vegetarian_cloned.triggering_answer_id.id,
                         q_is_vegetarian_cloned.suggested_answer_ids[1].id)
        # Doesn't reference the original survey
        self.assertNotEqual(q_food_not_vegetarian_cloned.triggering_question_id.id, q_is_vegetarian.id)
        self.assertNotEqual(q_food_not_vegetarian_cloned.triggering_answer_id.id,
                            q_is_vegetarian.suggested_answer_ids[1].id)

    def test_get_pages_and_questions_to_show(self):
        """
        Tests the method `_get_pages_and_questions_to_show` - it takes a recordset of
        question.question from a survey.survey and returns a recordset without
        invalid conditional questions and pages without description

        Structure of the test survey:

        sequence    | type                          | trigger       | validity
        ----------------------------------------------------------------------
        1           | page, no description          | /             | X
        2           | text_box                      | trigger is 6  | X
        3           | numerical_box                 | trigger is 2  | X
        4           | simple_choice                 | /             | V
        5           | page, description             | /             | V
        6           | multiple_choice               | /             | V
        7           | multiple_choice, no answers   | /             | V
        8           | text_box                      | trigger is 6  | V
        9           | matrix                        | trigger is 5  | X
        10          | simple_choice                 | trigger is 7  | X
        11          | simple_choice, no answers     | trigger is 8  | X
        12          | text_box                      | trigger is 11 | X
        """

        my_survey = self.env['survey.survey'].create({
            'title': 'my_survey',
            'questions_layout': 'page_per_question',
            'questions_selection': 'all',
            'access_mode': 'public',
        })
        [
            page_without_description,
            text_box_1,
            numerical_box,
            _simple_choice_1,
            page_with_description,
            multiple_choice_1,
            multiple_choice_2,
            text_box_2,
            matrix,
            simple_choice_2,
            simple_choice_3,
            text_box_3,
        ] = self.env['survey.question'].create([{
            'title': 'no desc',
            'survey_id': my_survey.id,
            'sequence': 1,
            'question_type': False,
            'is_page': True,
            'description': False,
        }, {
            'title': 'text_box with invalid trigger',
            'survey_id': my_survey.id,
            'sequence': 2,
            'is_page': False,
            'question_type': 'simple_choice',
        }, {
            'title': 'numerical box with trigger that is invalid',
            'survey_id': my_survey.id,
            'sequence': 3,
            'is_page': False,
            'question_type': 'numerical_box',
        }, {
            'title': 'valid simple_choice',
            'survey_id': my_survey.id,
            'sequence': 4,
            'is_page': False,
            'question_type': 'simple_choice',
            'suggested_answer_ids': [(0, 0, {'value': 'a'})],
        }, {
            'title': 'with desc',
            'survey_id': my_survey.id,
            'sequence': 5,
            'is_page': True,
            'question_type': False,
            'description': 'This page has a description',
        }, {
            'title': 'multiple choice not conditional',
            'survey_id': my_survey.id,
            'sequence': 6,
            'is_page': False,
            'question_type': 'multiple_choice',
            'suggested_answer_ids': [(0, 0, {'value': 'a'})]
        }, {
            'title': 'multiple_choice with no answers',
            'survey_id': my_survey.id,
            'sequence': 7,
            'is_page': False,
            'question_type': 'multiple_choice',
        }, {
            'title': 'text_box with valid trigger',
            'survey_id': my_survey.id,
            'sequence': 8,
            'is_page': False,
            'question_type': 'text_box',
        }, {
            'title': 'matrix with invalid trigger (page)',
            'survey_id': my_survey.id,
            'sequence': 9,
            'is_page': False,
            'question_type': 'matrix',
        }, {
            'title': 'simple choice w/ invalid trigger (no suggested_answer_ids)',
            'survey_id': my_survey.id,
            'sequence': 10,
            'is_page': False,
            'question_type': 'simple_choice',
        }, {
            'title': 'text_box w/ invalid trigger (not a mcq)',
            'survey_id': my_survey.id,
            'sequence': 11,
            'is_page': False,
            'question_type': 'simple_choice',
            'suggested_answer_ids': False,
        }, {
            'title': 'text_box w/ invalid trigger (suggested_answer_ids is False)',
            'survey_id': my_survey.id,
            'sequence': 12,
            'is_page': False,
            'question_type': 'text_box',
        }])
        text_box_1.write({'is_conditional': True, 'triggering_question_id': multiple_choice_1.id})
        numerical_box.write({'is_conditional': True, 'triggering_question_id': text_box_1.id})
        text_box_2.write({'is_conditional': True, 'triggering_question_id': multiple_choice_1.id})
        matrix.write({'is_conditional': True, 'triggering_question_id': page_with_description.id})
        simple_choice_2.write({'is_conditional': True, 'triggering_question_id': multiple_choice_2.id})
        simple_choice_3.write({'is_conditional': True, 'triggering_question_id': text_box_2.id})
        text_box_3.write({'is_conditional': True, 'triggering_question_id': simple_choice_3.id})

        invalid_records = page_without_description + text_box_1 + numerical_box \
            + matrix + simple_choice_2 + simple_choice_3 + text_box_3
        question_and_page_ids = my_survey.question_and_page_ids
        returned_questions_and_pages = my_survey._get_pages_and_questions_to_show()

        self.assertEqual(question_and_page_ids - invalid_records, returned_questions_and_pages)
