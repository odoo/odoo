from odoo.tests import tagged

from odoo.addons.hr_recruitment_survey.tests.survey_link_common import (
    SurveyLinkCommon,
)


@tagged('-at_install', 'post_install')
class TestSurveyExpiration(SurveyLinkCommon):
    """
    Links to surveys should expire, and not be accessible anymore in some
    specific cases.
    This suite tests all the cases where surveys should be marked as "cancelled"
    automatically.
    """

    def _is_survey_closed(self, survey_url: str) -> bool:
        survey_closed_text = (
            "This survey is now closed. Thank you for your interest!"
        )
        res = self.url_open(survey_url)
        self.assertEqual(
            res.status_code,
            200,
            f"url_open did not succeed for survey url at {survey_url}",
        )
        return survey_closed_text in res.content.decode('utf-8')

    def test_refuse_expires_survey(self) -> None:
        survey_url = self._send_new_survey_and_get_url()
        refuse_reason = self.env['hr.applicant.refuse.reason'].create(
            [{'name': 'Fired'}],
        )
        applicant_get_refuse_reason = self.env[
            'applicant.get.refuse.reason'
        ].create(
            [
                {
                    'refuse_reason_id': refuse_reason.id,
                    'applicant_ids': [self.test_applicant.id],
                    'duplicates': True,
                },
            ],
        )
        self.assertFalse(self._is_survey_closed(survey_url))
        applicant_get_refuse_reason.action_refuse_reason_apply()
        self.assertTrue(
            self._is_survey_closed(survey_url),
            "Refusing an applicant should expire its surveys",
        )

    def test_archive_expires_survey(self) -> None:
        survey_url = self._send_new_survey_and_get_url()
        self.assertFalse(self._is_survey_closed(survey_url))
        self.test_applicant.action_archive()
        self.assertTrue(
            self._is_survey_closed(survey_url),
            "Archiving an applicant should expire its surveys",
        )

    def test_hire_applicant_expires_survey(self) -> None:
        survey_url = self._send_new_survey_and_get_url()
        self.assertFalse(self._is_survey_closed(survey_url))
        self.test_applicant.write({'stage_id': self.stage_hired.id})
        self.assertTrue(
            self._is_survey_closed(survey_url),
            "Hiring an applicant should expire its surveys",
        )

    def test_unlink_expires_survey(self) -> None:
        survey_url = self._send_new_survey_and_get_url()
        self.assertFalse(self._is_survey_closed(survey_url))
        self.test_applicant.unlink()
        self.assertTrue(
            self._is_survey_closed(survey_url),
            "Deleting an applicant should expire its surveys",
        )
