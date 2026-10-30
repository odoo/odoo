from odoo.tests import TransactionCase, tagged
from unittest import mock
import smtplib


@tagged('mail_mail')
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

    def test_mail_send_no_recipients_notification(self):
        """Test that sending an email without recipients marks notifications as failed."""
        mail = self.env['mail.mail'].create({
            'body_html': '<p>Test</p>',
            'is_notification': True,
        })
        notif = self.env['mail.notification'].create({
            'failure_type': 'mail_email_missing',
            'mail_mail_id': mail.id,
            'mail_message_id': mail.mail_message_id.id,
            'notification_status': 'ready',
            'notification_type': 'email',
        })
        with mock.patch('odoo.addons.base.models.ir_mail_server.IrMail_Server._disable_send', return_value=False):
            mail.send()
        notif.flush_recordset()
        self.assertEqual(mail.state, 'exception')
        self.assertEqual(mail.failure_type, 'mail_email_missing')
        self.assertEqual(notif.notification_status, 'exception')
        self.assertEqual(notif.failure_type, 'mail_email_missing')
