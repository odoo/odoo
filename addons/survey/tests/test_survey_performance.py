# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.survey.tests import common
from odoo.tests import tagged
from odoo.tests.common import warmup, HttpCase


@tagged('post_install', '-at_install')
class SurveyPerformance(common.TestSurveyResultsCommon, HttpCase):

    @warmup
    def test_survey_results_with_multiple_filters_mixed_model(self):
        """ Check that, in comparison with having filters from the same model,
        having filters from different models needs only a few more queries.
        """
        url = f'/survey/results/{self.survey.id}?filters=A,0,{self.gras_id}|L,0,{self.answer_pauline.id}'
        self.authenticate('survey_manager', 'survey_manager')
        with self.assertQueryCount(default=23):
            self.url_open(url)

    @warmup
    def test_survey_results_with_multiple_filters_question_answer_model(self):
        """ Check that no matter the number of filters, if their answers
        data are stored in the same model (here survey.question.answer)
        the query count stay the same as having a single filter.
        """
        url = f'/survey/results/{self.survey.id}?filters=A,0,{self.gras_id}|A,0,{self.cat_id}'
        self.authenticate('survey_manager', 'survey_manager')
        with self.assertQueryCount(default=21):
            self.url_open(url)

    @warmup
    def test_survey_results_with_one_filter(self):
        url = f'/survey/results/{self.survey.id}?filters=A,0,{self.cat_id}'
        self.authenticate('survey_manager', 'survey_manager')
        with self.assertQueryCount(default=21):
            self.url_open(url)
