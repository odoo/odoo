# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from markupsafe import Markup

from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError, UserError
from odoo.modules.module import get_module_resource
from odoo.tests import Form, users
from odoo.tools import convert_file


class TestMailTemplate(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailTemplate, cls).setUpClass()
        # Enable the Jinja rendering restriction
        cls.env['ir.config_parameter'].set_param('mail.restrict.template.rendering', True)
        cls.user_employee.groups_id -= cls.env.ref('mail.group_mail_template_editor')

        cls.mail_template = cls.env['mail.template'].create({
            'name': 'Test template',
            'subject': '{{ 1 + 5 }}',
            'body_html': '<t t-out="4 + 9"/>',
            'lang': '{{ object.lang }}',
            'auto_delete': True,
            'model_id': cls.env.ref('base.model_res_partner').id,
        })

    @users('employee')
    def test_mail_compose_message_content_from_template(self):
        form = Form(self.env['mail.compose.message'])
        form.template_id = self.mail_template
        mail_compose_message = form.save()

        self.assertEqual(mail_compose_message.subject, '6', 'We must trust mail template values')

    @users('employee')
    def test_mail_compose_message_content_from_template_mass_mode(self):
        mail_compose_message = self.env['mail.compose.message'].create({
            'composition_mode': 'mass_mail',
            'model': 'res.partner',
            'template_id': self.mail_template.id,
            'subject': '{{ 1 + 5 }}',
        })

        values = mail_compose_message.get_mail_values(self.partner_employee.ids)

        self.assertEqual(values[self.partner_employee.id]['subject'], '6', 'We must trust mail template values')
        self.assertIn('13', values[self.partner_employee.id]['body_html'], 'We must trust mail template values')

    def test_mail_template_acl(self):
        # Sanity check
        self.assertTrue(self.user_admin.has_group('mail.group_mail_template_editor'))
        self.assertFalse(self.user_employee.has_group('mail.group_mail_template_editor'))

        # Group System can create / write / unlink mail template
        mail_template = self.env['mail.template'].with_user(self.user_admin).create({'name': 'Test template'})
        self.assertEqual(mail_template.name, 'Test template')

        mail_template.with_user(self.user_admin).name = 'New name'
        self.assertEqual(mail_template.name, 'New name')

        # Standard employee can create and edit non-dynamic templates
        employee_template = self.env['mail.template'].with_user(self.user_employee).create({'body_html': '<p>foo</p>'})

        employee_template.with_user(self.user_employee).body_html = '<p>bar</p>'

        employee_template = self.env['mail.template'].with_user(self.user_employee).create({'email_to': 'foo@bar.com'})

        employee_template.with_user(self.user_employee).email_to = 'bar@foo.com'

        # Standard employee cannot create and edit templates with dynamic qweb
        with self.assertRaises(AccessError):
            self.env['mail.template'].with_user(self.user_employee).create({'body_html': '<p t-esc="\'foo\'"></p>'})

        # Standard employee cannot edit templates from another user, non-dynamic and dynamic
        with self.assertRaises(AccessError):
            mail_template.with_user(self.user_employee).body_html = '<p>foo</p>'
        with self.assertRaises(AccessError):
            mail_template.with_user(self.user_employee).body_html = '<p t-esc="\'foo\'"></p>'

        # Standard employee can edit his own templates if not dynamic
        employee_template.with_user(self.user_employee).body_html = '<p>foo</p>'

        # Standard employee cannot create and edit templates with dynamic inline fields
        with self.assertRaises(AccessError):
            self.env['mail.template'].with_user(self.user_employee).create({'email_to': '{{ object.partner_id.email }}'})

        # Standard employee cannot edit his own templates if dynamic
        with self.assertRaises(AccessError):
            employee_template.with_user(self.user_employee).body_html = '<p t-esc="\'foo\'"></p>'

        with self.assertRaises(AccessError):
            employee_template.with_user(self.user_employee).email_to = '{{ object.partner_id.email }}'

    def test_mail_template_acl_translation(self):
        ''' Test that a user that doenn't have the group_mail_template_editor cannot create / edit
        translation with dynamic code if he cannot write dynamic code on the related record itself.
        '''

        self.env.ref('base.lang_fr').sudo().active = True

        employee_template = self.env['mail.template'].with_user(self.user_employee).create({
            'model_id': self.env.ref('base.model_res_partner').id,
            'subject': 'The subject',
            'body_html': '<p>foo</p>',
        })

        ### check qweb dynamic
        # write on translation for template without dynamic code is allowed
        employee_template.with_context(lang='fr_FR').body_html = 'non-qweb'

        # cannot write dynamic code on mail_template translation for employee without the group mail_template_editor.
        with self.assertRaises(AccessError):
            employee_template.with_context(lang='fr_FR').body_html = '<t t-esc="foo"/>'

        employee_template.with_context(lang='fr_FR').sudo().body_html = '<t t-esc="foo"/>'

        # reset the body_html to static
        employee_template.body_html = False
        employee_template.body_html = '<p>foo</p>'

        ### check qweb inline dynamic
        # write on translation for template without dynamic code is allowed
        employee_template.with_context(lang='fr_FR').subject = 'non-qweb'

        # cannot write dynamic code on mail_template translation for employee without the group mail_template_editor.
        with self.assertRaises(AccessError):
            employee_template.with_context(lang='fr_FR').subject = '{{ object.foo }}'

        employee_template.with_context(lang='fr_FR').sudo().subject = '{{ object.foo }}'

    def test_server_archived_usage_protection(self):
        """ Test the protection against using archived server (servers used cannot be archived) """
        IrMailServer = self.env['ir.mail_server']
        server = IrMailServer.create({
            'name': 'Server',
            'smtp_host': 'archive-test.smtp.local',
        })
        self.mail_template.mail_server_id = server.id
        with self.assertRaises(UserError, msg='Server cannot be archived because it is used'):
            server.action_archive()
        self.assertTrue(server.active)
        self.mail_template.mail_server_id = IrMailServer
        server.action_archive()  # No more usage -> can be archived
        self.assertFalse(server.active)


class TestMailTemplateReset(MailCommon):

    def _load(self, module, *args):
        convert_file(self.cr, module='mail',
                     filename=get_module_resource(module, *args),
                     idref={}, mode='init', noupdate=False, kind='test')

    def test_mail_template_reset(self):
        self._load('mail', 'tests', 'test_mail_template.xml')

        mail_template = self.env.ref('mail.mail_template_test').with_context(lang=self.env.user.lang)

        mail_template.write({
            'body_html': '<div>Hello</div>',
            'name': 'Mail: Mail Template',
            'subject': 'Test',
            'email_from': 'admin@example.com',
            'email_to': 'user@example.com',
            'attachment_ids': False,
        })

        context = {'default_template_ids': mail_template.ids}
        mail_template_reset = self.env['mail.template.reset'].with_context(context).create({})
        reset_action = mail_template_reset.reset_template()
        self.assertTrue(reset_action)

        self.assertEqual(mail_template.body_html.strip(), Markup('<div>Hello Odoo</div>'))
        self.assertEqual(mail_template.name, 'Mail: Test Mail Template')
        self.assertEqual(
            mail_template.email_from,
            '"{{ object.company_id.name }}" <{{ (object.company_id.email or user.email) }}>'
        )
        self.assertEqual(mail_template.email_to, '{{ object.email_formatted }}')
        self.assertEqual(mail_template.attachment_ids, self.env.ref('mail.mail_template_test_attachment'))

        # subject is not there in the data file template, so it should be set to False
        self.assertFalse(mail_template.subject, "Subject should be set to False")
