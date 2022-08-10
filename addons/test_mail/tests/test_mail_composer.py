# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from unittest.mock import patch

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.models.test_mail_models import MailTestTicket
from odoo.addons.test_mail.tests.common import TestMailCommon, TestRecipients
from odoo.tests import tagged
from odoo.tests.common import users, Form
from odoo.tools import mute_logger, formataddr

@tagged('mail_composer')
class TestMailComposer(TestMailCommon, TestRecipients):
    """ Test Composer internals """

    @classmethod
    def setUpClass(cls):
        super(TestMailComposer, cls).setUpClass()
        cls._init_mail_gateway()

        # ensure employee can create partners, necessary for templates
        cls.user_employee.write({
            'groups_id': [(4, cls.env.ref('base.group_partner_manager').id)],
        })

        cls.user_employee_2 = mail_new_test_user(
            cls.env, login='employee2', groups='base.group_user',
            notification_type='email', email='eglantine@example.com',
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
        cls.test_record_report = cls.test_report._render_qweb_pdf(cls.test_report.ids)

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
            'email_from': '${(object.user_id.email_formatted or user.email_formatted) | safe}',
            'model_id': cls.env['ir.model']._get('mail.test.ticket').id,
            'mail_server_id': cls.mail_server.id,
            'auto_delete': True,
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
        self.assertEqual(composer_form.model, self.test_record._name)

    @users('employee')
    def test_mail_composer_comment_attachments(self):
        """Tests that all attachments are added to the composer, static attachments
        are not duplicated and while reports are re-generated, and that intermediary
        attachments are dropped."""
        attachment_data = self._generate_attachments_data(2)
        template_1 = self.template.copy({
            'attachment_ids': [(0, 0, a) for a in attachment_data],
            'report_name': 'TestReport for ${object.name}.html',  # test cursor forces html
            'report_template': self.test_report.id,
        })
        template_1_attachments = template_1.attachment_ids
        self.assertEqual(len(template_1_attachments), 2)
        template_2 = self.template.copy({
            'attachment_ids': False,
            'report_template': self.test_report.id,
        })

        # begins without attachments
        composer_form = Form(self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_record, add_web=True, default_attachment_ids=[])
        ))
        self.assertEqual(len(composer_form.attachment_ids), 0)

        # change template: 2 static (attachment_ids) and 1 dynamic (report)
        composer_form.template_id = template_1
        self.assertEqual(len(composer_form.attachment_ids), 3)
        report_attachments = [att for att in composer_form.attachment_ids if att not in template_1_attachments]
        self.assertEqual(len(report_attachments), 1)
        tpl_attachments = composer_form.attachment_ids[:] - report_attachments[0]
        self.assertEqual(tpl_attachments, template_1_attachments)

        # change template: 0 static (attachment_ids) and 1 dynamic (report)
        composer_form.template_id = template_2
        self.assertEqual(len(composer_form.attachment_ids), 1)
        report_attachments = [att for att in composer_form.attachment_ids if att not in template_1_attachments]
        self.assertEqual(len(report_attachments), 1)
        tpl_attachments = composer_form.attachment_ids[:] - report_attachments[0]
        self.assertEqual(tpl_attachments, self.env['ir.attachment'])

        # change back to template 1
        composer_form.template_id = template_1
        self.assertEqual(len(composer_form.attachment_ids), 3)
        report_attachments = [att for att in composer_form.attachment_ids if att not in template_1_attachments]
        self.assertEqual(len(report_attachments), 1)
        tpl_attachments = composer_form.attachment_ids[:] - report_attachments[0]
        self.assertEqual(tpl_attachments, template_1_attachments)

        # reset template
        composer_form.template_id = self.env['mail.template']
        self.assertEqual(len(composer_form.attachment_ids), 0)

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
            'report_name': 'TestReport for ${object.name}.html',  # test cursor forces html
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
        self.assertEqual(generated.name, 'TestReport for %s.html' % self.test_record.name)
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
    def test_mail_composer_content(self):
        """ Test content management (subject, body, server) in both comment and
        mass mailing mode. Template update is also tested. """
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

    @users('employee')
    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail')
    def test_mail_composer_parent(self):
        """ Test specific management in comment mode when having parent_id set:
        record_name, subject, parent's partners. """
        parent = self.test_record.message_post(body='Test', partner_ids=(self.partner_1 + self.partner_2).ids)

        composer = self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_record, add_web=False, default_parent_id=parent.id)
        ).create({
            'body': '<p>Test Body</p>',
        })

        # creation values taken from parent
        self.assertEqual(composer.subject, 'Re: %s' % self.test_record.name)
        self.assertEqual(composer.body, '<p>Test Body</p>')
        self.assertEqual(composer.partner_ids, self.partner_1 + self.partner_2)

    def test_mail_composer_rights_portal(self):
        portal_user = self._create_portal_user()

        with patch.object(MailTestTicket, 'check_access_rights', return_value=True):
            self.env['mail.compose.message'].with_user(portal_user).with_context(
                self._get_web_context(self.test_record)
            ).create({
                'subject': 'Subject',
                'body': '<p>Body text</p>',
                'partner_ids': []
            }).send_mail()

            self.assertEqual(self.test_record.message_ids[0].body, '<p>Body text</p>')
            self.assertEqual(self.test_record.message_ids[0].author_id, portal_user.partner_id)

            self.env['mail.compose.message'].with_user(portal_user).with_context({
                'default_composition_mode': 'comment',
                'default_parent_id': self.test_record.message_ids.ids[0],
            }).create({
                'subject': 'Subject',
                'body': '<p>Body text 2</p>'
            }).send_mail()

            self.assertEqual(self.test_record.message_ids[0].body, '<p>Body text 2</p>')
            self.assertEqual(self.test_record.message_ids[0].author_id, portal_user.partner_id)

    @users('employee')
    def test_mail_composer_save_template(self):
        self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_record, add_web=False)
        ).create({
            'subject': 'Template Subject',
            'body': '<p>Template Body</p>',
        }).save_as_template()

        # Test: email_template subject, body_html, model
        template = self.env['mail.template'].search([
            ('model', '=', self.test_record._name),
            ('subject', '=', 'Template Subject')
        ], limit=1)
        self.assertEqual(template.name, "%s: %s" % (self.env['ir.model']._get(self.test_record._name).name, 'Template Subject'))
        self.assertEqual(template.body_html, '<p>Template Body</p>', 'email_template incorrect body_html')


