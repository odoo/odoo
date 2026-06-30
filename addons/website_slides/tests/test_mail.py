from odoo.addons.website_slides.tests.common import SlidesCase


class TestSlidesMail(SlidesCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        common_vals = {
            'auto_delete': True,
            'body_html': '<p>Fist fight with <t t-out="object.user_id.name"/></p>',
            'email_from': '{{ object.user_id.email_formatted or user.email_formatted or "" }}',
            'subject': 'Test {{ object.name }}'
        }
        cls.user_manager.group_ids += cls.env.ref('mail.group_mail_template_editor')
        cls.test_template_slides = cls.env['mail.template'].with_user(cls.user_manager).create({
            **common_vals,
            'model_id': cls.env['ir.model']._get_id('slide.slide'),
            'name': 'Test Slide Template',
        })
        cls.test_template_channel = cls.env['mail.template'].with_user(cls.user_manager).create({
            **common_vals,
            'model_id': cls.env['ir.model']._get_id('slide.channel'),
            'name': 'Test Channel Template',
        })
        cls.slide.write({
            'partner_ids': [(6, 0, [cls.customer.id, cls.user_emp.partner_id.id, cls.user_portal.partner_id.id])],
        })
        cls.channel.write({
            'partner_ids': [(6, 0, [cls.customer.id, cls.user_emp.partner_id.id, cls.user_portal.partner_id.id])],
        })

    def test_slide_channel_get_default_recipients(self):
        channel = self.channel.with_user(self.user_manager)
        default_recipients = channel._message_get_default_recipients()
        self.assertDictEqual(default_recipients[channel.id], {'email_cc': '', 'email_to': '', 'partner_ids': []})

    def test_slide_slide_get_default_recipients(self):
        slide = self.slide.with_user(self.user_manager)
        default_recipients = slide._message_get_default_recipients()
        self.assertDictEqual(default_recipients[slide.id], {'email_cc': '', 'email_to': '', 'partner_ids': []})

    def test_slide_channel_get_suggested_recipients(self):
        channel = self.channel.with_user(self.user_manager)
        suggested_recipient = channel._message_get_suggested_recipients()[0]
        user_id = channel.user_id
        self.assertDictEqual(
            suggested_recipient,
            {
                'email': user_id.email, 'name': user_id.name,
                'partner_id': user_id.partner_id.id, 'create_values': {}
            }
        )

    def test_slide_slide_get_suggested_recipients(self):
        slide = self.slide.with_user(self.user_manager)
        suggested_recipient = slide._message_get_suggested_recipients()
        self.assertFalse(suggested_recipient, "The user_id is already subscribed => no suggested_recipients")

    def test_slide_and_channel_templates(self):
        values = [self.channel.with_user(self.user_manager), self.slide.with_user(self.user_manager)]
        templates = [
            self.test_template_channel.with_user(self.user_manager),
            self.test_template_slides.with_user(self.user_manager),
        ]
        expected_values = [values[0].user_id.partner_id, values[1].user_id.partner_id]
        error_messages = [
            "auto subscribe => only channel's user_id is notified",
            "auto subscribe => only slide's user_id is subscribed + notified",
        ]
        for channel_or_slide, template, expected_value, error_message in zip(values, templates, expected_values, error_messages):
            with self.subTest(channel_or_slide=channel_or_slide, template=template, expected_value=expected_value):
                message = channel_or_slide.message_post_with_source(
                    template,
                    message_type='comment',
                    subtype_id=self.env.ref('mail.mt_comment').id,
                )
                self.assertEqual(message.notified_partner_ids, expected_value, error_message)
