# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.base.tests.common import MockSmtplibCase
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import config, mute_logger


@tagged('mail_server')
class TestIrMailServerCommon(TransactionCase, MockSmtplibCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._init_mail_config()
        cls._init_mail_servers()

    @classmethod
    def _init_mail_config(cls):
        super()._init_mail_config()
        cls.alias_bounce = 'bounce.test'
        cls.alias_domain = 'test.mycompany.com'
        cls.default_from = 'notifications'
        cls.env['ir.config_parameter'].sudo().set_param('mail.catchall.domain', cls.alias_domain)
        cls.env['ir.config_parameter'].sudo().set_param('mail.default.from', cls.default_from)
        cls.env['ir.config_parameter'].sudo().set_param('mail.bounce.alias', cls.alias_bounce)


@tagged('mail_server')
class TestIrMailServer(TestIrMailServerCommon):

    @patch.dict(config.options, {"email_from": "settings@example.com"})
    def test_default_email_from(self):
        """Email from setting is respected."""
        # ICP setting is more important
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("mail.catchall.domain", "test.mycompany.com")
        ICP.set_param("mail.default.from", "icp")
        message = self.env["ir.mail_server"].build_email(
            False, "recipient@example.com", "Subject",
            "The body of an email",
        )
        self.assertEqual(message["From"], "icp@test.mycompany.com")

        # Without ICP, the config file/CLI setting is used
        ICP.set_param("mail.default.from", False)
        message = self.env["ir.mail_server"].build_email(
            False, "recipient@example.com", "Subject",
            "The body of an email",
        )
        self.assertEqual(message["From"], "settings@example.com")

    @mute_logger('odoo.models.unlink')
    def test_mail_server_send_email(self):
        IrMailServer = self.env['ir.mail_server']

        # Test that the mail from / recipient envelop are encoded using IDNA
        self.env['ir.config_parameter'].sudo().set_param('mail.catchall.domain', 'ééééééé.com')
        with self.mock_smtplib_connection():
            message = self._build_email(mail_from='test@ééééééé.com')
            IrMailServer.send_email(message)

        self.assertEqual(len(self.emails), 1)
        self.assert_email_sent_smtp(
            smtp_from='bounce.test@xn--9caaaaaaa.com',
            smtp_to_list=['dest@xn--example--i1a.com'],
            message_from='test@=?utf-8?b?w6nDqcOpw6nDqcOpw6k=?=.com',
            from_filter=False,
        )