@tagged('mail_composer')
class TestComposerResultsComment(TestMailComposer):
    """ Test global output of composer used in comment mode. Test notably
    notification and emails generated during this process. """

    @users('employee')
    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail')
    def test_mail_composer_notifications_delete(self):
        """ Notifications are correctly deleted once sent """
        composer = self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_record)
        ).create({
            'body': '<p>Test Body</p>',
            'partner_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]
        })
        with self.mock_mail_gateway(mail_unlink_sent=True):
            composer.send_mail()

        # notifications
        message = self.test_record.message_ids[0]
        self.assertEqual(message.notified_partner_ids, self.partner_employee_2 + self.partner_1 + self.partner_2)

        # global outgoing
        self.assertEqual(len(self._new_mails), 2, 'Should have created 2 mail.mail (1 for users, 1 for customers)')
        self.assertEqual(len(self._mails), 3, 'Should have sent an email each recipient')
        self.assertEqual(self._new_mails.exists(), self.env['mail.mail'], 'Should have deleted mail.mail records')

        # ensure ``mail_auto_delete`` context key allow to override this behavior
        composer = self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_record),
            mail_auto_delete=False,
        ).create({
            'body': '<p>Test Body</p>',
            'partner_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]
        })
        with self.mock_mail_gateway(mail_unlink_sent=True):
            composer.send_mail()

        # notifications
        message = self.test_record.message_ids[0]
        self.assertEqual(message.notified_partner_ids, self.partner_employee_2 + self.partner_1 + self.partner_2)

        # global outgoing
        self.assertEqual(len(self._new_mails), 2, 'Should have created 2 mail.mail (1 for users, 1 for customers)')
        self.assertEqual(len(self._mails), 3, 'Should have sent an email each recipient')
        self.assertEqual(len(self._new_mails.exists()), 2, 'Should not have deleted mail.mail records')

    @users('employee')
    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail')
    def test_mail_composer_recipients(self):
        """ Test partner_ids given to composer are given to the final message. """
        composer = self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_record)
        ).create({
            'body': '<p>Test Body</p>',
            'partner_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]
        })
        composer.send_mail()

        message = self.test_record.message_ids[0]
        self.assertEqual(message.body, '<p>Test Body</p>')
        self.assertEqual(message.author_id, self.user_employee.partner_id)
        self.assertEqual(message.subject, 'Re: %s' % self.test_record.name)
        self.assertEqual(message.subtype_id, self.env.ref('mail.mt_comment'))
        self.assertEqual(message.partner_ids, self.partner_1 | self.partner_2)

    @users('employee')
    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_mail_composer_wtpl_complete(self):
        """ Test a posting process using a complex template, holding several
        additional recipients and attachments.

        This tests notifies: 2 new email_to (+ 1 duplicated), 1 email_cc,
        test_record followers and partner_admin added in partner_to."""
        attachment_data = self._generate_attachments_data(2)
        email_to_1 = 'test.to.1@test.example.com'
        email_to_2 = 'test.to.2@test.example.com'
        email_to_3 = 'test.to.1@test.example.com'  # duplicate: should not sent twice the email
        email_cc_1 = 'test.cc.1@test.example.com'
        self.template.write({
            'auto_delete': False,  # keep sent emails to check content
            'attachment_ids': [(0, 0, a) for a in attachment_data],
            'email_to': '%s, %s, %s' % (email_to_1, email_to_2, email_to_3),
            'email_cc': email_cc_1,
            'partner_to': '%s, ${object.customer_id.id if object.customer_id else ""}' % self.partner_admin.id,
            'report_name': 'TestReport for ${object.name}',  # test cursor forces html
            'report_template': self.test_report.id,
        })
        attachs = self.env['ir.attachment'].search([('name', 'in', [a['name'] for a in attachment_data])])
        self.assertEqual(len(attachs), 2)

        # ensure initial data
        self.assertEqual(self.test_record.user_id, self.user_employee_2)
        self.assertEqual(self.test_record.message_partner_ids, self.partner_employee_2)

        # open a composer and run it in comment mode
        composer_form = Form(self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_record, add_web=True,
                                  default_template_id=self.template.id)
        ))
        composer = composer_form.save()
        self.assertFalse(composer.no_auto_thread, 'Mail: thread-enabled models should use auto thread by default')
        with self.mock_mail_gateway(mail_unlink_sent=False), self.mock_mail_app():
            composer.send_mail()

        # check new partners have been created based on emails given
        new_partners = self.env['res.partner'].search([
            ('email', 'in', [email_to_1, email_to_2, email_to_3, email_cc_1])
        ])
        self.assertEqual(len(new_partners), 3)
        self.assertEqual(set(new_partners.mapped('email')),
                         set(['test.to.1@test.example.com', 'test.to.2@test.example.com', 'test.cc.1@test.example.com'])
                        )

        # global outgoing: one mail.mail (all customer recipients, then all employee recipients)
        # and 5 emails, and 1 inbox notification (admin)
        self.assertEqual(len(self._new_mails), 2, 'Should have created 1 mail.mail')
        self.assertEqual(len(self._mails), 5, 'Should have sent 5 emails, one per recipient')

        # template is sent only to partners (email_to are transformed)
        message = self.test_record.message_ids[0]
        self.assertMailMail(self.partner_employee_2, 'sent',
                            mail_message=message,
                            author=self.partner_employee,  # author != email_from (template sets only email_from)
                            email_values={
                                'body_content': 'TemplateBody %s' % self.test_record.name,
                                'email_from': self.test_record.user_id.email_formatted,  # set by template
                                'subject': 'TemplateSubject %s' % self.test_record.name,
                                'attachments_info': [
                                    {'name': '00.txt', 'raw': b'Att00', 'type': 'text/plain'},
                                    {'name': '01.txt', 'raw': b'Att01', 'type': 'text/plain'},
                                    {'name': 'TestReport for %s.html' % self.test_record.name, 'type': 'text/plain'},
                                ]
                            },
                            fields_values={},
                           )
        self.assertMailMail(self.test_record.customer_id + new_partners, 'sent',
                            mail_message=message,
                            author=self.partner_employee,  # author != email_from (template sets only email_from)
                            email_values={
                                'body_content': 'TemplateBody %s' % self.test_record.name,
                                'email_from': self.test_record.user_id.email_formatted,  # set by template
                                'subject': 'TemplateSubject %s' % self.test_record.name,
                                'attachments_info': [
                                    {'name': '00.txt', 'raw': b'Att00', 'type': 'text/plain'},
                                    {'name': '01.txt', 'raw': b'Att01', 'type': 'text/plain'},
                                    {'name': 'TestReport for %s.html' % self.test_record.name, 'type': 'text/plain'},
                                ]
                            },
                            fields_values={},
                           )

        # message is posted and notified admin
        self.assertEqual(message.subtype_id, self.env.ref('mail.mt_comment'))
        self.assertNotified(message, [{'partner': self.partner_admin, 'is_read': False, 'type': 'inbox'}])
        # attachments are copied on message and linked to document
        self.assertEqual(
            set(message.attachment_ids.mapped('name')),
            set(['00.txt', '01.txt', 'TestReport for %s.html' % self.test_record.name])
        )
        self.assertEqual(set(message.attachment_ids.mapped('res_model')), set([self.test_record._name]))
        self.assertEqual(set(message.attachment_ids.mapped('res_id')), set(self.test_record.ids))
        self.assertTrue(all(attach not in message.attachment_ids for attach in attachs), 'Should have copied attachments')


