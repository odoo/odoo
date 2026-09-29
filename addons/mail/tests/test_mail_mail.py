import base64
from itertools import product
import re

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
        disconnected_smtpsession = mock.MagicMock()
        disconnected_smtpsession.quit.side_effect = smtplib.SMTPServerDisconnected
        mail = self.env["mail.mail"].create({})
        with mock.patch("odoo.addons.base.models.ir_mail_server.IrMailServer.connect", return_value=disconnected_smtpsession):
            with mock.patch("odoo.addons.mail.models.mail_mail._logger.info") as mock_logging_info:
                mail.send()
        disconnected_smtpsession.quit.assert_called_once()
        mock_logging_info.assert_any_call(
            "Ignoring SMTPServerDisconnected while trying to quit non open session"
        )
        # if we get here SMTPServerDisconnected was not raised
        self.assertEqual(mail.state, "exception")
        self.assertEqual(
            mail.failure_reason,
            "Error without exception. Probably due to sending "
            "an email without computed recipients."
        )

    def test_render_attachment_links_in_body(self):
        """Test attachment link rendering over various body formats and attachment counts."""
        # size of header ({}), overhead from _estimate_email_size, overhead from _render_attachment_links_in_body
        MailMail = self.env['mail.mail']
        default_overhead_size = 2 + 10 * 1024 + 5000
        no_attachments = self.env['ir.attachment']
        content = b'TEST'
        content_len = len(base64.b64encode(content))
        all_attachments = self.env['ir.attachment'].create(
            [{'name': name, 'raw': content}
             for name in ['test1.txt', 'test2.txt', 'outside.txt']])
        outside_attachment = all_attachments[2]
        outside_attachment.generate_access_token()
        for attachments, (body, expected_match) in product(
                (
                        no_attachments,
                        all_attachments[0],
                        all_attachments[:2],
                ),
                (
                        (False, r'.*<div class="o-attachments-container"'),
                        ('', r'.*<div class="o-attachments-container"'),
                        ('OUTSIDE only text', r'.*<div class="o-attachments-container".*only text'),
                        ('<html>OUTSIDE <p>broken html</p></htm>',
                         r'.*<html>.*<div class="o-attachments-container".*broken html'),
                        ('<root>OUTSIDE broken html</root>', r'.*<div class="o-attachments-container".*broken html'),
                        ('<html>OUTSIDE <p>fine html</p></html>',
                         r'.*<div class="o-attachments-container".*fine html</p>'),
                        ('<html><body><p>OUTSIDE correct html</p></body></html>', r'.*<div class="o-attachments-container".*correct html'),
                        ('<html><body>OUTSIDE Hello, <div class="o-signature-container">Signature</div></body></html>',
                         r'.*Hello,.*<div class="o-attachments-container".*o-signature-container'),
                        (('<html><body>OUTSIDE Hello <div class="o-attachments-container">can be replaced</div>..., '
                          '<div class="o-signature-container">Signature</div></body></html>'),
                         r'.*Hello.*<div class="o-attachments-container".*o-signature-container'),
                ),
        ):
            # Setup limit to be reach with the second attachment only
            self.env['ir.config_parameter'].sudo().set_param(
                'base.default_max_email_size',
                (default_overhead_size + (len(body) if body else 0) + content_len + 1) / 1024.0 / 1024.0)
            with self.subTest(test='without outside attachment', body=body, attachments=attachments):
                rendered = MailMail._render_attachment_links_in_body(body, attachments)
                self.assertEqual(rendered.count('o-attachments-container'),
                                 (body or '').count('o-attachments-container') + 1)
                self.assertTrue(re.match(expected_match, rendered, re.DOTALL))
                for idx, attachment in enumerate(attachments):
                    self.assertTrue(attachment.access_token, f'attachment {idx} must have a token')
                    self.assertIn(attachment.access_token, rendered, f'attachment {idx} must be present')
