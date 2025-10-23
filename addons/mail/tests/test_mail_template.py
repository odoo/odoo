# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from markupsafe import Markup
from unittest.mock import patch

from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.tests import Form, HttpCase, tagged, users
from odoo.tools import convert_file, mute_logger


@tagged('mail_template')
class TestMailTemplate(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailTemplate, cls).setUpClass()
        # Enable the Jinja rendering restriction
        cls.env['ir.config_parameter'].set_param('mail.restrict.template.rendering', True)
        cls.user_employee.group_ids -= cls.env.ref('mail.group_mail_template_editor')
        cls.test_partner = cls.env['res.partner'].create({
            'email': 'test.rendering@test.example.com',
            'name': 'Test Rendering',
        })

        cls.mail_template = cls.env['mail.template'].create({
            'name': 'Test template',
            'subject': '{{ 1 + 5 }}',
            'body_html': '<t t-out="4 + 9"/>',
            'lang': '{{ object.lang }}',
            'auto_delete': True,
            'model_id': cls.env.ref('base.model_res_partner').id,
            'use_default_to': False,
        })

        cls.user_employee_2 = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='employee_2@test.com',
            groups='base.group_user',
            login='employee_2',
            name='Albertine Another Employee',
        )

    @users('admin')
    @mute_logger('odoo.addons.mail.models.mail_template')
    @mute_logger('odoo.addons.mail.models.mail_render_mixin')
    def test_invalid_template_on_save(self):
        mail_template = self.env['mail.template'].create({
                'name': 'Test template',
                'model_id': self.env['ir.model']._get_id('res.users'),
                'subject': 'Template {{ object.company_id.email }}',
                'lang': '{{ object.partner_id.lang }}'
            })

        for fname in [
            'body_html', 'email_cc', 'email_from', 'email_to',
            'lang', 'partner_to', 'reply_to', 'scheduled_date',
            'subject'
        ]:
            with self.subTest(fname=fname):
                if fname == 'body_html':
                    value_field = '<p>Hello <t t-out="object.unknown_field"/></p>'
                    value_fun = '<p>Hello <t t-out="object.is_portal_0()"/></p>'
                else:
                    value_field = '{{ object.unknown_field }}'
                    value_fun = '{{ object.is_portal_0() }}'
                # cannot update with a wrong field
                with self.assertRaises(ValidationError):
                    mail_template.write({
                        fname: value_field,
                    })
                with self.assertRaises(ValidationError):
                    mail_template.write({
                        fname: value_fun,
                    })
                # Check templates having invalid object references can't be created
                with self.assertRaises(ValidationError):
                    self.env['mail.template'].create({
                        'name': 'Test template',
                        'model_id': self.env['ir.model']._get('res.users').id,
                        fname: value_field,
                    })

        # new model would crash at rendering
        with self.assertRaises(ValidationError):
            mail_template.write({
                'model_id': self.env['ir.model']._get_id('res.partner'),
            })

    @users('employee')
    def test_mail_compose_message_content_from_template(self):
        form = Form(self.env['mail.compose.message'].with_context(default_model='res.partner', active_ids=self.test_partner.ids))
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

        values = mail_compose_message._prepare_mail_values(self.partner_employee.ids)

        self.assertEqual(values[self.partner_employee.id]['subject'], '6', 'We must trust mail template values')
        self.assertIn('13', values[self.partner_employee.id]['body_html'], 'We must trust mail template values')

    @users('admin')
    def test_mail_template_abstract_model(self):
        """Check abstract models cannot be set on templates."""
        # create
        with self.assertRaises(ValidationError):
            self.env['mail.template'].create({
                'name': 'Test abstract template',
                'model_id': self.env['ir.model']._get('mail.thread').id, # abstract model
            })
        # write
        template = self.env['mail.template'].create({
            'name': 'Test abstract template',
            'model_id': self.env['ir.model']._get('res.partner').id,
        })
        with self.assertRaises(ValidationError):
            template.write({
                'name': 'Test abstract template',
                'model_id': self.env['ir.model']._get('mail.thread').id,
            })

    def test_mail_template_acl(self):
        # Sanity check
        self.assertTrue(self.user_admin.has_group('mail.group_mail_template_editor'))
        self.assertTrue(self.user_admin.has_group('base.group_sanitize_override'))
        self.assertFalse(self.user_employee.has_group('mail.group_mail_template_editor'))
        self.assertFalse(self.user_employee.has_group('base.group_sanitize_override'))

        model = self.env['ir.model']._get_id('res.users')
        record = self.user_employee

        # Group System can create / write / unlink mail template
        mail_template = self.env['mail.template'].with_user(self.user_admin).create({
            'name': 'Test template',
            'model_id': model,
        })
        self.assertEqual(mail_template.name, 'Test template')

        mail_template.with_user(self.user_admin).name = 'New name'
        self.assertEqual(mail_template.name, 'New name')

        # Standard employee can create and edit non-dynamic templates
        employee_template = self.env['mail.template'].with_user(self.user_employee).create({'body_html': '<p>foo</p>', 'model_id': model})
        employee_template.with_user(self.user_employee).body_html = '<p>bar</p>'

        employee_template = self.env['mail.template'].with_user(self.user_employee).create({
            'email_to': 'foo@bar.com',
            'model_id': model,
        })
        employee_template = employee_template.with_user(self.user_employee)

        employee_template.email_to = 'bar@foo.com'

        # Standard employee cannot create and edit templates with forbidden expression
        with self.assertRaises(AccessError):
            self.env['mail.template'].with_user(self.user_employee).create({'body_html': '''<p t-out="'foo'"></p>''', 'model_id': model})

        # If no model is specify, he can not write allowed expression
        with self.assertRaises(AccessError):
            self.env['mail.template'].with_user(self.user_employee).create({'body_html': '''<p t-out="object.name"></p>'''})

        # Standard employee cannot edit templates from another user, non-dynamic and dynamic
        with self.assertRaises(AccessError):
            mail_template.with_user(self.user_employee).body_html = '<p>foo</p>'
        with self.assertRaises(AccessError):
            mail_template.with_user(self.user_employee).body_html = '''<p t-out="'foo'"></p>'''

        # Standard employee can edit his own templates if not dynamic
        employee_template.body_html = '<p>foo</p>'

        # Standard employee cannot create and edit templates with dynamic inline fields
        with self.assertRaises(AccessError):
            self.env['mail.template'].with_user(self.user_employee).create({'email_to': '{{ object.partner_id.email }}', 'model_id': model})

        # Standard employee cannot edit his own templates if dynamic
        with self.assertRaises(AccessError):
            employee_template.body_html = '''<p t-out="'foo'"></p>'''

        forbidden_expressions = (
            'object.partner_id.email',
            'object.password',
            "object.name or (1+1)",
            'user.password',
            'object.name or object.name',
            '[a for a in (1,)]',
            "object.name or f''",
            "object.name or ''.format",
            "object.name or f'{1+1}'",
            "object.name or len('')",
            "'abcd' or object.name",
            "object.name and ''",
        )
        for expression in forbidden_expressions:
            with self.assertRaises(AccessError):
                employee_template.email_to = '{{ %s }}' % expression

            with self.assertRaises(AccessError):
                employee_template.email_to = '{{ %s ||| Bob}}' % expression

            with self.assertRaises(AccessError):
                employee_template.body_html = '<p t-out="%s"></p>' % expression

            with self.assertRaises(AccessError):
                employee_template.body_html = '<p t-esc="%s"></p>' % expression

            # try to cheat with the context
            with self.assertRaises(AccessError):
                employee_template.with_context(raise_on_forbidden_code=False).email_to = '{{ %s }}' % expression
            with self.assertRaises(AccessError):
                employee_template.with_context(raise_on_forbidden_code=False).body_html = '<p t-esc="%s"></p>' % expression

            # check that an admin can use the expression
            mail_template.with_user(self.user_admin).email_to = '{{ %s }}' % expression
            mail_template.with_user(self.user_admin).email_to = '{{ %s ||| Bob }}' % expression
            mail_template.with_user(self.user_admin).body_html = '<p t-out="%s">Default</p>' % expression
            mail_template.with_user(self.user_admin).body_html = '<p t-esc="%s">Default</p>' % expression

        # hide qweb code in t-inner-content
        code = '''<t t-inner-content="<p t-out='1+11'>Test</p>"></t>'''
        body = self.env['mail.render.mixin']._render_template_qweb(code, 'res.partner', record.ids)[record.id]
        self.assertNotIn('12', body)
        code = '''<t t-inner-content="&lt;p t-out='1+11'&gt;Test&lt;/p&gt;"></t>'''
        body = self.env['mail.render.mixin']._render_template_qweb(code, 'res.partner', record.ids)[record.id]
        self.assertNotIn('12', body)

        forbidden_qweb_expressions = (
            '<p t-out="partner_id.name"></p>',
            '<p t-esc="partner_id.name"></p>',
            '<p t-debug=""></p>',
            '<p t-set="x" t-value="object.name"></p>',
            '<p t-set="x" t-value="object.name"></p>',
            '<p t-groups="base.group_system"></p>',
            '<t t-call="template"/>',
            '<t t-set="namn" t-value="Hello {{world}} !"/>',
            '<t t-att-test="object.name"/>',
            '<p t-att-title="object.name"></p>',
            # allowed expression with other attribute
            '<p t-out="object.name" title="Test"></p>',
            # allowed expression with child
            '<p t-out="object.name"><img/></p>',
            '<p t-out="object.password"></p>',
        )
        for expression in forbidden_qweb_expressions:
            with self.assertRaises(AccessError):
                employee_template.body_html = expression
            self.assertTrue(self.env['mail.render.mixin']._has_unsafe_expression_template_qweb(expression, 'res.partner'))

        # allowed expressions
        allowed_qweb_expressions = (
            '<p t-out="object.name"></p>',
            '<p t-out="object.name"></p><img/>',
            '<p t-out="object.name"></p><img title="Test"/>',
            '<p t-out="object.name">Default</p>',
            '<p t-out="object.partner_id.name">Default</p>',

        )
        o_qweb_render = self.env['ir.qweb']._render
        for expression in allowed_qweb_expressions:
            template = self.env['mail.template'].with_user(self.user_employee).create({
                'body_html': expression,
                'model_id': model,
            })
            self.assertFalse(self.env['mail.render.mixin']._has_unsafe_expression_template_qweb(expression, 'res.partner'))

            with (patch('odoo.addons.base.models.ir_qweb.IrQweb._render', side_effect=o_qweb_render) as qweb_render,
                patch('odoo.addons.base.models.ir_qweb.unsafe_eval', side_effect=eval) as unsafe_eval):
                rendered = template._render_field('body_html', record.ids)[record.id]
                self.assertNotIn('t-out', rendered)
                self.assertFalse(qweb_render.called)
                self.assertFalse(unsafe_eval.called)

        # double check that we can detect the qweb rendering
        mail_template.body_html = '<t t-out="1+1"/>'
        with (patch('odoo.addons.base.models.ir_qweb.IrQweb._render', side_effect=o_qweb_render) as qweb_render,
            patch('odoo.addons.base.models.ir_qweb.unsafe_eval', side_effect=eval) as unsafe_eval):
            rendered = mail_template._render_field('body_html', record.ids)[record.id]
            self.assertNotIn('t-out', rendered)
            self.assertTrue(qweb_render.called)
            self.assertTrue(unsafe_eval.called)

        employee_template.email_to = 'Test {{ object.name }}'
        with patch('odoo.tools.safe_eval.unsafe_eval', side_effect=eval) as unsafe_eval:
            employee_template._render_field('email_to', record.ids)
            self.assertFalse(unsafe_eval.called)

        # double check that we can detect the eval call
        mail_template.email_to = 'Test {{ 1+1 }}'
        with patch('odoo.tools.safe_eval.unsafe_eval', side_effect=eval) as unsafe_eval:
            mail_template._render_field('email_to', record.ids)
            self.assertTrue(unsafe_eval.called)

        # malformed HTML (html_normalize should prevent the regex rendering on the malformed HTML)
        templates = (
            # here sanitizer adds an 'equals void' after object.name as properties
            # should have values
            ('''<p ou="<p t-out="object.name">"</p>''', '<p ou="&lt;p t-out=" object.name="">"</p>'),
            ('''<p title="'<p t-out='object.name'/>">''', '''<p title="'&lt;p t-out='object.name'/&gt;"></p>'''),
        )
        o_render = self.env['mail.render.mixin']._render_template_qweb_regex
        for template, excepted in templates:
            mail_template.body_html = template
            with patch('odoo.addons.mail.models.mail_render_mixin.MailRenderMixin._render_template_qweb_regex', side_effect=o_render) as render:
                rendered = mail_template._render_field('body_html', record.ids)[record.id]
                self.assertEqual(rendered, excepted)
                self.assertTrue(render.called)

        record.name = '<b> test </b>'
        mail_template.body_html = '<t t-out="object.name"/>'
        with patch('odoo.addons.mail.models.mail_render_mixin.MailRenderMixin._render_template_qweb_regex', side_effect=o_render) as render:
            rendered = mail_template._render_field('body_html', record.ids)[record.id]
            self.assertEqual(rendered, "&lt;b&gt; test &lt;/b&gt;")
            self.assertTrue(render.called)

        # Check that the environment is the evaluation context
        mail_template.with_user(self.user_admin).email_to = '{{ env.user.name }}'
        rendered = mail_template._render_field('email_to', record.ids)[record.id]
        self.assertIn(self.user_admin.name, rendered)

    def test_mail_template_acl_translation(self):
        ''' Test that a user that doesn't have the group_mail_template_editor cannot create / edit
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
            employee_template.with_context(lang='fr_FR').subject = '{{ object.city }}'

        employee_template.with_context(lang='fr_FR').sudo().subject = '{{ object.city }}'

    def test_mail_template_copy(self):
        (self.user_employee + self.user_employee_2).write({
            'group_ids': [(4, self.env.ref('mail.group_mail_template_editor').id)],
        })
        attachment_data_list = self._generate_attachments_data(4, self.mail_template._name, self.mail_template.id)
        self.mail_template.write({
            'attachment_ids': [
                (0, 0, attachment_data)
                for attachment_data in attachment_data_list[:2]
            ],
        })
        original_attachments = self.mail_template.attachment_ids
        # users access template, can read attachments
        for test_user in (self.user_employee, self.user_employee_2):
            with self.subTest(user_name=test_user.name):
                template = self.mail_template.with_user(test_user)
                self.assertEqual(
                    set(template.attachment_ids.mapped('name')),
                    {'AttFileName_00.txt', 'AttFileName_01.txt'},
                )
        # other template for multi copy support
        mail_template_2 = self.env['mail.template'].create({
            'name': 'Test Template 2',
        })

        # employee make a private copy -> other template should still be readable
        new_template, new_template_2 = (self.mail_template + mail_template_2).with_user(self.user_employee).copy()
        new_template.user_id = self.user_employee
        self.assertEqual(
            set(new_template.attachment_ids.mapped('name')),
            {'AttFileName_00.txt', 'AttFileName_01.txt'},
        )
        self.assertFalse(
            new_template.attachment_ids & original_attachments,
            'Template copy should copy attachments, not keep the same, to avoid ACLs / ownership issues',
        )
        self.assertFalse(new_template_2.attachment_ids, 'Should not take attachments from first template in multi copy')
        self.assertEqual(new_template.name, f'{self.mail_template.name} (copy)', 'Default name should be the old one + copy')
        self.assertEqual(new_template_2.name, f'{mail_template_2.name} (copy)', 'Default name should be the old one + copy')
        # linked to their respective template
        self.assertEqual(new_template.attachment_ids.mapped('res_id'), new_template.ids * 2)
        self.assertEqual(original_attachments.mapped('res_id'), self.mail_template.ids * 2)

        new_template_as2 = new_template.with_user(self.user_employee_2)
        self.assertEqual(
            set(new_template_as2.attachment_ids.mapped('name')),
            {'AttFileName_00.txt', 'AttFileName_01.txt'},
        )

        # check default is correctly used instead of copy
        newer_template, newer_template_2 = (self.mail_template + mail_template_2).with_user(self.user_employee).copy(default={
            'attachment_ids': [
                (0, 0, attachment_data_list[2]),
                (0, 0, attachment_data_list[3]),
            ],
            'name': 'My Copy',
        })
        self.assertEqual(
            set(newer_template.attachment_ids.mapped('name')),
            {'AttFileName_02.txt', 'AttFileName_03.txt'},
        )
        self.assertEqual(
            set(newer_template_2.attachment_ids.mapped('name')),
            {'AttFileName_02.txt', 'AttFileName_03.txt'},
        )
        self.assertFalse(
            newer_template.attachment_ids & (original_attachments & new_template.attachment_ids),
            'Template copy should copy attachments, not keep the same, to avoid ACLs / ownership issues',
        )
        self.assertFalse(
            newer_template_2.attachment_ids & newer_template.attachment_ids,
            'Template copy should copy attachments, not keep the same, to avoid ACLs / ownership issues',
        )
        self.assertEqual(newer_template.name, 'My Copy', 'Copy should respect given default')
        self.assertEqual(newer_template_2.name, 'My Copy', 'Copy should respect given default')
        # linked to their respective template
        self.assertEqual(newer_template.attachment_ids.mapped('res_id'), newer_template.ids * 2)
        self.assertEqual(newer_template_2.attachment_ids.mapped('res_id'), newer_template_2.ids * 2)
        self.assertEqual(newer_template.attachment_ids.mapped('res_model'), [newer_template._name] * 2)
        self.assertEqual(newer_template.attachment_ids.mapped('res_id'), newer_template.ids * 2)
        self.assertEqual(newer_template.attachment_ids.mapped('res_model'), [newer_template._name] * 2)
        self.assertEqual(original_attachments.mapped('res_id'), self.mail_template.ids * 2)
        self.assertEqual(original_attachments.mapped('res_model'), [self.mail_template._name] * 2)

    def test_mail_template_parse_partner_to(self):
        for partner_to, expected in [
            ('1', [1]),
            ('1,2,3', [1, 2, 3]),
            ('1, 2,  3', [1, 2, 3]),  # remove spaces
            ('[1, 2, 3]', [1, 2, 3]),  # %r of a list
            ('(1, 2, 3)', [1, 2, 3]),  # %r of a tuple
            ('1,[],2,"3"', [1, 2, 3]),  # type tolerant
            ('(1, "wrong", 2, "partner_name", "3")', [1, 2, 3]),  # fault tolerant
            ('res.partner(1, 2, 3)', [2]),  # invalid input but avoid crash
        ]:
            with self.subTest(partner_to=partner_to):
                parsed = self.mail_template._parse_partner_to(partner_to)
                self.assertListEqual(parsed, expected)

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


@tagged('mail_template')
class TestMailTemplateReset(MailCommon):

    def _load(self, module, filepath):
        # pylint: disable=no-value-for-parameter
        convert_file(self.env, module='mail',
                     filename=filepath,
                     idref={}, mode='init', noupdate=False)

    def test_mail_template_reset(self):
        self._load('mail', 'tests/test_mail_template.xml')

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

    def test_mail_template_reset_translation(self):
        """ Test if a translated value can be reset correctly when its translation exists/doesn't exist in the po file of the directory """
        self._load('mail', 'tests/test_mail_template.xml')

        self.env['res.lang']._activate_lang('en_GB')
        self.env['res.lang']._activate_lang('fr_FR')
        mail_template = self.env.ref('mail.mail_template_test').with_context(lang='en_US')
        mail_template.write({
            'body_html': '<div>Hello</div>',
            'name': 'Mail: Mail Template',
        })

        mail_template.with_context(lang='en_GB').write({
            'body_html': '<div>Hello UK</div>',
            'name': 'Mail: Mail Template UK',
        })

        context = {'default_template_ids': mail_template.ids, 'lang': 'fr_FR'}

        def fake_load_file(translation_importer, filepath, lang, xmlids=None):
            """ a fake load file to mimic the use case when
            translations for fr_FR exist in the fr.po of the directory and
            no en.po in the directory
            """
            if lang == 'fr_FR':  # fr_FR has translations
                translation_importer.model_translations['mail.template'] = {
                    'body_html': {'mail.mail_template_test': {'fr_FR': '<div>Hello Odoo FR</div>'}},
                    'name':  {'mail.mail_template_test': {'fr_FR': "Mail: Test Mail Template FR"}},
                }

        with patch('odoo.tools.translate.TranslationImporter.load_file', fake_load_file):
            mail_template_reset = self.env['mail.template.reset'].with_context(context).create({})
            reset_action = mail_template_reset.reset_template()
        self.assertTrue(reset_action)

        self.assertEqual(mail_template.body_html.strip(), Markup('<div>Hello Odoo</div>'))
        self.assertEqual(mail_template.with_context(lang='en_GB').body_html.strip(), Markup('<div>Hello Odoo</div>'))
        self.assertEqual(mail_template.with_context(lang='fr_FR').body_html.strip(), Markup('<div>Hello Odoo FR</div>'))

        self.assertEqual(mail_template.name, 'Mail: Test Mail Template')
        self.assertEqual(mail_template.with_context(lang='en_GB').name, 'Mail: Test Mail Template')
        self.assertEqual(mail_template.with_context(lang='fr_FR').name, 'Mail: Test Mail Template FR')


@tagged("mail_template", "-at_install", "post_install")
class TestMailTemplateUI(HttpCase):

    def test_mail_template_dynamic_placeholder_tour(self):
        # keep debug for technical fields visibility
        self.start_tour('/odoo?debug=1', 'mail_template_dynamic_placeholder_tour', login='admin')


@tagged("mail_template", "-at_install", "post_install")
class TestTemplateConfigRestrictEditor(MailCommon):

    def test_switch_icp_value(self):
        # Sanity check
        group = self.env.ref('mail.group_mail_template_editor')

        self.assertTrue(self.user_employee.has_group('mail.group_mail_template_editor'))
        self.assertFalse(self.user_employee.has_group('base.group_system'))

        # Check that the group is on the user via the settings configuration and not that
        # the right has been added specifically to this person.
        self.assertIn(group, self.user_employee.all_group_ids)
        self.assertNotIn(group, self.user_employee.group_ids)

        self.env['ir.config_parameter'].set_param('mail.restrict.template.rendering', True)
        self.assertFalse(self.user_employee.has_group('mail.group_mail_template_editor'))

        self.env['ir.config_parameter'].set_param('mail.restrict.template.rendering', False)
        self.assertTrue(self.user_employee.has_group('mail.group_mail_template_editor'))


@tagged("mail_template", "-at_install", "post_install")
class TestSearchTemplateCategory(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        MailTemplate = cls.env['mail.template'].with_context(active_test=False)
        ModelData = cls.env['ir.model.data']

        cls.existing = MailTemplate.search([])

        # Create templates
        # 2 Hidden templates
        cls.hidden_templates = MailTemplate.create([
            {'name': 'Hidden Template 1', 'active': False},
            {'name': 'Hidden Template 2', 'description': ''},
        ])
        last = cls.hidden_templates[-1]
        ModelData.create({
            'name': f'mail_template_{last.id}',
            'module': 'test_module',
            'model': 'mail.template',
            'res_id': last.id
        })

        # 5 Custom templates
        cls.custom_templates = MailTemplate.create([
            {'name': f'Custom Template {i + 1}', 'description': f'Desc {i + 1}'}
            for i in range(4)
        ])
        cls.custom_templates |= MailTemplate.create({'name': 'Custom Template empty', 'description': ''})

        # 4 Base templates with XML ID
        cls.base_templates = MailTemplate.create([
            {'name': f'Base Template {i + 1}', 'description': f'Desc Base {i + 1}'}
            for i in range(4)
        ])

        for template in cls.base_templates:
            ModelData.create({
                'name': f'mail_template_{template.id}',
                'module': 'test_module',
                'model': 'mail.template',
                'res_id': template.id
            })

    @users('employee')
    def test_search_template_category(self):
        MailTemplate = self.env['mail.template'].with_context(active_test=False)

        # Search by hidden templates
        hidden_domain = [('template_category', 'in', ['hidden_template'])]
        hidden_templates = MailTemplate.search(hidden_domain) - self.existing
        self.assertEqual(len(hidden_templates), len(self.hidden_templates), "Hidden templates count mismatch")
        self.assertEqual(set(hidden_templates.mapped('template_category')), {'hidden_template'}, "Computed field doesn't match 'hidden_template'")

        # Search by base templates
        base_domain = [('template_category', 'in', ['base_template'])]
        base_templates = MailTemplate.search(base_domain) - self.existing
        self.assertEqual(len(base_templates), len(self.base_templates), "Base templates count mismatch")
        self.assertEqual(set(base_templates.mapped('template_category')), {'base_template'}, "Computed field doesn't match 'base_template'")

        # Search by custom templates
        custom_domain = [('template_category', 'in', ['custom_template'])]
        custom_templates = MailTemplate.search(custom_domain) - self.existing
        self.assertEqual(len(custom_templates), len(self.custom_templates), "Custom templates count mismatch")
        self.assertEqual(set(custom_templates.mapped('template_category')), {'custom_template'}, "Computed field doesn't match 'custom_template'")

        # Combined search
        combined_domain = [('template_category', 'in', ['hidden_template', 'base_template', 'custom_template'])]
        combined_templates = MailTemplate.search(combined_domain) - self.existing
        total_templates = len(self.hidden_templates) + len(self.base_templates) + len(self.custom_templates)
        self.assertEqual(len(combined_templates), total_templates, "Combined templates count mismatch")

        # Search with '=' operator
        hidden_domain = [('template_category', '=', 'hidden_template')]
        hidden_templates = MailTemplate.search(hidden_domain) - self.existing
        self.assertEqual(len(hidden_templates), len(self.hidden_templates), "Hidden templates count mismatch")

        # Search with '!=' operator
        not_in_domain = [('template_category', '!=', 'hidden_template')]
        not_in_templates = MailTemplate.search(not_in_domain) - self.existing
        expected_templates = len(self.base_templates) + len(self.custom_templates)
        self.assertEqual(len(not_in_templates), expected_templates, "Not in templates count mismatch")

        # Search with 'not in' operator
        not_in_domain = [('template_category', 'not in', ['hidden_template'])]
        not_in_templates = MailTemplate.search(not_in_domain) - self.existing
        expected_templates = len(self.base_templates) + len(self.custom_templates)
        self.assertEqual(len(not_in_templates), expected_templates, "Not in templates count mismatch")

        # Search with 'not in' operator
        not_in_domain = [('template_category', 'not in', ['hidden_template', 'base_template'])]
        not_in_templates = MailTemplate.search(not_in_domain) - self.existing
        expected_templates = len(self.custom_templates)
        self.assertEqual(len(not_in_templates), expected_templates, "Not in multi templates count mismatch")
