# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.tests.common import TestMailCommon, TestRecipients
from odoo.tests import tagged
from odoo.tests.common import users, Form
from odoo.tools import mute_logger

@tagged('mail_composer')
class TestMailComposer(TestMailCommon, TestRecipients):
    """ Test Composer internals """

    @classmethod
    def setUpClass(cls):
        super(TestMailComposer, cls).setUpClass()
        cls._init_mail_gateway()

        cls.user_employee_2 = mail_new_test_user(
            cls.env, login='employee2', groups='base.group_user',
            notification_type='inbox', email='eglantine@example.com',
            name='Eglantine Employee', signature='--\nEglantine')
        cls.partner_employee_2 = cls.user_employee_2.partner_id

        cls.test_record = cls.env['mail.test.ticket'].with_context(cls._test_context).create({
            'name': 'TestRecord',
            'customer_id': cls.partner_1.id,
            'user_id': cls.user_employee_2.id,
        })
        cls.test_records, cls.test_partners = cls._create_records_for_batch('mail.test.ticket', 2)

        cls.test_report = cls.env['ir.actions.report'].create({
            'name': 'Test Report on mail test ticket',
            'model': 'mail.test.ticket',
            'report_type': 'qweb-pdf',
            'report_name': 'test_mail.mail_test_ticket_test_template',
        })

        cls.test_from = '"John Doe" <john@example.com>'

        cls.mail_server = cls.env['ir.mail_server'].create({
            'name': 'Dummy Test Server',
            'smtp_host': 'smtp.pizza.moc',
            'smtp_port': 17,
            'smtp_encryption': 'ssl',
            'sequence': 666,
        })

        cls.template = cls.env['mail.template'].create({
            'name': 'TestTemplate',
            'subject': 'TemplateSubject ${object.name}',
            'body_html': '<p>TemplateBody ${object.name}</p>',
            'partner_to': '${object.customer_id.id if object.customer_id else ""}',
            'email_to': '${(object.email_from if not object.customer_id else "") | safe}',
            'email_from': '${object.user_id.email_formatted | safe}',
            'model_id': cls.env['ir.model']._get('mail.test.ticket').id,
            'mail_server_id': cls.mail_server.id,
        })

    def _generate_attachments_data(self, count):
        return [{
            'name': '%02d.txt' % x,
            'datas': base64.b64encode(b'Att%02d' % x),
        } for x in range(count)]

    def _get_web_context(self, records, add_web=True, **values):
        """ Helper to generate composer context. Will make tests a bit less
        verbose.

        :param add_web: add web context, generally making noise especially in
          mass mail mode (active_id/ids both present in context)
        """
        base_context = {
            'default_model': records._name,
        }
        if len(records) == 1:
            base_context['default_composition_mode'] = 'comment'
            base_context['default_res_id'] = records.id
        else:
            base_context['default_composition_mode'] = 'mass_mail'
            base_context['active_ids'] = records.ids
        if add_web:
            base_context['active_model'] = records._name
            base_context['active_id'] = records[0].id
        if values:
            base_context.update(**values)
        return base_context


@tagged('mail_composer')
class TestComposerForm(TestMailComposer):

    @users('employee')
    def test_mail_composer_comment(self):
        composer_form = Form(self.env['mail.compose.message'].with_context(self._get_web_context(self.test_record, add_web=True)))
        self.assertEqual(
            composer_form.subject, 'Re: %s' % self.test_record.name,
            'MailComposer: comment mode should have default subject Re: record_name')
        # record name not displayed currently in view
        # self.assertEqual(composer_form.record_name, self.test_record.name, 'MailComposer: comment mode should compute record name')
        self.assertFalse(composer_form.no_auto_thread)
        self.assertEqual(composer_form.composition_mode, 'comment')
        self.assertEqual(composer_form.model, self.test_records._name)

    @users('employee')
    def test_mail_composer_mass(self):
        composer_form = Form(self.env['mail.compose.message'].with_context(self._get_web_context(self.test_records, add_web=True)))
        self.assertFalse(composer_form.subject, 'MailComposer: mass mode should have void default subject if no template')
        # record name not displayed currently in view
        # self.assertFalse(composer_form.record_name, 'MailComposer: mass mode should have void record name')
        self.assertFalse(composer_form.no_auto_thread)
        self.assertEqual(composer_form.composition_mode, 'mass_mail')
        self.assertEqual(composer_form.model, self.test_records._name)

    @users('employee')
    def test_mail_composer_mass_wtpl(self):
        ctx = self._get_web_context(self.test_records, add_web=True, default_template_id=self.template.id)
        composer_form = Form(self.env['mail.compose.message'].with_context(ctx))
        self.assertEqual(composer_form.subject, self.template.subject,
                         'MailComposer: mass mode should have template raw subject if template')
        self.assertEqual(composer_form.body, self.template.body_html,
                         'MailComposer: mass mode should have template raw body if template')
        # record name not displayed currently in view
        # self.assertFalse(composer_form.record_name, 'MailComposer: mass mode should have void record name')
        self.assertFalse(composer_form.no_auto_thread)
        self.assertEqual(composer_form.composition_mode, 'mass_mail')
        self.assertEqual(composer_form.model, self.test_records._name)


