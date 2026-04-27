# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time
from datetime import datetime, timedelta
from freezegun import freeze_time
from markupsafe import Markup
from odoo.addons.whatsapp.tests.common import WhatsAppCommon, MockIncomingWhatsApp
from odoo.tests import tagged, users


@tagged('wa_message')
class DiscussChannel(WhatsAppCommon, MockIncomingWhatsApp):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_channel_wa, cls.test_channel_wa2, cls.test_channel_std = cls.env['discuss.channel'].create([
            {
                'channel_partner_ids': [(4, cls.user_wa_admin.partner_id.id)],
                'channel_type': 'whatsapp',
                'name': 'Dummy WA Channel',
                'wa_account_id': cls.whatsapp_account.id,
                'whatsapp_number': '911234567891',
                'whatsapp_partner_id': cls.whatsapp_customer.id,
            }, {
                'channel_partner_ids': [(4, cls.user_wa_admin.partner_id.id)],
                'channel_type': 'whatsapp',
                'name': 'Dummy WA Channel 2',
                'wa_account_id': cls.whatsapp_account.id,
                'whatsapp_number': '911234567891',
                'whatsapp_partner_id': cls.whatsapp_customer.id,
            }, {
                'channel_partner_ids': [(4, cls.user_wa_admin.partner_id.id)],
                'channel_type': 'channel',
                'name': 'Dummy Test Channel',
            }
        ])

    def test_gc_whatsapp_inactive(self):
        for test_record, delay_days, mark_read in ((self.test_channel_wa, 2, True), (self.test_channel_wa2, 6, False)):  # 2 days - 6 days
            with self.subTest(test_record=test_record):
                test_record.channel_pin(pinned=True)
                member_of_operator = self.env["discuss.channel.member"].search(
                    [
                        ("channel_id", "=", test_record.id),
                        ("partner_id", "=", self.user_wa_admin.partner_id.id),
                    ]
                )
                message = test_record.message_post(
                    author_id=self.whatsapp_customer.id,
                    body='TestBody',
                    message_type='whatsapp_message',
                    subtype_xmlid='mail.mt_comment',
                )
                if mark_read:
                    member_of_operator._mark_as_read(message.id)
                self.assertTrue(member_of_operator.is_pinned)
                with freeze_time(datetime.now() + timedelta(days=delay_days)):
                    member_of_operator._gc_unpin_whatsapp_channels()
                self.assertFalse(member_of_operator.is_pinned)

    def test_post_with_audio_attachment(self):
        message_vals_all = (
            {'body': '', 'attachment_ids': self.audio_attachment_wa_admin.ids},
            {'body': 'TestBody', 'attachment_ids': self.audio_attachment_wa_admin.ids},
            {'body': 'TestBody', 'attachment_ids': (self.image_attachment_wa_admin + self.audio_attachment_wa_admin).ids},
        )
        for message_vals in message_vals_all:
            expected_body = message_vals['body']
            expect_audio_attachment = self.audio_attachment_wa_admin.id in message_vals['attachment_ids']
            expect_image_attachment = self.image_attachment_wa_admin.id in message_vals['attachment_ids']
            with self.subTest(
                body=expected_body, image_attachment=expect_image_attachment, audio_attachment=expect_audio_attachment
            ):
                with self.mockWhatsappGateway(), self.mock_mail_app():
                    return_message = self.test_channel_wa.message_post(
                        author_id=self.test_channel_wa.whatsapp_partner_id.id,
                        message_type='whatsapp_message',
                        subtype_xmlid='mail.mt_comment',
                        **message_vals,
                    )
                    self.assertEqual(len(return_message), 1, "We expect one returned message when posting.")
                    if expected_body:
                        self.assertIn(
                            expected_body, return_message.body,
                            "Should return the message containing the body if two are created."
                        )
                messages = self._new_msgs

                expected_message_count = bool(message_vals['body']) + bool(expect_audio_attachment)

                self.assertEqual(len(messages), expected_message_count)
                self.assertEqual(len(self._wa_msg_sent), expected_message_count)
                self.assertEqual(messages.wa_message_ids.mapped('msg_uid'), self._wa_msg_sent)

                if expected_body:
                    body_message = messages[0]
                    self.assertIn(expected_body, body_message.body)
                    if expect_image_attachment:
                        self.assertEqual(len(body_message.attachment_ids), 1)
                        self.assertEqual(body_message.attachment_ids.mimetype, 'image/jpeg')
                if expect_audio_attachment:
                    audio_message = messages[expected_message_count - 1]
                    self.assertEqual(len(audio_message.attachment_ids), 1)
                    self.assertEqual(audio_message.attachment_ids.mimetype, 'audio/mpeg')

    @users('user_wa_admin')
    def test_post_with_outbound(self):
        """ Test automatic whatsapp message creation when posting on a whatsapp
        channel: should create an outbound wa message """
        test_channel_wa = self.test_channel_wa.with_env(self.env)
        with self.mockWhatsappGateway():
            new_msg = test_channel_wa.message_post(
                author_id=test_channel_wa.whatsapp_partner_id.id,
                body=Markup('<p>Line 1<br>Line 2</p>'),
                message_type='whatsapp_message',
                subtype_xmlid='mail.mt_comment',
            )
        wa_message = new_msg.wa_message_ids
        self.assertEqual(self._wa_msg_sent_vals[0]['body'], "Line 1\nLine 2", "Mismatch body in `send_vals`")
        self.assertEqual(len(wa_message), 1)
        self.assertEqual(wa_message.message_type, 'outbound')
        self.assertEqual(wa_message.mobile_number, f'+{test_channel_wa.whatsapp_number}')
        self.assertTrue(wa_message.msg_uid)
        self.assertEqual(wa_message.state, 'sent')
        self.assertEqual(wa_message.wa_account_id, self.test_channel_wa.wa_account_id)

        # should not be supported on other channels / models
        for test_record in (self.whatsapp_customer, self.test_channel_std):
            with self.subTest(test_record=test_record), self.mockWhatsappGateway():
                new_msg = test_record.message_post(
                    author_id=test_channel_wa.whatsapp_partner_id.id,
                    body='TestBody',
                    message_type='whatsapp_message',
                    subtype_xmlid='mail.mt_comment',
                )
                self.assertFalse(new_msg.wa_message_ids)

    @users('user_wa_admin')
    def test_post_with_url_body_cleanup_for_duplicated_urls(self):
        """ Test that the we won't send the same URL twice in the body of a message to whatsapp."""
        test_channel = self.test_channel_wa.with_env(self.env)

        input_body = Markup('<p>I love <a href="https://shin.com">https://shin.com</a> and <a href="https://chan.com">https://chan.com</a></p>')
        expected_body = "I love https://shin.com and https://chan.com"

        with self.mockWhatsappGateway():
            test_channel.message_post(
                author_id=self.user_wa_admin.partner_id.id,
                body=input_body,
                message_type='whatsapp_message',
                subtype_xmlid='mail.mt_comment',
            )

        self.assertEqual(len(self._wa_msg_sent_vals), 1, "One message should have been sent.")
        sent_body = self._wa_msg_sent_vals[0].get('body')
        self.assertEqual(sent_body, expected_body, "The body should not contain duplicated urls.")

    @users('user_wa_admin')
    def test_post_with_whatsapp_inbound_msg_uid(self):
        """ Test automatic whatsapp message creation when posting from whatsapp
        specific controller """
        test_channel_wa = self.test_channel_wa.with_env(self.env)
        new_msg = test_channel_wa.message_post(
            author_id=test_channel_wa.whatsapp_partner_id.id,
            body='TestBody',
            message_type='whatsapp_message',
            subtype_xmlid='mail.mt_comment',
            whatsapp_inbound_msg_uid='msg.uid.123456789',
        )
        wa_message = new_msg.wa_message_ids
        self.assertEqual(len(wa_message), 1)
        self.assertEqual(wa_message.message_type, 'inbound')
        self.assertEqual(wa_message.mobile_number, f'+{test_channel_wa.whatsapp_number}')
        self.assertEqual(wa_message.msg_uid, 'msg.uid.123456789')
        self.assertEqual(wa_message.state, 'received')
        self.assertEqual(wa_message.wa_account_id, self.test_channel_wa.wa_account_id)

        # should not be supported on other channels / models
        for test_record in (self.whatsapp_customer, self.test_channel_std):
            with self.subTest(test_record=test_record):
                with self.assertRaises(ValueError):
                    test_record.message_post(
                        author_id=test_channel_wa.whatsapp_partner_id.id,
                        body='TestBody',
                        message_type='whatsapp_message',
                        subtype_xmlid='mail.mt_comment',
                        whatsapp_inbound_msg_uid='msg.uid.123456789',
                    )

    def test_parent_msg_reciever(self):
        template = self.env['whatsapp.template'].create({
            'body': 'Hello World',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'name': 'Test-basic',
            'status': 'approved',
            'wa_account_id': self.whatsapp_account.id,
        })
        test_partner = self.env['res.partner'].create({
            'country_id': self.env.ref('base.be').id,
            'mobile': '+32455001122',
            'name': 'Test Partner',
        })
        composer = self._instanciate_wa_composer_from_records(template, from_records=test_partner)
        with self.mockWhatsappGateway():
            msg = composer.action_send_whatsapp_template()

        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(
                self.whatsapp_account,
                "Hello, it's reply",
                test_partner.mobile,
                additional_message_values={
                    'context': {'id': msg.msg_uid},
                },
            )
        self.assertEqual(self._new_wa_msg.mail_message_id.parent_id, msg.mail_message_id)
