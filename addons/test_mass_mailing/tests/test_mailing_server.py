# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mass_mailing.tests.common import TestMassMailCommon
from odoo.addons.base.tests.common import MockSmtplibCase
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger


@tagged('mass_mailing')
class TestMassMailingServer(TestMassMailCommon, MockSmtplibCase):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailingServer, cls).setUpClass()
        cls._init_mail_gateway()
        cls.env['ir.mail_server'].search([]).unlink()
        cls._init_mail_servers()
        cls.recipients = cls._create_mailing_test_records(model='mailing.test.optout', count=8)

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.addons.mass_mailing.models.mailing')
    def test_mass_mailing_server_batch(self):
        """Test that the right mail server is chosen to send the mailing.

        Test also the envelop and the SMTP headers.
        """
        # Test sending mailing in batch
        mailings = self.env['mailing.mailing'].create([{
            'subject': 'Mailing',
            'body_html': 'Body for <t t-out="object.name" />',
            'email_from': 'specific_user@test.com',
            'mailing_model_id': self.env['ir.model']._get('mailing.test.optout').id,
        }, {
            'subject': 'Mailing',
            'body_html': 'Body for <t t-out="object.name" />',
            'email_from': 'unknown_name@test.com',
            'mailing_model_id': self.env['ir.model']._get('mailing.test.optout').id,
        }])
        with self.mock_smtplib_connection():
            mailings.action_send_mail()
        self.assertEqual(self.find_mail_server_mocked.call_count, 2, 'Must be called only once per mail from')

        self.assert_email_sent_smtp(
            smtp_from='specific_user@test.com',
            message_from='specific_user@test.com',
            from_filter=self.server_user.from_filter,
            emails_count=8,
        )

        self.assert_email_sent_smtp(
            # Must use the bounce address here because the mail server
            # is configured for the entire domain "test.com"
            smtp_from=lambda x: 'bounce' in x,
            message_from='unknown_name@test.com',
            from_filter=self.server_domain.from_filter,
            emails_count=8,
        )

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.addons.mass_mailing.models.mailing')
    def test_mass_mailing_server_default(self):
        # We do not have a mail server for this address email, so fall back to the
        # "notifications@domain" email.
        mailings = self.env['mailing.mailing'].create([{
            'subject': 'Mailing',
            'body_html': 'Body for <t t-out="object.name" />',
            'email_from': '"Testing" <unknow_email@unknow_domain.com>',
            'mailing_model_id': self.env['ir.model']._get('mailing.test.optout').id,
        }])

        with self.mock_smtplib_connection():
            mailings.action_send_mail()

        self.assertEqual(self.find_mail_server_mocked.call_count, 1)
        self.assert_email_sent_smtp(
            smtp_from='notifications@test.com',
            message_from='"Testing" <notifications@test.com>',
            from_filter=self.server_notification.from_filter,
            emails_count=8,
        )

        self.assertEqual(self.find_mail_server_mocked.call_count, 1, 'Must be called only once')

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.addons.mass_mailing.models.mailing')
    def test_mass_mailing_server_forced(self):
        # We force a mail server on one mailing
        mailings = self.env['mailing.mailing'].create([{
            'subject': 'Mailing',
            'body_html': 'Body for <t t-out="object.name" />',
            'email_from': self.server_user.from_filter,
            'mailing_model_id': self.env['ir.model']._get('mailing.test.optout').id,
        }, {
            'subject': 'Mailing',
            'body_html': 'Body for <t t-out="object.name" />',
            'email_from': 'unknow_email@unknow_domain.com',
            'mailing_model_id': self.env['ir.model']._get('mailing.test.optout').id,
            'mail_server_id': self.server_notification.id,
        }])
        with self.mock_smtplib_connection():
            mailings.action_send_mail()
        self.assertEqual(self.find_mail_server_mocked.call_count, 1, 'Must not be called when mail server is forced')

        self.assert_email_sent_smtp(
            smtp_from='specific_user@test.com',
            message_from='specific_user@test.com',
            from_filter=self.server_user.from_filter,
            emails_count=8,
        )

        self.assert_email_sent_smtp(
            smtp_from='unknow_email@unknow_domain.com',
            message_from='unknow_email@unknow_domain.com',
            from_filter=self.server_notification.from_filter,
            emails_count=8,
        )
