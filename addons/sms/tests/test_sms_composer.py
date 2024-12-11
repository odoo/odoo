# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.sms.models.mail_thread import MailThread
from odoo.addons.sms.tests.common import SMSCommon, SMSCase
from odoo.tests import tagged


@tagged('at_install')
class TestSMSComposerComment(SMSCommon, SMSCase):
    """ Test behaviors that are overridden when other modules
    are installed (e.g., mass_mailing). In these cases,
    test_mail_sms or test_mail_full should be used."""

    def test_message_post_sms_vs_notification(self):
        """Check that the conversion of html to plain text does remove links

        This is necessary when an SMS is sent from message_post with sms type
        and not from _message_sms. In this case, it can be expected to receive html
        that should be interpreted as such instead of escaped before being sent.
        """
        cases = [
            (
                'Hello there, check this awesome <b>app</b> I found:<br/>https://odoo.com',  # not a `a` link in source
                '<p>Hello there, check this awesome &lt;b&gt;app&lt;/b&gt; I found:&lt;br/&gt;<a href="https://odoo.com" target="_blank" rel="noreferrer noopener">https://odoo.com</a></p>',
                'Hello there, check this awesome <b>app</b> I found:<br/>https://odoo.com'
            ), (
                'Hello there, check this awesome <b>app</b> I found:<br/><a href="https://odoo.com">Here</a>',   # a link
                '<p>Hello there, check this awesome &lt;b&gt;app&lt;/b&gt; I found:&lt;br/&gt;&lt;a href="<a href="https://odoo.com" target="_blank" rel="noreferrer noopener">https://odoo.com</a>"&gt;Here&lt;/a&gt;</p>',
                'Hello there, check this awesome <b>app</b> I found:<br/><a href="https://odoo.com">Here</a>'  # keep all information
            )
        ]

        for message_content, expected_notification_content, expected_sms_content in cases:
            with self.subTest(message_content=message_content):
                with self.with_user('admin'), self.mockSMSGateway():
                    message = self.env.user.partner_id.message_post(
                        body=message_content, message_type='sms', sms_numbers=['+3215228817386'])

                self.assertSMSNotification(
                    [{'number': '+3215228817386'}], expected_sms_content, message,
                    mail_message_values={"body": expected_notification_content},
                )

    def test_message_sms_body_sms_vs_notification(self):
        """Check that the rendering of the sms notification is identical to the sms.

        The only expected difference is that links are converted to be clickable.
        The test verifies that MailThread._message_sms() works as expected."""
        # Cases are formatted as sms text, expected notification body
        cases = [
            (
                "Hello there, check this awesome app I found:\nhttps://odoo.com",
                '<p>Hello there, check this awesome app I found:<br>'
                '<a href="https://odoo.com" target="_blank" rel="noreferrer noopener">https://odoo.com</a></p>',
            ), (
                "Hello there, check this awesome <b>app</b> I found:\nhttps://odoo.com",
                # b is kept as is in notification, but link is still added as well
                '<p>Hello there, check this awesome &lt;b&gt;app&lt;/b&gt; I found:<br>'
                '<a href="https://odoo.com" target="_blank" rel="noreferrer noopener">https://odoo.com</a></p>',
            ),
            (
                # Here, we check that the sms sent is the sms written.
                "Hello there, check this awesome <b>app</b> I found:\n*https://odoo.com*",
                '<p>Hello there, check this awesome &lt;b&gt;app&lt;/b&gt; I found:<br>'
                '*<a href="https://odoo.com" target="_blank" rel="noreferrer noopener">https://odoo.com</a>*</p>',
            ),
        ]

        for sms_content, expected_notification_content in cases:
            with self.subTest(sms_content=sms_content):
                with self.with_user('admin'):
                    composer = self.env['sms.composer'].with_context(
                        active_model='res.partner', active_id=self.partner_employee).create({'body': sms_content})
                    _message_sms_patch = patch.object(
                        MailThread, '_message_sms', autospec=True, side_effect=MailThread._message_sms)
                    with self.mockSMSGateway(), _message_sms_patch as _patched_message_sms:
                        messages = composer._action_send_sms()
                        _patched_message_sms.assert_called()  # make sure we're testing `_message_sms` too
                self.assertSMSNotification(
                    [{'partner': self.partner_employee}], sms_content, messages,
                    mail_message_values={"body": expected_notification_content},
                )
