from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('-at_install', 'post_install')
class TestSurveyLinkExpire(HttpCase):

    def test_survey_link_expire(self):
        certification = self.env['survey.survey'].create({
            'title': 'Certification',
            'survey_type': 'recruitment',
            'access_mode': 'token',
            'certification_mail_template_id': self.env.ref('hr_recruitment_survey.mail_template_applicant_interview_invite').id,
        })
        self.env['survey.question'].create({
            'title': 'Test Free Text',
            'survey_id': certification.id,
            'sequence': 2,
            'question_type': 'text_box',
        })
        job = self.env['hr.job'].create({
            'name': 'Test Job',
            'no_of_recruitment': 1,
            'survey_id': certification.id,
        })
        stage_new, stage_hired = self.env['hr.recruitment.stage'].create([
            {
                'name': 'New',
                'sequence': 0,
                'hired_stage': False,
            },
            {
                'name': 'Hired',
                'sequence': 1,
                'hired_stage': True,
            },
        ])
        test_applicant = self.env['hr.applicant'].create({
            'partner_name': 'Test Applicant',
            'email_from': 'test@applicant.com',
            'job_id': job.id,
            'stage_id': stage_new.id,
        })

        expired_link_template_text = "Interview Link Unavailable"

        # Case 1: Send initial survey, link should be valid
        survey_url = self._send_new_survey_and_get_url(test_applicant)
        self._open_url_match_text(survey_url, expired_link_template_text, contain_text=False)

        # Case 2: Refuse applicant → link should be expired
        refuse_reason = self.env['hr.applicant.refuse.reason'].create([{'name': 'Fired'}])
        applicant_get_refuse_reason = self.env['applicant.get.refuse.reason'].create([{
            'refuse_reason_id': refuse_reason.id,
            'applicant_ids': [test_applicant.id],
            'duplicates': True,
        }])
        applicant_get_refuse_reason.action_refuse_reason_apply()
        self._open_url_match_text(survey_url, expired_link_template_text)

        test_applicant.action_unarchive()
        survey_url = self._send_new_survey_and_get_url(test_applicant)

        # Case 3: Archive applicant → link should be expired
        test_applicant.action_archive()
        self._open_url_match_text(survey_url, expired_link_template_text)

        test_applicant.action_unarchive()
        survey_url = self._send_new_survey_and_get_url(test_applicant)

        # Case 4: Move applicant to hired stage → link should be expired
        test_applicant.write({'stage_id': stage_hired.id})
        self._open_url_match_text(survey_url, expired_link_template_text)

        test_applicant.write({'stage_id': stage_new.id})
        survey_url = self._send_new_survey_and_get_url(test_applicant)
        self._open_url_match_text(survey_url, expired_link_template_text, contain_text=False)

    def _send_new_survey_and_get_url(self, applicant):
        send_survey_action = applicant.action_send_survey()
        context = send_survey_action['context']
        wizard = self.env['survey.invite'].with_context(context).create({})
        wizard.action_invite()

        user_input = self.env['survey.user_input'].search([
            ('partner_id', '=', applicant.partner_id.id),
            ('expired', '=', False)
        ], order='id desc', limit=1)
        return user_input.get_start_url()

    def _open_url_match_text(self, url, text, contain_text=True):
        """
            method to check whether url response contains specific text in `it or not
        """
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        if contain_text:
            self.assertIn(text, res.content.decode('utf-8'))
        else:
            self.assertNotIn(text, res.content.decode('utf-8'))
