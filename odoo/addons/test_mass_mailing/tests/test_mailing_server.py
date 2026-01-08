# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mass_mailing.tests.common import TestMassMailCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger


@tagged('mass_mailing', 'mail_server')
class TestMassMailingServer(TestMassMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailingServer, cls).setUpClass()
        cls.recipients = cls._create_mailing_test_records(model='mailing.test.optout', count=8)

    def test_mass_mailing_server_archived_usage_protection(self):
        """ Test the protection against using archived server:
        - servers used cannot be archived
        - mailing clone of a mailing with an archived server gets the default one instead
        """
        servers = self.env['ir.mail_server'].create([{
            'name': 'Server 1',
            'smtp_host': 'archive-test1.smtp.local',
        }, {
            'name': 'Server 2',
            'smtp_host': 'archive-test2.smtp.local',
        }])
        self.env['ir.config_parameter'].set_param('mass_mailing.mail_server_id', servers[0].id)
        mailing = self.env['mailing.mailing'].create({
            'subject': 'Mailing',
            'body_html': 'Body for <t t-out="object.name" />',
            'email_from': 'specific_user@test.com',
            'mailing_model_id': self.env['ir.model']._get('mailing.test.optout').id,
        })

        mailing_clone = mailing.copy()
        self.assertEqual(mailing_clone.mail_server_id.id, servers[0].id,
                         'The clone of a mailing inherits from the server of the copied mailing')
        with self.assertRaises(UserError, msg='Servers still used as default and for 2 mailings'):
            servers.action_archive()
        self.assertTrue(all(server.active for server in servers), 'All servers must be active')
        self.env['ir.config_parameter'].set_param('mass_mailing.mail_server_id', False)
        with self.assertRaises(UserError, msg='Servers still used for 2 mailings'):
            servers.action_archive()
        self.assertTrue(all(server.active for server in servers), 'All servers must be active')
        with self.mock_smtplib_connection():
            mailing.action_send_mail()
        with self.assertRaises(UserError, msg='Servers still used for 1 mailings'):
            servers.action_archive()
        self.assertTrue(all(server.active for server in servers), 'All servers must be active')
        with self.mock_smtplib_connection():
            mailing_clone.action_send_mail()
        servers.action_archive()  # Servers no more used -> no error
        self.assertFalse(servers.filtered('active'), 'All servers must be archived')
        self.assertFalse(mailing.copy().mail_server_id,
                         'The clone of a mailing with an archived server gets the default one (none here)')
        servers[1].action_unarchive()
        self.env['ir.config_parameter'].set_param('mass_mailing.mail_server_id', servers[1].id)
        mailing_clone = mailing.copy()
        self.assertEqual(mailing_clone.mail_server_id.id, servers[1].id,
                         'The clone of a mailing with an archived server gets the default one')
        mailing_clone.action_archive()
        with self.assertRaises(UserError, msg='Servers still used as default'):
            servers.action_archive()
        self.assertTrue(servers[1].active)
        self.env['ir.config_parameter'].set_param('mass_mailing.mail_server_id', False)
        servers.action_archive()  # Servers no more used -> no error
        self.assertFalse(servers.filtered('active'), 'All servers must be archived')

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.addons.mass_mailing.models.mailing')
    def test_mass_mailing_server_find(self):
        """Test that the right mail server is chosen to send the mailing.

        Test also the envelop and the SMTP headers.
        """
        mailings = self.env['mailing.mailing'].create([{
            'subject': 'Mailing',
            'body_html': 'Body for <t t-out="object.name" />',
            'email_from': 'specific_user@test.mycompany.com',
            'mailing_model_id': self.env['ir.model']._get_id('mailing.test.optout'),
        }, {
            'subject': 'Mailing',
            'body_html': 'Body for <t t-out="object.name" />',
            'email_from': 'unknown_name@test.mycompany.com',
            'mailing_model_id': self.env['ir.model']._get_id('mailing.test.optout'),
        }, {
            'subject': 'Mailing',
            'body_html': 'Body for <t t-out="object.name" />',
            'email_from': '"Testing" <unknow_email@unknow_domain.com>',
            'mailing_model_id': self.env['ir.model']._get_id('mailing.test.optout'),
        }, {
            'subject': 'Mailing Forced',
            'body_html': 'Body for <t t-out="object.name" />',
            'email_from': 'unknow_email@unknow_domain.com',
            'mailing_model_id': self.env['ir.model']._get_id('mailing.test.optout'),
            'mail_server_id': self.mail_server_notification.id,
        }])
        with self.mock_smtplib_connection():
            mailings.action_send_mail()
        self.assertEqual(self.find_mail_server_mocked.call_count, 3, 'Must be called only once per mail from except when forced')

        for (expected_smtp_from, expected_msg_from, expected_mail_server) in [
            ('specific_user@test.mycompany.com', 'specific_user@test.mycompany.com', self.mail_server_user),
            (f'{self.alias_bounce}@{self.alias_domain}', 'unknown_name@test.mycompany.com', self.mail_server_domain),
            # We do not have a mail server for this address email, so fall back to the "notifications@domain" email.
            (f'{self.default_from}@{self.alias_domain}', f'"Testing" <{self.default_from}@{self.alias_domain}>', self.mail_server_notification),
            # forced sever
            ('unknow_email@unknow_domain.com', 'unknow_email@unknow_domain.com', self.mail_server_notification),
        ]:
            self.assertSMTPEmailsSent(
                smtp_from=expected_smtp_from,
                message_from=expected_msg_from,
                mail_server=expected_mail_server,
                emails_count=8,
            )
