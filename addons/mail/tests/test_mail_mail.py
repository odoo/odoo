from odoo.tests import TransactionCase, tagged
from odoo.addons.mail.tests.common import MockSmtplibCase
from unittest import mock
import smtplib


@tagged('mail_mail')
class MailCase(TransactionCase, MockSmtplibCase):

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

    def test_batch_send_through_cron(self):
        """
        Test the detection of the cron when processesing "Mail: Email Queue Manager"
        'code' : 'model.process_email_queue()'. With the change from _notify_progress
        to _commit_progress we need to properly detect the cron model for batch processing
        """
        post_data = [{
            "body": "Hello Peter",
            "email_add_signature": False,
            "message_type": "comment",
            "email_to": ["peter.parker@marvel.com"],

        }] * 50
        messages = self.env["mail.mail"].create(post_data)
        self.assertEqual(len(messages.filtered_domain([["state", "=", "outgoing"]])), 50)

        mail_cron = self.env.ref('mail.ir_cron_mail_scheduler_action')
        mail_cron.write({"code": "model.process_email_queue(batch_size=5)"})  # changing the batch size from default 1000 to 5

        # Establish a mock smtp connection and enter the test mode for registry
        # for crons otherwise it wont commit
        with self.mock_smtplib_connection(), self.enter_registry_test_mode():
            mail_cron.method_direct_trigger()

        messages = self.env["mail.mail"].browse(messages.ids)
        self.assertEqual(len(messages.filtered_domain([["state", "=", "outgoing"]])), 0)
        self.assertEqual(len(messages.filtered_domain([["state", "=", "sent"]])), 50)
