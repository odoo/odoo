# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from markupsafe import Markup
from unittest.mock import patch

from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.tests import Form, HttpCase, tagged, users
from odoo.tools import convert_file


@tagged('mail_template')
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

        values = mail_compose_message._prepare_mail_values(self.partner_employee.ids)

        self.assertEqual(values[self.partner_employee.id]['subject'], '6', 'We must trust mail template values')
        self.assertIn('13', values[self.partner_employee.id]['body_html'], 'We must trust mail template values')

    @users('admin')
    def test_mail_template_abstract_model(self):
        """Check abstract models cannot be set on templates."""
        # create
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['mail.template'].create({
                'name': 'Test abstract template',
                'model_id': self.env['ir.model']._get('mail.thread').id, # abstract model
            })
        # write
        template = self.env['mail.template'].create({
            'name': 'Test abstract template',
            'model_id': self.env['ir.model']._get('res.partner').id,
        })
        with self.assertRaises(ValidationError), self.cr.savepoint():
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

        model = self.env['ir.model']._get_id('res.partner')
        record = self.user_employee.partner_id

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
            'password',
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
            '<p t-call="template"></p>',
            '<p t-cache="object.name"></p>',
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

            with (patch('odoo.addons.base.models.ir_qweb.IrQWeb._render', side_effect=o_qweb_render) as qweb_render,
                patch('odoo.addons.base.models.ir_qweb.unsafe_eval', side_effect=eval) as unsafe_eval):
                rendered = template._render_field('body_html', record.ids)[record.id]
                self.assertNotIn('t-out', rendered)
                self.assertFalse(qweb_render.called)
                self.assertFalse(unsafe_eval.called)

        # double check that we can detect the qweb rendering
        mail_template.body_html = '<t t-out="1+1"/>'
        with (patch('odoo.addons.base.models.ir_qweb.IrQWeb._render', side_effect=o_qweb_render) as qweb_render,
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
            employee_template.with_context(lang='fr_FR').subject = '{{ object.foo }}'

        employee_template.with_context(lang='fr_FR').sudo().subject = '{{ object.foo }}'

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
                     idref={}, mode='init', noupdate=False, kind='test')

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
        self.start_tour("/odoo", 'mail_template_dynamic_placeholder_tour', login="admin")


@tagged("mail_template", "-at_install", "post_install")
class TestTemplateConfigRestrictEditor(MailCommon):

    def test_switch_icp_value(self):
        # Sanity check
        self.assertTrue(self.user_employee.has_group('mail.group_mail_template_editor'))
        self.assertFalse(self.user_employee.has_group('base.group_system'))

        self.env['ir.config_parameter'].set_param('mail.restrict.template.rendering', True)
        self.assertFalse(self.user_employee.has_group('mail.group_mail_template_editor'))

        self.env['ir.config_parameter'].set_param('mail.restrict.template.rendering', False)
        self.assertTrue(self.user_employee.has_group('mail.group_mail_template_editor'))


@tagged("mail_template", "-at_install", "post_install")
class TestSearchTemplateCategory(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mail_template = cls.env['mail.template'].with_context(active_test=False)
        cls.model_data = cls.env['ir.model.data']

        cls.existing = cls.mail_template.search([])

        # Create templates
        # 2 Hidden templates
        cls.hidden_templates = cls.mail_template.create([
            {'name': 'Hidden Template 1', 'active': False},
            {'name': 'Hidden Template 2', 'description': ''},
        ])
        last = cls.hidden_templates[-1]
        cls.model_data.create({
            'name': f'mail_template_{last.id}',
            'module': 'test_module',
            'model': 'mail.template',
            'res_id': last.id
        })

        # 5 Custom templates
        cls.custom_templates = cls.mail_template.create([
            {'name': f'Custom Template {i + 1}', 'description': f'Desc {i + 1}'}
            for i in range(4)
        ])
        cls.custom_templates |= cls.mail_template.create({'name': 'Custom Template empty', 'description': ''})

        # 4 Base templates with XML ID
        cls.base_templates = cls.mail_template.create([
            {'name': f'Base Template {i + 1}', 'description': f'Desc Base {i + 1}'}
            for i in range(4)
        ])

        for template in cls.base_templates:
            cls.model_data.create({
                'name': f'mail_template_{template.id}',
                'module': 'test_module',
                'model': 'mail.template',
                'res_id': template.id
            })

    def test_search_template_category(self):

        # Search by hidden templates
        hidden_domain = [('template_category', 'in', ['hidden_template'])]
        hidden_templates = self.mail_template.search(hidden_domain) - self.existing
        self.assertEqual(len(hidden_templates), len(self.hidden_templates), "Hidden templates count mismatch")
        self.assertEqual(set(hidden_templates.mapped('template_category')), {'hidden_template'}, "Computed field doesn't match 'hidden_template'")

        # Search by base templates
        base_domain = [('template_category', 'in', ['base_template'])]
        base_templates = self.mail_template.search(base_domain) - self.existing
        self.assertEqual(len(base_templates), len(self.base_templates), "Base templates count mismatch")
        self.assertEqual(set(base_templates.mapped('template_category')), {'base_template'}, "Computed field doesn't match 'base_template'")

        # Search by custom templates
        custom_domain = [('template_category', 'in', ['custom_template'])]
        custom_templates = self.mail_template.search(custom_domain) - self.existing
        self.assertEqual(len(custom_templates), len(self.custom_templates), "Custom templates count mismatch")
        self.assertEqual(set(custom_templates.mapped('template_category')), {'custom_template'}, "Computed field doesn't match 'custom_template'")

        # Combined search
        combined_domain = [('template_category', 'in', ['hidden_template', 'base_template', 'custom_template'])]
        combined_templates = self.mail_template.search(combined_domain) - self.existing
        total_templates = len(self.hidden_templates) + len(self.base_templates) + len(self.custom_templates)
        self.assertEqual(len(combined_templates), total_templates, "Combined templates count mismatch")

        # Search with '=' operator
        hidden_domain = [('template_category', '=', 'hidden_template')]
        hidden_templates = self.mail_template.search(hidden_domain) - self.existing
        self.assertEqual(len(hidden_templates), len(self.hidden_templates), "Hidden templates count mismatch")

        # Search with '!=' operator
        not_in_domain = [('template_category', '!=', 'hidden_template')]
        not_in_templates = self.mail_template.search(not_in_domain) - self.existing
        expected_templates = len(self.base_templates) + len(self.custom_templates)
        self.assertEqual(len(not_in_templates), expected_templates, "Not in templates count mismatch")

        # Search with 'not in' operator
        not_in_domain = [('template_category', 'not in', ['hidden_template'])]
        not_in_templates = self.mail_template.search(not_in_domain) - self.existing
        expected_templates = len(self.base_templates) + len(self.custom_templates)
        self.assertEqual(len(not_in_templates), expected_templates, "Not in templates count mismatch")

        # Search with 'not in' operator
        not_in_domain = [('template_category', 'not in', ['hidden_template', 'base_template'])]
        not_in_templates = self.mail_template.search(not_in_domain) - self.existing
        expected_templates = len(self.custom_templates)
        self.assertEqual(len(not_in_templates), expected_templates, "Not in multi templates count mismatch")
