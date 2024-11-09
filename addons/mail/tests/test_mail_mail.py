from odoo.tests import TransactionCase
from unittest import mock
import smtplib


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
        not_connected = smtplib.SMTP(local_hostname="fake-hostname.com", port=9999, timeout=1)
        mail = self.env["mail.mail"].create({})
        with mock.patch("odoo.addons.base.models.ir_mail_server.IrMailServer.connect", return_value=not_connected):
            mail.send()
        # if we get here SMTPServerDisconnected was not raised
        self.assertEqual(mail.state, "exception")
        self.assertEqual(
            mail.failure_reason,
            "Error without exception. Probably due to sending "
            "an email without computed recipients."
        )
