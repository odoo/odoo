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

    def test_refuse_single_mail_with_template_recipients(self):
        """Refusing one applicant sends the edited email to the recipients of the template,
        with the attachments of the wizard."""
        mail_template = self.env['mail.template'].create({
            'name': 'Test template',
            'model_id': self.env['ir.model']._get('hr.applicant').id,
            'email_from': 'from@test.test',
            'email_cc': 'cc@test.test',
            'email_to': '{{ object.partner_id.email }}',
            'use_default_to': False,
            'subject': 'Application refused: {{ object.partner_name }}',
            'body_html': '<p>Dear <t t-out="object.partner_name"/></p>',
        })
        refuse_reason = self.env['hr.applicant.refuse.reason'].create({
            'name': 'Not good',
            'template_id': mail_template.id,
        })
        applicant = self.env['hr.applicant'].create({
            'partner_name': 'Laurie Poiret',
            'email_from': 'laurie.poiret@aol.ru',
        })
        attachment = self.env['ir.attachment'].create({
            'name': 'feedback.txt',
            'raw': b'Some feedback',
            'mimetype': 'text/plain',
            'res_model': 'mail.compose.message',
            'res_id': 0,
        })
        action = applicant.archive_applicant()
        self.assertEqual(action['res_model'], 'applicant.refuse.single')
        applicant_refuse_single = self.env['applicant.refuse.single'].with_context(action['context']).create({
            'refuse_reason_id': refuse_reason.id,
        })
        applicant_refuse_single.write({
            'body': '<p>Dear Laurie, thank you for your time.</p>',
            'attachment_ids': attachment.ids,
        })
        self.assertTrue(applicant_refuse_single.send_mail)

        with self.mock_mail_gateway():
            applicant_refuse_single.action_refuse_reason_apply()

        self.assertSentEmail(
            'from@test.test',
            ['"Laurie Poiret" <laurie.poiret@aol.ru>'],
            subject='Application refused: Laurie Poiret',
            body_content='Dear Laurie, thank you for your time.',
            attachments_info=[{'name': 'feedback.txt', 'raw': b'Some feedback', 'type': 'text/plain'}],
        )
        self.assertIn(
            '"cc@test.test" <cc@test.test>',
            [email_cc for mail in self._mails for email_cc in mail['email_cc']],
            "The email should be sent to the CC of the template",
        )
