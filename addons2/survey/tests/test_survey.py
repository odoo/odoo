# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import _, Command, fields
from odoo.addons.mail.tests.common import MailCase
from odoo.addons.survey.tests import common
from odoo.tests.common import users


class TestSurveyInternals(common.TestSurveyCommon, MailCase):

    @users('survey_manager')
    def test_allowed_triggering_question_ids(self):
        # Create 2 surveys, each with 3 questions, each with 2 suggested answers
        survey_1, survey_2 = self.env['survey.survey'].create([
            {'title': 'Test Survey 1', 'session_code': '10000'},
            {'title': 'Test Survey 2', 'session_code': '10001'}
        ])
        self.env['survey.question'].create([
            {
                'survey_id': survey_id,
                'title': f'Question {question_idx}',
                'question_type': 'simple_choice',
                'suggested_answer_ids': [
                    Command.create({
                        'value': f'Answer {answer_idx}',
                    }) for answer_idx in range(2)],
            }
            for question_idx in range(3)
            for survey_id in (survey_1 | survey_2).ids
        ])
        survey_1_q_1, survey_1_q_2, _ = survey_1.question_ids
        survey_2_q_1, survey_2_q_2, _ = survey_2.question_ids

        with self.subTest('Editing existing questions'):
            # Only previous questions from the same survey
            self.assertFalse(bool(survey_1_q_2.allowed_triggering_question_ids & survey_2_q_2.allowed_triggering_question_ids))
            self.assertEqual(survey_1_q_2.allowed_triggering_question_ids, survey_1_q_1)
            self.assertEqual(survey_2_q_2.allowed_triggering_question_ids, survey_2_q_1)

        survey_1_new_question = self.env['survey.question'].new({'survey_id': survey_1})
        survey_2_new_question = self.env['survey.question'].new({'survey_id': survey_2})

        with self.subTest('New questions'):
            # New questions should be allowed to use any question with choices from the same survey
            self.assertFalse(
                bool(survey_1_new_question.allowed_triggering_question_ids & survey_2_new_question.allowed_triggering_question_ids)
            )
            self.assertEqual(survey_1_new_question.allowed_triggering_question_ids.ids, survey_1.question_ids.ids)
            self.assertEqual(survey_2_new_question.allowed_triggering_question_ids.ids, survey_2.question_ids.ids)

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
            question.validate_question('Is Alfred an answer?'),
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
            question.validate_question('Is Alfred an answer?'),
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

    def test_simple_choice_question_answer_result(self):
        test_survey = self.env['survey.survey'].create({
            'title': 'Test This Survey',
            'scoring_type': 'scoring_with_answers',
            'scoring_success_min': 80.0,
        })
        [a_01, a_02, a_03, a_04] = self.env['survey.question.answer'].create([{
            'value': 'In Europe',
            'answer_score': 0.0,
            'is_correct': False
        }, {
            'value': 'In Asia',
            'answer_score': 5.0,
            'is_correct': True
        }, {
            'value': 'In South Asia',
            'answer_score': 10.0,
            'is_correct': True
        }, {
            'value': 'On Globe',
            'answer_score': 5.0,
            'is_correct': False
        }])
        q_01 = self.env['survey.question'].create({
            'survey_id': test_survey.id,
            'title': 'Where is india?',
            'sequence': 1,
            'question_type': 'simple_choice',
            'suggested_answer_ids': [(6, 0, (a_01 | a_02 | a_03 | a_04).ids)]
        })

        user_input = self.env['survey.user_input'].create({'survey_id': test_survey.id})
        user_input_line = self.env['survey.user_input.line'].create({
            'user_input_id': user_input.id,
            'question_id': q_01.id,
            'answer_type': 'suggestion',
            'suggested_answer_id': a_01.id
        })

        # this answer is incorrect with no score: should be considered as incorrect
        statistics = user_input._prepare_statistics()[user_input]
        self.assertAnswerStatus('Incorrect', statistics)

        # this answer is correct with a positive score (even if not the maximum): should be considered as correct
        user_input_line.suggested_answer_id = a_02.id
        statistics = user_input._prepare_statistics()[user_input]
        self.assertAnswerStatus('Correct', statistics)

        # this answer is correct with the best score: should be considered as correct
        user_input_line.suggested_answer_id = a_03.id
        statistics = user_input._prepare_statistics()[user_input]
        self.assertAnswerStatus('Correct', statistics)

        # this answer is incorrect but has a score: should be considered as "partially"
        user_input_line.suggested_answer_id = a_04.id
        statistics = user_input._prepare_statistics()[user_input]
        self.assertAnswerStatus('Partially', statistics)

    @users('survey_manager')
    def test_skipped_values(self):
        """ Create one question per type of questions.
        Make sure they are correctly registered as 'skipped' after saving an empty answer for each
        of them. """

        questions = self._create_one_question_per_type()
        survey_user = self.survey._create_answer(user=self.survey_user)

        for question in questions:
            answer = '' if question.question_type in ['char_box', 'text_box'] else None
            survey_user._save_lines(question, answer)

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
        q_is_vegetarian_text = 'Are you vegetarian?'
        q_is_vegetarian = self._add_question(
            self.page_0, q_is_vegetarian_text, 'multiple_choice', survey_id=self.survey.id,
            sequence=100, labels=[{'value': 'Yes'}, {'value': 'No'}, {'value': 'Sometimes'}])
        q_food_vegetarian_text = 'Choose your green meal'
        self._add_question(self.page_0, q_food_vegetarian_text, 'multiple_choice',
                           sequence=101,
                           triggering_answer_ids=[q_is_vegetarian.suggested_answer_ids[0].id,
                                                  q_is_vegetarian.suggested_answer_ids[2].id],
                           survey_id=self.survey.id,
                           labels=[{'value': 'Vegetarian pizza'}, {'value': 'Vegetarian burger'}])
        q_food_not_vegetarian_text = 'Choose your meal in case we serve meet/fish'
        self._add_question(self.page_0, q_food_not_vegetarian_text, 'multiple_choice',
                           sequence=102,
                           triggering_answer_ids=q_is_vegetarian.suggested_answer_ids[1].ids,
                           survey_id=self.survey.id,
                           labels=[{'value': 'Steak with french fries'}, {'value': 'Fish'}])

        # Clone the survey
        survey_clone = self.survey.copy()

        # Verify the conditional layout and that the cloned survey doesn't reference the original survey
        q_is_vegetarian_cloned = get_question_by_title(survey_clone, q_is_vegetarian_text)
        q_food_vegetarian_cloned = get_question_by_title(survey_clone, q_food_vegetarian_text)
        q_food_not_vegetarian_cloned = get_question_by_title(survey_clone, q_food_not_vegetarian_text)

        self.assertFalse(bool(q_is_vegetarian_cloned.triggering_answer_ids))

        # Vegetarian choice
        self.assertTrue(bool(q_food_vegetarian_cloned))
        # Correct conditional layout
        self.assertEqual(q_food_vegetarian_cloned.triggering_answer_ids.ids,
                         [q_is_vegetarian_cloned.suggested_answer_ids[0].id, q_is_vegetarian_cloned.suggested_answer_ids[2].id])
        # Doesn't reference the original survey
        self.assertNotEqual(q_food_vegetarian_cloned.triggering_answer_ids.ids,
                            [q_is_vegetarian.suggested_answer_ids[0].id, q_is_vegetarian.suggested_answer_ids[2].id])

        # Not vegetarian choice
        self.assertTrue(bool(q_food_not_vegetarian_cloned.triggering_answer_ids))
        # Correct conditional layout
        self.assertEqual(q_food_not_vegetarian_cloned.triggering_answer_ids.ids,
                         q_is_vegetarian_cloned.suggested_answer_ids[1].ids)
        # Doesn't reference the original survey
        self.assertNotEqual(q_food_not_vegetarian_cloned.triggering_answer_ids.ids,
                            q_is_vegetarian.suggested_answer_ids[1].ids)

    @users('survey_manager')
    def test_copy_conditional_question_with_sequence_changed(self):
        """ Create a survey with two questions, change the sequence of the questions,
        set the second question as conditional on the first one, and check that the conditional
        question is still conditional on the first one after copying the survey."""

        def get_question_by_title(survey, title):
            return survey.question_ids.filtered(lambda q: q.title == title)[0]

        # Create the survey questions
        q_1 = self._add_question(
            self.page_0, 'Q1', 'multiple_choice', survey_id=self.survey.id,
            sequence=200, labels=[{'value': 'Yes'}, {'value': 'No'}])
        q_2 = self._add_question(
            self.page_0, 'Q2', 'multiple_choice', survey_id=self.survey.id,
            sequence=300, labels=[{'value': 'Yes'}, {'value': 'No'}])

        # Change the sequence of the second question to be before the first one
        q_2.write({'sequence': 100})

        # Set a conditional question on the first question
        q_1.write({'triggering_answer_ids': [Command.set([q_2.suggested_answer_ids[0].id])]})

        (q_1 | q_2).invalidate_recordset()

        # Clone the survey
        cloned_survey = self.survey.copy()

        # Check that the sequence of the questions are the same as the original survey
        self.assertEqual(get_question_by_title(cloned_survey, 'Q1').sequence, q_1.sequence)
        self.assertEqual(get_question_by_title(cloned_survey, 'Q2').sequence, q_2.sequence)

        # Check that the conditional question is correctly copied to the right question
        self.assertEqual(
            get_question_by_title(cloned_survey, 'Q1').triggering_answer_ids[0].value, q_1.triggering_answer_ids[0].value
        )
        self.assertFalse(bool(get_question_by_title(cloned_survey, 'Q2').triggering_answer_ids))

    @users('survey_manager')
    def test_matrix_rows_display_name(self):
        """Check that matrix rows' display name is not changed."""
        # A case's shape is: (question title, row value, expected row display names)
        cases = [
            (
                'Question 1',
                'Row A is short, so what?',
                'Row A is short, so what?',
            ), (
                'Question 2',
                'Row B is a very long question, but it is shown by itself so there shouldn\'t be any change',
                'Row B is a very long question, but it is shown by itself so there shouldn\'t be any change',
            ),
        ]

        for question_title, row_value, exp_display_name in cases:
            question = self.env['survey.question'].create({
                'title': question_title,
                'matrix_row_ids': [Command.create({'value': row_value})],
            })

            with self.subTest(question=question_title, row=row_value):
                self.assertEqual(question.matrix_row_ids[0].display_name, exp_display_name)

    @users('survey_manager')
    def test_suggested_answer_display_name(self):
        """Check that answers' display name is not too long and allows to identify the question & answer.

        When a matrix answer though, simply show the value as the question and row should be made
        clear via the survey.user.input.line context."""
        # A case's shape is: (question title, answer value, expected display name, additional create values)
        cases = [
            (
                'Question 1',
                'Answer A is short',
                'Question 1 : Answer A is short',
                {}
            ), (
                'Question 2',
                'Answer B is a very long answer, so it should itself be shortened or we would go too far',
                'Question 2 : Answer B is a very long answer, so it should itself be shortened or we...',
                {}
            ), (
                'Question 3 is a very long question, so what can we do?',
                'Answer A is short',
                'Question 3 is a very long question, so what can we do? : Answer A is short',
                {}
            ), (
                'Question 4 is a very long question, so what can we do?',
                'Answer B is a bit too long for Q4 now',
                'Question 4 is a very long question, so what can... : Answer B is a bit too long for Q4 now',
                {}
            ), (
                'Question 5 is a very long question, so what can we do?',
                'Answer C is so long that both the question and the answer will be shortened',
                'Question 5 is a very long... : Answer C is so long that both the question and the...',
                {}
            ), (
                'Question 6',
                'Answer A is short, so what?',
                'Answer A is short, so what?',
                {'question_type': 'matrix'},
            ), (
                'Question 7',
                'Answer B is a very long answer, but it is shown by itself so there shouldn\'t be any change',
                'Answer B is a very long answer, but it is shown by itself so there shouldn\'t be any change',
                {'question_type': 'matrix'},
            ),
        ]

        for question_title, answer_value, exp_display_name, other_values in cases:
            question = self.env['survey.question'].create({
                'title': question_title,
                'suggested_answer_ids': [Command.create({'value': answer_value})],
                **other_values
            })

            with self.subTest(question=question_title, answer=answer_value):
                self.assertEqual(question.suggested_answer_ids[0].display_name, exp_display_name)

    @users('survey_manager')
    def test_unlink_triggers(self):
        # Create the survey questions
        q_is_vegetarian_text = 'Are you vegetarian?'
        q_is_vegetarian = self._add_question(
            self.page_0, q_is_vegetarian_text, 'simple_choice', survey_id=self.survey.id, sequence=100,
            labels=[{'value': 'Yes'}, {'value': 'No'}, {'value': 'It depends'}], constr_mandatory=True,
        )

        q_is_kinda_vegetarian_text = 'Would you prefer a veggie meal if possible?'
        q_is_kinda_vegetarian = self._add_question(
            self.page_0, q_is_kinda_vegetarian_text, 'simple_choice', survey_id=self.survey.id, sequence=101,
            labels=[{'value': 'Yes'}, {'value': 'No'}], constr_mandatory=True, triggering_answer_ids=[
                Command.link(q_is_vegetarian.suggested_answer_ids[1].id),  # It depends
            ],
        )

        q_food_vegetarian_text = 'Choose your green meal'
        veggie_question = self._add_question(
            self.page_0, q_food_vegetarian_text, 'simple_choice', survey_id=self.survey.id, sequence=102,
            labels=[{'value': 'Vegetarian pizza'}, {'value': 'Vegetarian burger'}], constr_mandatory=True,
            triggering_answer_ids=[
                Command.link(q_is_vegetarian.suggested_answer_ids[0].id),  # Veggie
                Command.link(q_is_kinda_vegetarian.suggested_answer_ids[0].id),  # Would prefer veggie
            ])

        q_food_not_vegetarian_text = 'Choose your meal'
        not_veggie_question = self._add_question(
            self.page_0, q_food_not_vegetarian_text, 'simple_choice', survey_id=self.survey.id, sequence=103,
            labels=[{'value': 'Steak with french fries'}, {'value': 'Fish'}], constr_mandatory=True,
            triggering_answer_ids=[
                Command.link(q_is_vegetarian.suggested_answer_ids[1].id),  # Not a veggie
                Command.link(q_is_kinda_vegetarian.suggested_answer_ids[1].id),  # Would not prefer veggie
            ],
        )

        q_is_kinda_vegetarian.unlink()

        # Deleting one trigger but maintaining another keeps conditional behavior
        self.assertTrue(bool(veggie_question.triggering_answer_ids))

        q_is_vegetarian.suggested_answer_ids[0].unlink()

        # Deleting answer Yes makes the following question always visible
        self.assertFalse(bool(veggie_question.triggering_answer_ids))

        # But the other is still conditional
        self.assertEqual(not_veggie_question.triggering_answer_ids[0].id, q_is_vegetarian.suggested_answer_ids[0].id)

        q_is_vegetarian.unlink()

        # Now it will also be always visible
        self.assertFalse(bool(not_veggie_question.triggering_answer_ids))

    def test_get_correct_answers(self):
        questions = self._create_one_question_per_type_with_scoring()
        qtype_mapping = {q.question_type: q for q in questions}
        expected_correct_answer = {
            qtype_mapping['numerical_box'].id: 5,
            qtype_mapping['date'].id: '10/16/2023',
            qtype_mapping['datetime'].id: '11/17/2023 08:00:00',
            qtype_mapping['simple_choice'].id:
                qtype_mapping['simple_choice'].suggested_answer_ids.filtered_domain([('value', '=', 'SChoice0')]).ids,
            qtype_mapping['multiple_choice'].id:
                qtype_mapping['multiple_choice'].suggested_answer_ids.filtered_domain([('value', 'in', ['MChoice0', 'MChoice1'])]).ids,
        }
        self.assertEqual(questions._get_correct_answers(), expected_correct_answer)

    def test_get_pages_and_questions_to_show(self):
        """
        Tests the method `_get_pages_and_questions_to_show` - it takes a recordset of
        question.question from a survey.survey and returns a recordset without
        invalid conditional questions and pages without description

        Structure of the test survey:

        sequence   | type                         | trigger           | validity
        ----------------------------------------------------------------------
        1          | page, no description         | /                 | X
        2          | simple_choice                | trigger is 5      | X
        3          | simple_choice                | trigger is 2      | X
        4          | page, description            | /                 | V
        5          | multiple_choice              | /                 | V
        6          | text_box                     | triggers are 5+7  | V
        7          | multiple_choice              |                   | V
        """

        my_survey = self.env['survey.survey'].create({
            'title': 'my_survey',
            'questions_layout': 'page_per_question',
            'questions_selection': 'all',
            'access_mode': 'public',
        })
        [
            page_without_description,
            simple_choice_1,
            simple_choice_2,
            _page_with_description,
            multiple_choice_1,
            text_box_2,
            multiple_choice_2,
        ] = self.env['survey.question'].create([{
            'title': 'no desc',
            'survey_id': my_survey.id,
            'sequence': 1,
            'question_type': False,
            'is_page': True,
            'description': False,
        }, {
            'title': 'simple choice with invalid trigger',
            'survey_id': my_survey.id,
            'sequence': 2,
            'is_page': False,
            'question_type': 'simple_choice',
            'suggested_answer_ids': [(0, 0, {'value': 'a'})],
        }, {
            'title': 'simple_choice with chained invalid trigger',
            'survey_id': my_survey.id,
            'sequence': 3,
            'is_page': False,
            'question_type': 'simple_choice',
            'suggested_answer_ids': [(0, 0, {'value': 'a'})],
        }, {
            'title': 'with desc',
            'survey_id': my_survey.id,
            'sequence': 4,
            'is_page': True,
            'question_type': False,
            'description': 'This page has a description',
        }, {
            'title': 'multiple choice not conditional',
            'survey_id': my_survey.id,
            'sequence': 5,
            'is_page': False,
            'question_type': 'multiple_choice',
            'suggested_answer_ids': [(0, 0, {'value': 'a'})]
        }, {
            'title': 'text_box with valid trigger',
            'survey_id': my_survey.id,
            'sequence': 6,
            'is_page': False,
            'question_type': 'text_box',
        }, {
            'title': 'valid multiple_choice',
            'survey_id': my_survey.id,
            'sequence': 7,
            'is_page': False,
            'question_type': 'multiple_choice',
            'suggested_answer_ids': [(0, 0, {'value': 'a'})]
        }])
        simple_choice_1.write({'triggering_answer_ids': multiple_choice_1.suggested_answer_ids})
        simple_choice_2.write({'triggering_answer_ids': multiple_choice_1.suggested_answer_ids})
        text_box_2.write({'triggering_answer_ids': (multiple_choice_1 | multiple_choice_2).suggested_answer_ids})
        invalid_records = page_without_description + simple_choice_1 + simple_choice_2
        question_and_page_ids = my_survey.question_and_page_ids
        returned_questions_and_pages = my_survey._get_pages_and_questions_to_show()

        self.assertEqual(question_and_page_ids - invalid_records, returned_questions_and_pages)

    def test_notify_subscribers(self):
        """Check that messages are posted only if there are participation followers"""
        survey_2 = self.survey.copy()
        survey_participation_subtype = self.env.ref('survey.mt_survey_survey_user_input_completed')
        user_input_participation_subtype = self.env.ref('survey.mt_survey_user_input_completed')
        # Make survey_user (group_survey_user) follow participation to survey (they follow), not survey 2 (no followers)
        self.survey.message_subscribe(partner_ids=self.survey_user.partner_id.ids, subtype_ids=survey_participation_subtype.ids)
        # Complete a participation for both surveys, only one should trigger a notification for followers
        user_inputs = self.env['survey.user_input'].create([{'survey_id': survey.id} for survey in (self.survey, survey_2)])
        with self.mock_mail_app():
            user_inputs._mark_done()
        self.assertEqual(len(self._new_msgs), 1)
        self.assertMessageFields(
            self._new_msgs,
            {
                'model': 'survey.user_input',
                'subtype_id': user_input_participation_subtype,
                'res_id': user_inputs[0].id,
                'notified_partner_ids': self.survey_user.partner_id
            },
        )

    def assertAnswerStatus(self, expected_answer_status, questions_statistics):
        """Assert counts for 'Correct', 'Partially', 'Incorrect', 'Unanswered' are 0, and 1 for our expected answer status"""
        for status, count in [(total['text'], total['count']) for total in questions_statistics['totals']]:
            self.assertEqual(count, 1 if status == expected_answer_status else 0)
