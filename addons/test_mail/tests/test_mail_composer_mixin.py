# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests.common import TestMailCommon, TestRecipients
from odoo.tests import tagged
from odoo.tests.common import users


@tagged('mail_composer_mixin')
class TestMailComposerMixin(TestMailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestMailComposerMixin, cls).setUpClass()

        cls.mail_template = cls.env['mail.template'].create({
            'subject': 'Subject for {{ object.name }}',
            'body_html': '<p>Body for <t t-out="object.name"/></p>',
        })

    @users("employee")
    def test_content_sync(self):
        record = self.env['mail.test.composer.mixin'].create({
            'name': 'Invite',
            'template_id': self.mail_template.id,
        })
        self.assertEqual(record.subject, self.mail_template.subject)
        self.assertEqual(record.body, self.mail_template.body_html)

        subject = record._render_field('subject', record.ids)[record.id]
        self.assertEqual(subject, 'Subject for %s' % record.name)
        body = record._render_field('body', record.ids)[record.id]
        self.assertEqual(body, '<p>Body for %s</p>' % record.name)

    @users("employee")
    def test_rendering(self):
        record = self.env['mail.test.composer.mixin'].create({
            'name': 'Invite',
            'subject': 'Subject for {{ object.name }}',
            'body': '<p>Content from <t t-out="user.name"/></p>',
            'description': '<p>Description for <t t-esc="object.name"/></p>',
        })
        self.assertEqual(record.subject, 'Subject for {{ object.name }}')
        self.assertEqual(record.body, '<p>Content from <t t-out="user.name"/></p>')

        subject = record._render_field('subject', record.ids)[record.id]
        self.assertEqual(subject, 'Subject for %s' % record.name)
        body = record._render_field('body', record.ids)[record.id]
        self.assertEqual(body, '<p>Content from %s</p>' % self.env.user.name)
        description = record._render_field('description', record.ids)[record.id]
        self.assertEqual(description, '<p>Description for Invite</p>')
