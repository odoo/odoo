# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('-at_install', 'post_install')
class SurveyLinkCommon(HttpCase):
    """Utilities to create and test surveys sent by email to partners/users"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.certification_survey = cls.env['survey.survey'].create(
            {
                'title': 'Flight Certification',
                'survey_type': 'recruitment',
                'access_mode': 'token',
                'certification_mail_template_id': cls.env.ref(
                    'hr_recruitment_survey.mail_template_applicant_interview_invite',
                ).id,
            },
        )
        cls.env['survey.question'].create(
            {
                'title': 'Can you fly?',
                'survey_id': cls.certification_survey.id,
                'sequence': 2,
                'question_type': 'text_box',
            },
        )
        stage_new, cls.stage_hired = cls.env['hr.recruitment.stage'].create(
            [
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
            ],
        )
        job = cls.env['hr.job'].create(
            {
                'name': 'Sheep Burner',
                'no_of_recruitment': 1,
                'survey_id': cls.certification_survey.id,
            },
        )
        cls.test_applicant = cls.env['hr.applicant'].create(
            {
                'partner_name': 'Spyro the Dragon',
                'email_from': 'spyro@the.dragon',
                'job_id': job.id,
                'stage_id': stage_new.id,
            },
        )

    def _send_new_survey_and_get_url(self) -> str:
        send_survey_action = self.test_applicant.action_send_survey()
        context = send_survey_action['context']
        wizard = self.env['survey.invite'].with_context(context).create({
            'survey_id': self.certification_survey.id,
        })
        wizard.action_invite()

        user_input = self.env['survey.user_input'].search(
            [
                ('partner_id', '=', self.test_applicant.partner_id.id),
                ('deadline', '>', fields.Datetime.now()),
            ],
            order='id desc',
            limit=1,
        )
        return user_input.get_start_url()
