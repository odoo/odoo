from odoo.tests import tagged, TransactionCase
from unittest import mock
import smtplib


@tagged('at_install', '-post_install')  # LEGACY at_install
class MailCase(TransactionCase):

    def test_mail_send_non_connected_smtp_session(self):
        """Check to avoid SMTPServerDisconnected error while trying to
        disconnect smtp session that is not connected.

        This used to happens while trying to connect to a
        google smtp server with an expired token.

        Or here testing non recipients emails with non connected
        smtp session, we won't get SMTPServerDisconnected that would
        hide the other error that is raised earlier.
        """
        disconnected_smtpsession = mock.MagicMock()
        disconnected_smtpsession.quit.side_effect = smtplib.SMTPServerDisconnected
        mail = self.env["mail.mail"].create({})
        with mock.patch("odoo.addons.base.models.ir_mail_server.IrMail_Server._connect__", return_value=disconnected_smtpsession):
            with mock.patch("odoo.addons.mail.models.mail_mail._logger.info") as mock_logging_info:
                mail.send()
        disconnected_smtpsession.quit.assert_called_once()
        mock_logging_info.assert_any_call(
            "Ignoring SMTPServerDisconnected while trying to quit non open session"
        )
        # if we get here SMTPServerDisconnected was not raised
        self.assertEqual(mail.state, "outgoing")

    def test_mail_mail_read_all(self):
        """E-mail created by root has message which is not visible to admin.
        Yet, the admin must be able to see it.
        """
        mail = self.env["mail.mail"].create({})
        mail = mail.with_user(self.ref('base.user_admin'))
        self.assertTrue(mail.has_access('read'))
        msg = mail.mail_message_id
        self.assertFalse(msg.has_access('read'))
        mail.invalidate_model()

        # should be able to read the following items
        for field_name in ('message_type', 'body'):
            with self.subTest(field=field_name):
                msg.invalidate_model()
                mail[field_name]
