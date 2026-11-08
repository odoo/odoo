from odoo.tests import TransactionCase, tagged

from odoo.addons.hr_recruitment_survey.tests.recruitment_survey_common import (
    RecruitmentSurveyCommon,
)


@tagged('-at_install', 'post_install')
class TestRecruitmentSurveyLinkExpiration(RecruitmentSurveyCommon):
    """
    Links to surveys should expire, and not be accessible anymore in some
    specific cases.
    This suite tests all the cases where surveys should automatically expire.
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


@tagged('-at_install', 'post_install')
class TestRecruitmentSurveyExpirationScope(TransactionCase):

    def test_expire_only_surveys_of_the_applicant(self):
        """ Archiving, deleting or hiring an applicant should only expire the
        survey answers of that applicant, not the other survey answers of the
        same person (other applications, surveys not related to recruitment). """
        survey_1, survey_2, survey_other = self.env['survey.survey'].create([
            {'title': 'Interview 1', 'survey_type': 'recruitment', 'access_mode': 'token'},
            {'title': 'Interview 2', 'survey_type': 'recruitment', 'access_mode': 'token'},
            {'title': 'Customer Feedback', 'access_mode': 'token'},
        ])
        job_1, job_2 = self.env['hr.job'].create([
            {'name': 'Job 1', 'survey_id': survey_1.id},
            {'name': 'Job 2', 'survey_id': survey_2.id},
        ])
        stage_hired = self.env['hr.recruitment.stage'].create({'name': 'Hired', 'hired_stage': True})
        partner = self.env['res.partner'].create({'name': 'Spyro the Dragon', 'email': 'spyro@the.dragon'})
        applicant_1, applicant_2 = self.env['hr.applicant'].create([
            {'partner_id': partner.id, 'job_id': job_1.id},
            {'partner_id': partner.id, 'job_id': job_2.id},
        ])
        answer_1 = survey_1._create_answer(partner=partner, applicant_id=applicant_1.id)
        answer_2 = survey_2._create_answer(partner=partner, applicant_id=applicant_2.id)
        answer_other = survey_other._create_answer(partner=partner)

        applicant_1.action_archive()
        self.assertTrue(answer_1.deadline, "The survey of the archived applicant should expire")
        self.assertFalse(answer_2.deadline, "The survey of another application should not expire")
        self.assertFalse(answer_other.deadline, "A survey unrelated to recruitment should not expire")

        applicant_2.write({'stage_id': stage_hired.id})
        self.assertTrue(answer_2.deadline, "The survey of the hired applicant should expire")
        self.assertFalse(answer_other.deadline, "A survey unrelated to recruitment should not expire")
