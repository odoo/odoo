# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from datetime import timedelta

from odoo.addons.sms.models.mail_thread import MailThread
from odoo.addons.sms.tests.common import SMSCommon, SMSCase
from odoo.fields import Datetime
from odoo.tests import tagged


@tagged('at_install', '-post_install')
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

    def test_sms_composer_schedule_action(self):
        """ Test that simulates the correct working of the 'Schedule' button in the wizard """

        test_partner = self.env['res.partner'].create({
            'name': 'Test User',
            'phone': '+393331234567',
        })

        future_date = Datetime.now() + timedelta(days=1)

        composer = self.env['sms.composer'].with_context(
            active_model='res.partner',
            active_id=test_partner.id,
        ).create({
            'body': 'Scheduled Message',
            'composition_mode': 'comment',
            'scheduled_date': future_date,
        })

        composer.action_schedule_message()

        scheduled_msg = self.env['mail.scheduled.message'].search([
            ('model', '=', 'res.partner'),
            ('res_id', '=', test_partner.id),
        ], limit=1)

        self.assertTrue(scheduled_msg, "The wizard should have created a 'mail.scheduled.message' record.")

        with self.mockSMSGateway():
            scheduled_msg._post_message()

        sms = self.env['sms.sms'].search([
            ('body', '=', 'Scheduled Message')
        ], limit=1)

        self.assertTrue(sms, "The SMS should be created after the scheduled message is processed")
        self.assertEqual(sms.number, '+393331234567')

        self.assertIn(sms.state, ['pending', 'outgoing'])

    def test_sms_composer_action_create_template(self):
        """ Test to save new SMS template """
        composer = self.env['sms.composer'].with_context(
            active_model='res.partner',
            active_id=self.partner_employee.id
        ).create({
            'body': 'SMS Template new body',
            'template_name': 'Test SMS Template',
        })

        composer.action_create_sms_template()

        template = self.env['sms.template'].search([('name', '=', 'Test SMS Template')], limit=1)
        self.assertTrue(template, 'New SMS Template must be created')
        self.assertEqual(template.body, 'SMS Template new body')
        self.assertEqual(template.model_id.model, 'res.partner')

    def test_sms_composer_schedule_html_conversion_and_url_references(self):
        test_partner = self.env['res.partner'].create({
            'name': 'John Smith',
            'phone': '+323339876543',
        })

        sms_plaintext_body = "See our promo here:\nhttps://odoo.com\nEnjoy!"
        future_date = Datetime.now() + timedelta(days=2)

        composer = self.env['sms.composer'].with_context(
            active_model='res.partner',
            active_id=test_partner.id,
        ).create({
            'body': sms_plaintext_body,
            'composition_mode': 'comment',
            'scheduled_date': future_date,
        })

        composer.action_schedule_message()

        scheduled_msg = self.env['mail.scheduled.message'].search([
            ('model', '=', 'res.partner'),
            ('res_id', '=', test_partner.id),
        ], limit=1)

        self.assertTrue(scheduled_msg, "The scheduled message should have been created.")
        self.assertIn('<br>', scheduled_msg.body, "Line breaks should be converted into HTML <br> tags.")
        self.assertIn('<p>', scheduled_msg.body, "The body should be encapsulated inside HTML paragraph tags.")
        self.assertIn('<a href="https://odoo.com"', scheduled_msg.body, "The URL should be encapsulated inside an HTML anchor tag.")

        with self.mockSMSGateway():
            scheduled_msg._post_message()

        sms_final = self.env['sms.sms'].search([
            ('number', '=', '+323339876543')
        ], limit=1)

        self.assertTrue(sms_final, "The final SMS should have been generated from the scheduled message.")
        self.assertEqual(
            sms_final.body, 
            sms_plaintext_body, 
            "The final SMS body does not match the original plaintext or contains duplicated URLs."
        )
