import base64
from itertools import product

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

    def check_render_attachment_links_in_body(self, body, attachments_to_render, check_attachments, expected_in):
        """Check the default and forced rendering of the attachment links.

        :param str body : The raw body that will be processed.
        :param recordset attachments_to_render: The attachments that will be processed.
        :param recordset check_attachments: Attachments that are expected to appear in the rendered output.
        :param str expected_in: A snippet that must be present in the rendered output.
        """
        MailMail = self.env['mail.mail']
        rendered = MailMail._render_attachment_links_in_body(body, attachments_to_render)
        if len(check_attachments) > 1:
            self.assertEqual(
                rendered.count('o-attachments-container'), 1,
                "With 2 attachments, the limit is reached and the attachments links must be added")
            for idx, attachment in enumerate(check_attachments):
                self.assertTrue(attachment.access_token, f'attachment {idx} must have a token')
                self.assertIn(attachment.access_token, rendered, f'attachment {idx} must be present')
        else:
            # The limit is not reached, the attachment links must not be added
            if 'o-attachments-container' in (body or ''):
                # If the container was present, it is removed
                self.assertEqual(rendered.count('o-attachments-container'), 0)
            else:
                self.assertFalse(rendered)

        # Check that forcing the rendering always render all attachments
        rendered_force = MailMail._render_attachment_links_in_body(body, attachments_to_render, force=True)
        self.assertEqual(rendered_force.count('o-attachments-container'), 1)
        self.assertIn(expected_in, rendered_force)
        for idx, attachment in enumerate(check_attachments):
            self.assertTrue(attachment.access_token, f'attachment {idx} must have a token')
            self.assertIn(attachment.access_token, rendered_force, f'attachment {idx} must be present')

        # Check appending
        rendered_force = MailMail._render_attachment_links_in_body(
            body, attachments_to_render, force=True, append=True)
        self.assertEqual(rendered_force.count('o-attachments-container'),
                         1 + (body or '').count('o-attachments-container'))
        self.assertIn(expected_in, rendered_force)
        for idx, attachment in enumerate(check_attachments):
            self.assertTrue(attachment.access_token, f'attachment {idx} must have a token')
            self.assertIn(attachment.access_token, rendered_force, f'attachment {idx} must be present')

    def test_render_attachment_links_in_body(self):
        """Test attachment link rendering over various body formats and attachment counts."""
        # size of header ({}), overhead from _estimate_email_size, overhead from _render_attachment_links_in_body
        default_overhead_size = 2 + 10 * 1024 + 5000
        no_attachments = self.env['ir.attachment']
        content = b'TEST'
        content_len = len(base64.b64encode(content))
        all_attachments = self.env['ir.attachment'].create(
            [{'name': name, 'raw': content}
             for name in ['test1.txt', 'test2.txt', 'outside.txt']])
        outside_attachment = all_attachments[2]
        outside_attachment.generate_access_token()
        for attachments, (body, expected_in) in product(
                (
                        no_attachments,
                        all_attachments[0],
                        all_attachments[:2],
                ),
                (
                        (False, '<div class="o-attachments-container"'),
                        ('', '<div class="o-attachments-container"'),
                        ('OUTSIDE only text', 'only text<div class="o-attachments-container"'),
                        ('<html>OUTSIDE <p>broken html</p></htm>', 'broken html</p><div class="o-attachments-container"'),
                        ('<root>OUTSIDE broken html</root>', 'broken html<div class="o-attachments-container"'),
                        ('<html>OUTSIDE <p>fine html</p></html>', 'fine html</p><div class="o-attachments-container"'),
                        ('<html><body>OUTSIDE correct html</body></html>', 'correct html<div class="o-attachments-container"'),
                        ('<html><body>OUTSIDE Hello, <div class="o-signature-container">Signature</div></body></html>',
                         'Hello, <div class="o-attachments-container"'),
                        (('<html><body>OUTSIDE Hello <div class="o-attachments-container">can be replaced</div>..., '
                          '<div class="o-signature-container">Signature</div></body></html>'),
                         'Hello <div class="o-attachments-container"'),
                ),
        ):
            # Setup limit to be reach with the second attachment only
            self.env['ir.config_parameter'].sudo().set_param(
                'base.default_max_email_size',
                (default_overhead_size + (len(body) if body else 0) + content_len + 1) / 1024.0 / 1024.0)
            with self.subTest(test='without outside attachment', body=body, attachments=attachments):
                self.check_render_attachment_links_in_body(
                    body, attachments, check_attachments=attachments, expected_in=expected_in)

            if body:
                attachments_outside = attachments | outside_attachment
                self.assertEqual(len(attachments_outside), len(attachments) + 1)
                body_outside = body.replace(
                    'OUTSIDE', (f'<a data-attachment-id="{outside_attachment.id}" '
                                f'href="http://localhost:8069/web/content/{outside_attachment.id}?download=1'
                                f'&amp;access_token={outside_attachment.access_token}">outside.txt</a>'))
                self.env['ir.config_parameter'].sudo().set_param(
                    'base.default_max_email_size',
                    (default_overhead_size + (len(body_outside) if body else 0) + content_len + 1) / 1024.0 / 1024.0)
                self.assertIn(outside_attachment.access_token, body_outside)
                with self.subTest(test='with outside attachment', body=body_outside, attachments=attachments_outside):
                    self.check_render_attachment_links_in_body(
                        body_outside, attachments_outside, check_attachments=attachments, expected_in=expected_in)