@tagged('mail_composer')
class TestComposerInternals(TestMailComposer):

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_composer_attachments_comment(self):
        """ Test attachments management in comment mode. """
        attachment_data = self._generate_attachments_data(3)
        self.template.write({
            'attachment_ids': [(0, 0, a) for a in attachment_data],
            'report_template': self.test_report.id,
        })
        attachs = self.env['ir.attachment'].search([('name', 'in', [a['name'] for a in attachment_data])])
        self.assertEqual(len(attachs), 3)

        composer = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_model': self.test_record._name,
            'default_res_id': self.test_record.id,
            'default_template_id': self.template.id,
        }).create({
            'body': '<p>Test Body</p>',
        })
        # currently onchange necessary
        composer.onchange_template_id_wrapper()

        # values coming from template
        self.assertEqual(len(composer.attachment_ids), 4)
        for attach in attachs:
            self.assertIn(attach, composer.attachment_ids)
        generated = composer.attachment_ids - attachs
        self.assertEqual(len(generated), 1, 'MailComposer: should have 1 additional attachment for report')
        self.assertEqual(generated.res_model, 'mail.compose.message')
        self.assertEqual(generated.res_id, 0)

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_composer_author(self):
        """ Test author_id / email_from synchronization, in both comment and mass mail
        modes. """
        for composition_mode in ['comment', 'mass_mail']:
            if composition_mode == 'comment':
                ctx = self._get_web_context(self.test_record, add_web=False)
            else:
                ctx = self._get_web_context(self.test_records, add_web=False)
            composer = self.env['mail.compose.message'].with_context(ctx).create({
                'body': '<p>Test Body</p>',
            })

            # default values are current user
            self.assertEqual(composer.author_id, self.env.user.partner_id)
            self.assertEqual(composer.email_from, self.env.user.email_formatted)

            # author values reset email (FIXME: currently not synchronized)
            composer.write({'author_id': self.partner_1})
            self.assertEqual(composer.author_id, self.partner_1)
            self.assertEqual(composer.email_from, self.env.user.email_formatted)
            # self.assertEqual(composer.email_from, self.partner_1.email_formatted)

            # changing template should update its email_from
            composer.write({'template_id': self.template.id, 'author_id': self.env.user.partner_id})
            # currently onchange necessary
            composer.onchange_template_id_wrapper()
            self.assertEqual(composer.author_id, self.env.user.partner_id,
                             'MailComposer: should take value given by user')
            if composition_mode == 'comment':
                self.assertEqual(composer.email_from, self.test_record.user_id.email_formatted,
                                 'MailComposer: should take email_from rendered from template')
            else:
                self.assertEqual(composer.email_from, self.template.email_from,
                                 'MailComposer: should take email_from raw from template')

            # manual values are kept over template values
            composer.write({'email_from': self.test_from})
            self.assertEqual(composer.author_id, self.env.user.partner_id)
            self.assertEqual(composer.email_from, self.test_from)

    @users('employee')
    def test_mail_composer_content_comment(self):
        """ Test content management (subject, body, server) in comment mode.
        Template update is also tested. """
        for composition_mode in ['comment', 'mass_mail']:
            if composition_mode == 'comment':
                ctx = self._get_web_context(self.test_record, add_web=False)
            else:
                ctx = self._get_web_context(self.test_records, add_web=False)

            # 1. check without template + template update
            composer = self.env['mail.compose.message'].with_context(ctx).create({
                'subject': 'My amazing subject',
                'body': '<p>Test Body</p>',
            })

            # creation values are taken
            self.assertEqual(composer.subject, 'My amazing subject')
            self.assertEqual(composer.body, '<p>Test Body</p>')
            self.assertEqual(composer.mail_server_id.id, False)

            # changing template should update its content
            composer.write({'template_id': self.template.id})
            # currently onchange necessary
            composer.onchange_template_id_wrapper()

            # values come from template
            if composition_mode == 'comment':
                self.assertEqual(composer.subject, 'TemplateSubject %s' % self.test_record.name)
                self.assertEqual(composer.body, '<p>TemplateBody %s</p>' % self.test_record.name)
                self.assertEqual(composer.mail_server_id, self.template.mail_server_id)
            else:
                self.assertEqual(composer.subject, self.template.subject)
                self.assertEqual(composer.body, self.template.body_html)
                self.assertEqual(composer.mail_server_id, self.template.mail_server_id)

            # manual values is kept over template
            composer.write({'subject': 'Back to my amazing subject'})
            self.assertEqual(composer.subject, 'Back to my amazing subject')

            # reset template should reset values
            composer.write({'template_id': False})
            # currently onchange necessary
            composer.onchange_template_id_wrapper()

            # values are reset
            if composition_mode == 'comment':
                self.assertEqual(composer.subject, 'Re: %s' % self.test_record.name)
                self.assertEqual(composer.body, '')
                # TDE FIXME: server id is kept, not sure why
                # self.assertFalse(composer.mail_server_id.id)
                self.assertEqual(composer.mail_server_id, self.template.mail_server_id)
            else:
                # values are reset TDE FIXME: strange for subject
                self.assertEqual(composer.subject, 'Back to my amazing subject')
                self.assertEqual(composer.body, '')
                # TDE FIXME: server id is kept, not sure why
                # self.assertFalse(composer.mail_server_id.id)
                self.assertEqual(composer.mail_server_id, self.template.mail_server_id)

            # 2. check with default
            ctx['default_template_id'] = self.template.id
            composer = self.env['mail.compose.message'].with_context(ctx).create({
                'template_id': self.template.id,
            })
            # currently onchange necessary
            composer.onchange_template_id_wrapper()

            # values come from template
            if composition_mode == 'comment':
                self.assertEqual(composer.subject, 'TemplateSubject %s' % self.test_record.name)
                self.assertEqual(composer.body, '<p>TemplateBody %s</p>' % self.test_record.name)
                self.assertEqual(composer.mail_server_id, self.template.mail_server_id)
            else:
                self.assertEqual(composer.subject, self.template.subject)
                self.assertEqual(composer.body, self.template.body_html)
                self.assertEqual(composer.mail_server_id, self.template.mail_server_id)

            # 3. check at create
            ctx.pop('default_template_id')
            composer = self.env['mail.compose.message'].with_context(ctx).create({
                'template_id': self.template.id,
            })
            # currently onchange necessary
            composer.onchange_template_id_wrapper()

            # values come from template
            if composition_mode == 'comment':
                self.assertEqual(composer.subject, 'TemplateSubject %s' % self.test_record.name)
                self.assertEqual(composer.body, '<p>TemplateBody %s</p>' % self.test_record.name)
                self.assertEqual(composer.mail_server_id, self.template.mail_server_id)
            else:
                self.assertEqual(composer.subject, self.template.subject)
                self.assertEqual(composer.body, self.template.body_html)
                self.assertEqual(composer.mail_server_id, self.template.mail_server_id)

            # 4. template + user input
            ctx['default_template_id'] = self.template.id
            composer = self.env['mail.compose.message'].with_context(ctx).create({
                'subject': 'My amazing subject',
                'body': '<p>Test Body</p>',
                'mail_server_id': False,
            })

            # creation values are taken
            self.assertEqual(composer.subject, 'My amazing subject')
            self.assertEqual(composer.body, '<p>Test Body</p>')
            self.assertEqual(composer.mail_server_id.id, False)
