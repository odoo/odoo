# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo.tests import tagged

from odoo.addons.survey.controllers.main import Survey
from odoo.addons.survey.tests import common
from odoo.addons.website.tools import MockRequest


@tagged("is_query_count")
class TestSurveyResults(common.TestSurveyResultsCommon):
    """ Check the results and the performance of the different filters combinations.
    The filters can be combined but their query count doesn't add up if their
    related question answers data are stored in the same model.
    """

    def setUp(self):
        super(TestSurveyResults, self).setUp()
        self.SurveyController = Survey()

    def test_get_filters_from_post(self):
        """ Check that the filters are correctly retrieved from the post. """
        # Matrix filter | simple_choice or multiple_choice filter | char_box, text_box, numerical_box, date or datetime filter
        post = {'filters': 'A,14,101|A,0,58|L,0,2'}
        with MockRequest(self.env):
            answer_by_column, user_input_lines_ids = self.SurveyController._get_filters_from_post(post)
        self.assertEqual(answer_by_column, {101: [14], 58: []})
        self.assertEqual(user_input_lines_ids, [2])

        # Multiple matrix filters
        post = {'filters': 'A,14,101|A,20,205'}
        with MockRequest(self.env):
            answer_by_column, user_input_lines_ids = self.SurveyController._get_filters_from_post(post)
        self.assertEqual(answer_by_column, {101: [14], 205: [20]})
        self.assertFalse(user_input_lines_ids)

        # Multiple filters on the same matrix column
        post = {'filters': 'A,14,101|A,20,101'}
        with MockRequest(self.env):
            answer_by_column, user_input_lines_ids = self.SurveyController._get_filters_from_post(post)
        self.assertEqual(answer_by_column, {101: [14, 20]})
        self.assertFalse(user_input_lines_ids)

        # No model associated with the J letter, the second filter should be ignored
        post = {'filters': 'A,0,9|J,40,3'}
        with MockRequest(self.env):
            answer_by_column, user_input_lines_ids = self.SurveyController._get_filters_from_post(post)
        self.assertEqual(answer_by_column, {9: []})
        self.assertFalse(user_input_lines_ids)

    def test_results_page_filters_survey_matrix(self):
        """ Same as 'test_results_page_filters_survey_question_answer_model'
        but with a matrix-type question (additional record involved for the row)
        """
        post = {'filters': f'A,{self.strawberries_row_id},{self.spring_id}'}
        expected_user_input_lines = self.user_input_1.user_input_line_ids + self.user_input_2.user_input_line_ids
        self._check_results_and_query_count(post, expected_user_input_lines, 3)

    def test_results_page_filters_survey_matrix_mixed_models(self):
        """ Same as 'test_results_page_filters_survey_mixed_models'
        but with a matrix-type question (additional record involved for the row)
        """
        post = {'filters': f'A,{self.strawberries_row_id},{self.spring_id}|L,0,{self.answer_pauline.id}'}
        expected_user_input_lines = self.user_input_2.user_input_line_ids
        self._check_results_and_query_count(post, expected_user_input_lines, 5)

    def test_results_page_filters_survey_matrix_multiple(self):
        """ Same as 'test_results_page_filters_survey_question_answer_model_multiple'
        but with matrix-type questions (additional records involved for the rows)
        """
        post = {'filters': f'A,{self.strawberries_row_id},{self.spring_id}|A,{self.ficus_row_id},{self.once_a_week_id}'}
        expected_user_input_lines = self.user_input_1.user_input_line_ids
        self._check_results_and_query_count(post, expected_user_input_lines, 3)

    def test_results_page_filters_survey_matrix_multiple_same_column(self):
        """ Same as 'test_results_page_filters_survey_matrix_multiple' but
        checking the case where the same answer id can be related to multiple row ids.
        """
        post = {'filters': f'A,{self.strawberries_row_id},{self.spring_id}|A,{self.apples_row_id},{self.spring_id}'}
        expected_user_input_lines = self.user_input_2.user_input_line_ids
        self._check_results_and_query_count(post, expected_user_input_lines, 3)

    def test_results_page_filters_survey_mixed_models(self):
        """ Check results and performance of matching filters across different answer models
        ('survey.question.answer' and 'survey.user_input.line' models)
        """
        post = {'filters': f'A,0,{self.gras_id}|L,0,{self.answer_pauline.id}'}
        expected_user_input_lines = self.user_input_2.user_input_line_ids
        self._check_results_and_query_count(post, expected_user_input_lines, 5)

    def test_results_page_filters_survey_question_answer_model(self):
        """ Check results and performance of matching one filter using
        the 'survey.question.answer' answer model
        """
        post = {'filters': f'A,0,{self.gras_id}'}
        expected_user_input_lines = self.user_input_1.user_input_line_ids + self.user_input_2.user_input_line_ids
        self._check_results_and_query_count(post, expected_user_input_lines, 3)

    def test_results_page_filters_survey_question_answer_model_multiple(self):
        """ Check results and performance of matching multiple filters using
        the 'survey.question.answer' answer model
        """
        post = {'filters': f'A,0,{self.gras_id}|A,0,{self.cat_id}'}
        expected_user_input_lines = self.user_input_1.user_input_line_ids
        self._check_results_and_query_count(post, expected_user_input_lines, 3)

    def test_results_page_filters_survey_user_input_line_model(self):
        """ Check results and performance of matching one filter using
        the 'survey.user_input.line' answer model
        """
        post = {'filters': f'L,0,{self.answer_24.id}'}
        expected_user_input_lines = self.user_input_1.user_input_line_ids + self.user_input_2.user_input_line_ids
        self._check_results_and_query_count(post, expected_user_input_lines, 3)

    def test_results_page_filters_survey_user_input_line_model_multiple(self):
        """ Check results and performance of matching multiple filters using
        the 'survey.user_input.line' answer model
        """
        post = {'filters': f'L,0,{self.answer_24.id}|L,0,{self.answer_pauline.id}'}
        expected_user_input_lines = self.user_input_2.user_input_line_ids
        self._check_results_and_query_count(post, expected_user_input_lines, 3)

    def test_statistics_scale(self):
        """ Test statistics of scale question. """
        with MockRequest(self.env):
            found_user_input_lines, _ = self.SurveyController._extract_filters_data(self.survey, {})
        data = self.question_scale._prepare_statistics(found_user_input_lines)[0]
        self.assertEqual(data['table_data'],
                         [{'value': str(value),
                           'suggested_answer': self.env['survey.question.answer'],
                           'count': 1 if value in (5, 7) else 0,
                           'count_text': f"{1 if value in (5, 7) else 0} Votes"}
                          for value in range(11)])
        self.assertEqual(json.loads(data['graph_data']),
                         [{'key': self.question_scale.title,
                           'values': [{'text': str(value),
                                       'count': 1 if value in (5, 7) else 0}
                                      for value in range(11)]}])
        self.assertEqual(data['numerical_max'], 7)
        self.assertEqual(data['numerical_min'], 5)
        self.assertEqual(data['numerical_average'], 6)
        # Test that a skipped value is not interpreted as a 0 value
        self.scale_answer_line_2.write({
            'value_scale': False,
            'skipped': True,
            'answer_type': False,
        })
        data = self.question_scale._prepare_statistics(found_user_input_lines)[0]
        self.assertEqual(data['table_data'],
                         [{'value': str(value),
                           'suggested_answer': self.env['survey.question.answer'],
                           'count': 1 if value == 5 else 0,
                           'count_text': f"{1 if value == 5 else 0} Votes"}
                          for value in range(11)])
        self.assertEqual(data['numerical_max'], 5)
        self.assertEqual(data['numerical_min'], 5)
        self.assertEqual(data['numerical_average'], 5)

    def _check_results_and_query_count(self, post, expected_user_input_lines, expected_query_count):
        """ Check that, depending on the URL filters, the _extract_filters_data method
        is correctly returning the expected user input lines.
        """
        self.env.invalidate_all() # clear env cache to not impact the query count
        with MockRequest(self.env), self.assertQueryCount(expected_query_count):
            found_user_input_lines, _ = self.SurveyController._extract_filters_data(self.survey, post)
        self.assertEqual(expected_user_input_lines, found_user_input_lines)
