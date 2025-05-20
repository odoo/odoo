# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlparse
from uuid import uuid4

from odoo.tests import tagged

from odoo.addons.hr_recruitment_survey.tests.survey_link_common import (
    SurveyLinkCommon,
)


@tagged('-at_install', 'post_install')
class TestSurveyLink(SurveyLinkCommon):
    """
    This test suite ensures that survey url permissions behave correctly
    depending of the url used to access it
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_cynder = cls.env['res.users'].create(
            {
                'name': 'Cynder the Dragon',
                'login': 'cynder',
                'email': 'cynder@the.dragon',
            },
        )
        cls.closed_survey_txt = (
            "This survey is now closed. Thank you for your interest!"
        )
        cls.survey_access_error_txt = "Survey Access Error"

    def test_unrelated_user_valid_answer_token(self):
        """
        A survey with a valid answer_token in its url should be accessible, even
        if you're logged into an unrelated user.
        """
        survey_url = self._send_new_survey_and_get_url()
        self.authenticate(self.user_cynder.login, self.user_cynder.login)
        response = self.url_open(survey_url)
        status_code = response.status_code
        content = response.content.decode('utf-8')
        self.assertEqual(
            status_code,
            200,
            f"url_open did not succeed for survey_url at {survey_url}",
        )
        self.assertNotIn(
            self.closed_survey_txt,
            content,
            "Survey should not be closed.",
        )
        self.assertNotIn(
            self.survey_access_error_txt,
            content,
            "Any user should be able to access the survey if the url contains the correct answer_token",
        )

    def test_unrelated_user_invalid_answer_token(self):
        """
        A survey with an invalid answer_token in its url should display an
        access error.
        """
        survey_url = urlparse(self._send_new_survey_and_get_url())
        fake_answer_token = uuid4()
        is_query_answer_token_only = (
            len(survey_url.query) == len(f'answer_token={fake_answer_token}')
            and survey_url.query[: len('answer_token=')] == 'answer_token='
        )
        self.assertTrue(
            is_query_answer_token_only,
            "survey_url should only have a valid answer_token query string parameter",
        )
        survey_url = survey_url._replace(
            query=f'answer_token={fake_answer_token}',
        )
        self.authenticate(self.user_cynder.login, self.user_cynder.login)
        response = self.url_open(survey_url.geturl())
        status_code = response.status_code
        content = response.content.decode('utf-8')
        # the page shows an error, but the HTTP Code is still 200(OK)
        self.assertEqual(
            status_code,
            200,
            f"url_open did not succeed for survey_url at {survey_url}",
        )
        self.assertNotIn(
            self.closed_survey_txt,
            content,
            "Survey should not be closed.",
        )
        self.assertIn(
            self.survey_access_error_txt,
            content,
            "Accessing a survey with a wrong answer_token should show an error",
        )
