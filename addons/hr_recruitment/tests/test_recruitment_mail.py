# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCase
from odoo.tests import tagged


@tagged('recruitment_mail')
class TestRecruitmentMail(MailCase):

    def test_refuse_mail_with_template_recipients(self):
        mail_template = self.env['mail.template'].create({
            'name': 'Test template',
            'model_id': self.env['ir.model']._get('hr.applicant').id,
            'email_from': 'from@test.test',
            'email_cc': 'cc@test.test',
            'email_to': '{{ object.partner_id.email }}',
            'partner_to': self.env.user.partner_id.id,
            'use_default_to': False,
            'subject': 'Application refused: {{ object.partner_name }}'
        })
        refuse_reason = self.env['hr.applicant.refuse.reason'].create({
            'name': 'Not good',
        })
        applicant = self.env['hr.applicant'].create({
            'partner_name': 'Laurie Poiret',
            'email_from': 'laurie.poiret@aol.ru',
        })
        applicant_get_refuse_reason = self.env['applicant.get.refuse.reason'].create({
            'refuse_reason_id': refuse_reason.id,
            'applicant_ids': applicant.ids,
            'template_id': mail_template.id,
            'send_mail': True,
        })

        with self.mock_mail_gateway():
            applicant_get_refuse_reason.with_context(active_test=False).action_refuse_reason_apply()

        partner_cc = self.env['res.partner'].search([('email', '=', 'cc@test.test')])
        self.assertTrue(partner_cc)
        self.assertSentEmail(
            'from@test.test',
            [applicant.partner_id.email_formatted],
            recipients_cc=[partner_cc],
            subject='Application refused: Laurie Poiret',
        )

        # Restore applicant and set template to default
        applicant.action_unarchive()
        mail_template.email_from = False
        mail_template.use_default_to = True
        with self.mock_mail_gateway():
            applicant_get_refuse_reason.with_context(active_test=False).action_refuse_reason_apply()

        self.assertSentEmail(
            self.env.user.email_formatted,
            [applicant.partner_id.email_formatted],
            recipients_cc=[],
            subject='Application refused: Laurie Poiret',
        )
