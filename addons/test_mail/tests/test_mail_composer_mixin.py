# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mail.tests.common import TestRecipients
from odoo.tests import tagged
from odoo.tests.common import users


@tagged('mail_composer_mixin')
class TestMailComposerMixin(MailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestMailComposerMixin, cls).setUpClass()

        # ensure employee can create partners, necessary for templates
        cls.user_employee.write({
            'groups_id': [(4, cls.env.ref('base.group_partner_manager').id)],
        })

        cls.mail_template = cls.env['mail.template'].create({
            'body_html': '<p>EnglishBody for <t t-out="object.name"/></p>',
            'model_id': cls.env['ir.model']._get('mail.test.composer.source').id,
            'name': 'Test Template for mail.test.composer.source',
            'lang': '{{ object.customer_id.lang }}',
            'subject': 'EnglishSubject for {{ object.name }}',
        })
        cls.test_record = cls.env['mail.test.composer.source'].create({
            'name': cls.partner_1.name,
            'customer_id': cls.partner_1.id,
        })

        cls._activate_multi_lang(
            layout_arch_db='<body><t t-out="message.body"/> English Layout for <t t-esc="model_description"/></body>',
            lang_code='es_ES',
            test_record=cls.test_record,
            test_template=cls.mail_template,
        )

    @users("employee")
    def test_content_sync(self):
        """ Test updating template updates the dynamic fields accordingly. """
        source = self.test_record.with_env(self.env)
        template = self.mail_template.with_env(self.env)
        template_void = template.copy()
        template_void.write({
            'body_html': '<p><br /></p>',
            'lang': False,
            'subject': False,
        })

        composer = self.env['mail.test.composer.mixin'].create({
            'name': 'Invite',
            'template_id': template.id,
            'source_ids': [(4, source.id)],
        })
        self.assertEqual(composer.body, template.body_html)
        self.assertTrue(composer.body_has_template_value)
        self.assertEqual(composer.lang, template.lang)
        self.assertEqual(composer.subject, template.subject)

        # check rendering
        body = composer._render_field('body', source.ids)[source.id]
        self.assertEqual(body, f'<p>EnglishBody for {source.name}</p>')
        subject = composer._render_field('subject', source.ids)[source.id]
        self.assertEqual(subject, f'EnglishSubject for {source.name}')

        # manual values > template default values
        composer.write({
            'body': '<p>CustomBody for <t t-out="object.name"/></p>',
            'subject': 'CustomSubject for {{ object.name }}',
        })
        self.assertFalse(composer.body_has_template_value)

        body = composer._render_field('body', source.ids)[source.id]
        self.assertEqual(body, f'<p>CustomBody for {source.name}</p>')
        subject = composer._render_field('subject', source.ids)[source.id]
        self.assertEqual(subject, f'CustomSubject for {source.name}')

        # template with void values: should not force void (TODO)
        composer.template_id = template_void.id
        self.assertEqual(composer.body, '<p>CustomBody for <t t-out="object.name"/></p>')
        self.assertFalse(composer.body_has_template_value)
        self.assertEqual(composer.lang, template.lang)
        self.assertEqual(composer.subject, 'CustomSubject for {{ object.name }}')

        # reset template TOOD should reset
        composer.write({'template_id': False})
        self.assertFalse(composer.body)
        self.assertFalse(composer.body_has_template_value)
        self.assertFalse(composer.lang)
        self.assertFalse(composer.subject)

    @users("employee")
    def test_rendering_custom(self):
        """ Test rendering with custom strings (not coming from template) """
        source = self.test_record.with_env(self.env)
        composer = self.env['mail.test.composer.mixin'].create({
            'description': '<p>Description for <t t-esc="object.name"/></p>',
            'body': '<p>SpecificBody from <t t-out="user.name"/></p>',
            'name': 'Invite',
            'subject': 'SpecificSubject for {{ object.name }}',
        })
        self.assertEqual(composer.body, '<p>SpecificBody from <t t-out="user.name"/></p>')
        self.assertEqual(composer.subject, 'SpecificSubject for {{ object.name }}')

        subject = composer._render_field('subject', source.ids)[source.id]
        self.assertEqual(subject, f'SpecificSubject for {source.name}')
        body = composer._render_field('body', source.ids)[source.id]
        self.assertEqual(body, f'<p>SpecificBody from {self.env.user.name}</p>')
        description = composer._render_field('description', source.ids)[source.id]
        self.assertEqual(description, f'<p>Description for {source.name}</p>')

    @users("employee")
    def test_rendering_lang(self):
        """ Test rendering with language involved """
        template = self.mail_template.with_env(self.env)
        customer = self.partner_1.with_env(self.env)
        customer.lang = 'es_ES'
        source = self.test_record.with_env(self.env)
        composer = self.env['mail.test.composer.mixin'].create({
            'description': '<p>Description for <t t-esc="object.name"/></p>',
            'name': 'Invite',
            'template_id': self.mail_template.id,
            'source_ids': [(4, source.id)],
        })
        self.assertEqual(composer.body, template.body_html)
        self.assertEqual(composer.subject, template.subject)
        self.assertEqual(composer.lang, '{{ object.customer_id.lang }}')

        # do not specifically ask for language computation
        subject = composer._render_field('subject', source.ids, compute_lang=False)[source.id]
        self.assertEqual(subject, f'EnglishSubject for {source.name}')
        body = composer._render_field('body', source.ids, compute_lang=False)[source.id]
        self.assertEqual(body, f'<p>EnglishBody for {source.name}</p>')
        description = composer._render_field('description', source.ids)[source.id]
        self.assertEqual(description, f'<p>Description for {source.name}</p>')

        # ask for dynamic language computation
        subject = composer._render_field('subject', source.ids, compute_lang=True)[source.id]
        self.assertEqual(subject, f'SpanishSubject for {source.name}',
                         'Translation comes from the template, as both values equal')
        body = composer._render_field('body', source.ids, compute_lang=True)[source.id]
        self.assertEqual(body, f'<p>SpanishBody for {source.name}</p>',
                         'Translation comes from the template, as both values equal')
        description = composer._render_field('description', source.ids)[source.id]
        self.assertEqual(description, f'<p>Description for {source.name}</p>')