@tagged('mail_composer')
class TestComposerResultsMass(TestMailComposer):

    @classmethod
    def setUpClass(cls):
        super(TestComposerResultsMass, cls).setUpClass()
        # ensure employee can create partners, necessary for templates
        cls.user_employee.write({
            'groups_id': [(4, cls.env.ref('base.group_partner_manager').id)],
        })

    @users('employee')
    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_mail_composer_wtpl(self):
        self.template.auto_delete = False  # keep sent emails to check content
        composer_form = Form(self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_records, add_web=True,
                                  default_template_id=self.template.id)
        ))
        composer = composer_form.save()
        self.assertFalse(composer.no_auto_thread, 'Mail: thread-enabled models should use auto thread by default')
        with self.mock_mail_gateway(mail_unlink_sent=True):
            composer.send_mail()

        # global outgoing
        self.assertEqual(len(self._new_mails), 2, 'Should have created 1 mail.mail per record')
        self.assertEqual(len(self._mails), 2, 'Should have sent 1 email per record')

        for record in self.test_records:
            # message copy is kept
            message = record.message_ids[0]

            # template is sent directly using customer field, meaning we have recipients
            self.assertMailMail(record.customer_id, 'sent',
                                mail_message=message,
                                author=self.partner_employee)

            # message content
            self.assertEqual(message.subject, 'TemplateSubject %s' % record.name)
            self.assertEqual(message.body, '<p>TemplateBody %s</p>' % record.name)
            self.assertEqual(message.author_id, self.user_employee.partner_id)
            # post-related fields are void
            self.assertEqual(message.subtype_id, self.env['mail.message.subtype'])
            self.assertEqual(message.partner_ids, self.env['res.partner'])

    @users('employee')
    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_mail_composer_wtpl_complete(self):
        """ Test a composer in mass mode with a quite complete template, containing
        notably email-based recipients and attachments. """
        attachment_data = self._generate_attachments_data(2)
        email_to_1 = 'test.to.1@test.example.com'
        email_to_2 = 'test.to.2@test.example.com'
        email_to_3 = 'test.to.1@test.example.com'  # duplicate: should not sent twice the email
        email_cc_1 = 'test.cc.1@test.example.com'
        self.template.write({
            'auto_delete': False,  # keep sent emails to check content
            'attachment_ids': [(0, 0, a) for a in attachment_data],
            'email_to': '%s, %s, %s' % (email_to_1, email_to_2, email_to_3),
            'email_cc': email_cc_1,
            'partner_to': '%s, ${object.customer_id.id if object.customer_id else ""}' % self.partner_admin.id,
            'report_name': 'TestReport for ${object.name}',  # test cursor forces html
            'report_template': self.test_report.id,
        })
        attachs = self.env['ir.attachment'].search([('name', 'in', [a['name'] for a in attachment_data])])
        self.assertEqual(len(attachs), 2)

        # ensure initial data
        self.assertEqual(self.test_records.user_id, self.env['res.users'])
        self.assertEqual(self.test_records.message_partner_ids, self.env['res.partner'])

        # launch composer in mass mode
        composer_form = Form(self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_records, add_web=True,
                                  default_template_id=self.template.id)
        ))
        composer = composer_form.save()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            composer.send_mail()

        new_partners = self.env['res.partner'].search([
            ('email', 'in', [email_to_1, email_to_2, email_to_3, email_cc_1])
        ])
        self.assertEqual(len(new_partners), 3)

        # global outgoing
        self.assertEqual(len(self._new_mails), 2, 'Should have created 1 mail.mail per record')
        self.assertEqual(len(self._mails), 10, 'Should have sent 5 emails per record')

        # hack to use assertEmails: filtering on from/to only is not sufficient to distinguish emails
        _mails_records = [
            [mail for mail in self._mails if '%s-%s' % (record.id, record._name) in mail['message_id']]
            for record in self.test_records
        ]

        for record, _mails in zip(self.test_records, _mails_records):
            # message copy is kept
            message = record.message_ids[0]

            # template is sent only to partners (email_to are transformed)
            self._mails = _mails
            self.assertMailMail(record.customer_id + new_partners + self.partner_admin,
                                'sent',
                                mail_message=message,
                                author=self.partner_employee,
                                email_values={
                                    'attachments_info': [
                                        {'name': '00.txt', 'raw': b'Att00', 'type': 'text/plain'},
                                        {'name': '01.txt', 'raw': b'Att01', 'type': 'text/plain'},
                                        {'name': 'TestReport for %s.html' % record.name, 'type': 'text/plain'},
                                    ],
                                    'body_content': 'TemplateBody %s' % record.name,
                                    'email_from': self.partner_employee.email_formatted,
                                    'reply_to': formataddr((
                                        f'{self.env.user.company_id.name} {record.name}',
                                        f'{self.alias_catchall}@{self.alias_domain}'
                                    )),
                                    'subject': 'TemplateSubject %s' % record.name,
                                },
                                fields_values={
                                    'email_from': self.partner_employee.email_formatted,
                                    'reply_to': formataddr((
                                        f'{self.env.user.company_id.name} {record.name}',
                                        f'{self.alias_catchall}@{self.alias_domain}'
                                    )),
                                },
                               )

        # test without catchall filling reply-to
        composer_form = Form(self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_records, add_web=True,
                                  default_template_id=self.template.id)
        ))
        composer = composer_form.save()
        with self.mock_mail_gateway(mail_unlink_sent=True):
            # remove alias so that _notify_get_reply_to will return the default value instead of alias
            self.env['ir.config_parameter'].sudo().set_param("mail.catchall.domain", None)
            composer.send_mail()

        # hack to use assertEmails: filtering on from/to only is not sufficient to distinguish emails
        _mails_records = [
            [mail for mail in self._mails if '%s-%s' % (record.id, record._name) in mail['message_id']]
            for record in self.test_records
        ]

        for record, _mails in zip(self.test_records, _mails_records):
            # template is sent only to partners (email_to are transformed)
            self._mails = _mails
            self.assertMailMail(record.customer_id + new_partners + self.partner_admin,
                                'sent',
                                mail_message=record.message_ids[0],
                                author=self.partner_employee,
                                email_values={
                                    'email_from': self.partner_employee.email_formatted,
                                    'reply_to': self.partner_employee.email_formatted,
                                },
                                fields_values={
                                    'email_from': self.partner_employee.email_formatted,
                                    'reply_to': self.partner_employee.email_formatted,
                                },
                               )

    @users('employee')
    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_mail_composer_wtpl_delete(self):
        self.template.auto_delete = True
        composer_form = Form(self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_records, add_web=True,
                                  default_template_id=self.template.id)
        ))
        composer = composer_form.save()
        with self.mock_mail_gateway(mail_unlink_sent=True):
            composer.send_mail()

        # global outgoing
        self.assertEqual(len(self._new_mails), 2, 'Should have created 1 mail.mail per record')
        self.assertEqual(len(self._mails), 2, 'Should have sent 1 email per record')
        self.assertEqual(self._new_mails.exists(), self.env['mail.mail'], 'Should have deleted mail.mail records')

        for record in self.test_records:
            # message copy is kept
            message = record.message_ids[0]

            # template is sent directly using customer field
            self.assertSentEmail(self.partner_employee, record.customer_id)

            # message content
            self.assertEqual(message.subject, 'TemplateSubject %s' % record.name)
            self.assertEqual(message.body, '<p>TemplateBody %s</p>' % record.name)
            self.assertEqual(message.author_id, self.user_employee.partner_id)
            # post-related fields are void
            self.assertEqual(message.subtype_id, self.env['mail.message.subtype'])
            self.assertEqual(message.partner_ids, self.env['res.partner'])

    @users('employee')
    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_mail_composer_wtpl_delete_notif(self):
        self.template.auto_delete = True
        composer_form = Form(self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_records, add_web=True,
                                  default_template_id=self.template.id,
                                  default_auto_delete_message=True)
        ))
        composer = composer_form.save()
        with self.mock_mail_gateway(mail_unlink_sent=True):
            composer.send_mail()

        # global outgoing
        self.assertEqual(len(self._new_mails), 2, 'Should have created 1 mail.mail per record')
        self.assertEqual(len(self._mails), 2, 'Should have sent 1 email per record')
        self.assertEqual(self._new_mails.exists(), self.env['mail.mail'], 'Should have deleted mail.mail records')

        for record in self.test_records:
            # message copy is unlinked
            self.assertEqual(record.message_ids, self.env['mail.message'], 'Should have deleted mail.message records')

            # template is sent directly using customer field
            self.assertSentEmail(self.partner_employee, record.customer_id)

    @users('employee')
    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_mail_composer_wtpl_no_auto_thread(self):
        """ Test no auto thread behavior, notably with reply-to. """
        # launch composer in mass mode
        composer_form = Form(self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_records, add_web=True,
                                  default_template_id=self.template.id)
        ))
        composer_form.no_auto_thread = True
        composer_form.reply_to = "${('\"' + object.name + '\" <%s>' % 'dynamic.reply.to@test.com') | safe}"
        composer = composer_form.save()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            composer.send_mail()

        for record in self.test_records:
            self.assertMailMail(record.customer_id,
                                'sent',
                                mail_message=record.message_ids[0],
                                author=self.partner_employee,
                                email_values={
                                    'body_content': 'TemplateBody %s' % record.name,
                                    'email_from': self.partner_employee.email_formatted,
                                    'reply_to': formataddr((
                                        f'{record.name}',
                                        'dynamic.reply.to@test.com'
                                    )),
                                    'subject': 'TemplateSubject %s' % record.name,
                                },
                                fields_values={
                                    'email_from': self.partner_employee.email_formatted,
                                    'reply_to': formataddr((
                                        f'{record.name}',
                                        'dynamic.reply.to@test.com'
                                    )),
                                },
                               )

    @users('employee')
    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_mail_composer_wtpl_recipients(self):
        """ Test various combinations of recipients: active_domain, active_id,
        active_ids, ... to ensure fallback behavior are working. """
        # 1: active_domain
        composer_form = Form(self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_records, add_web=True,
                                  default_template_id=self.template.id,
                                  active_ids=[],
                                  default_use_active_domain=True,
                                  default_active_domain=[('id', 'in', self.test_records.ids)])
        ))
        composer = composer_form.save()
        with self.mock_mail_gateway(mail_unlink_sent=True):
            composer.send_mail()

        # global outgoing
        self.assertEqual(len(self._new_mails), 2, 'Should have created 1 mail.mail per record')
        self.assertEqual(len(self._mails), 2, 'Should have sent 1 email per record')

        for record in self.test_records:
            # template is sent directly using customer field
            self.assertSentEmail(self.partner_employee, record.customer_id)

        # 2: active_domain not taken into account if use_active_domain is False
        composer_form = Form(self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_records, add_web=True,
                                  default_template_id=self.template.id,
                                  default_use_active_domain=False,
                                  default_active_domain=[('id', 'in', -1)])
        ))
        composer = composer_form.save()
        with self.mock_mail_gateway(mail_unlink_sent=True):
            composer.send_mail()

        # global outgoing
        self.assertEqual(len(self._new_mails), 2, 'Should have created 1 mail.mail per record')
        self.assertEqual(len(self._mails), 2, 'Should have sent 1 email per record')

        # 3: fallback on active_id if not active_ids
        composer_form = Form(self.env['mail.compose.message'].with_context(
            self._get_web_context(self.test_records, add_web=True,
                                  default_template_id=self.template.id,
                                  active_ids=[])
        ))
        composer = composer_form.save()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            composer.send_mail()

        # global outgoing
        self.assertEqual(len(self._new_mails), 1, 'Should have created 1 mail.mail per record')
        self.assertEqual(len(self._mails), 1, 'Should have sent 1 email per record')

        # 3: void is void
        composer_form = Form(self.env['mail.compose.message'].with_context(
            default_model='mail.test.ticket',
            default_template_id=self.template.id
        ))
        composer = composer_form.save()
        with self.mock_mail_gateway(mail_unlink_sent=False), self.assertRaises(ValueError):
            composer.send_mail()
