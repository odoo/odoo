from odoo.tests import tagged, users

from odoo.addons.test_mail.tests.test_mail_composer import TestMailComposer
from odoo.addons.test_mass_mailing.tests import common


@tagged('mail_message', 'mail_tracking')
class TestMailMessage(TestMailComposer, common.TestMassMailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_marketing.write({'group_ids': [(4, cls.env.ref('mail.group_mail_template_editor').id)]})

        cls.test_template_ticket_mc = cls._create_template('mail.test.ticket.mc')

    @users('user_marketing')
    def test_message_tracking_mailing(self):
        mailing = self.env['mailing.mailing'].browse(self.mailing_bl.ids)
        recipients = self._create_mailing_test_records(model='mailing.test.blacklist', count=5)

        mailing.write({
            'mailing_domain': [('id', 'in', recipients.ids)]
        })
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing.action_send_mail()

        self.assertMailTraces(
            [{
                'email': record.email_normalized,
                'email_to_mail': record.email_from,
                'mail_values': {
                    'source_mailing_id': mailing,
                    'source_template_id': self.env['mail.template'],
                    'source_view_id': self.env['ir.ui.view'],
                },  # mail.message source audit
             } for record in recipients],
            mailing, recipients,
            check_mail=True,
        )

    @users('user_marketing')
    def test_message_tracking_mailing_composer(self):
        """Check mass_mailing_id tracking when generating messages """
        subject = 'Test Mailing Tracking'
        recipients = self.test_records  # setup of TestMailComposer -> 'mail.test.ticket.mc'

        composer = self.env['mail.compose.message'].with_context(
            self._get_web_context(recipients)
        ).create({
            'body': '<p>Body</p>',
            'subject': subject,
            'mass_mailing_create': True,
            'template_id': self.test_template_ticket_mc.id,
        })
        with self.mock_mail_gateway(mail_unlink_sent=False):
            composer._action_send_mail()
        mailing = self.env['mailing.mailing'].search([('subject', '=', subject)])
        self.assertTrue(mailing)

        self.assertMailTraces(
            [{
                'email': record.customer_id.email_normalized,
                'mail_values': {
                    'source_mailing_id': mailing,
                    'source_template_id': self.test_template_ticket_mc,
                    'source_view_id': self.env['ir.ui.view'],
                },  # mail.message source audit
                'partner': record.customer_id,
             } for record in recipients],
            mailing, recipients,
            check_mail=True,
        )
