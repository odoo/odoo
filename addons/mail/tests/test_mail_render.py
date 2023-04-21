# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo.addons.mail.tests import common
from odoo.exceptions import AccessError
from odoo.tests import tagged, users


class TestMailRenderCommon(common.MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailRenderCommon, cls).setUpClass()

        # activate multi language support
        cls.env['res.lang']._activate_lang('fr_FR')
        cls.user_admin.write({'lang': 'en_US'})

        # test records
        cls.render_object = cls.env['res.partner'].create({
            'name': 'TestRecord',
            'lang': 'en_US',
        })
        cls.render_object_fr = cls.env['res.partner'].create({
            'name': 'Element de Test',
            'lang': 'fr_FR',
        })

        # some jinja templates
        cls.base_inline_template_bits = [
            '<p>Hello</p>',
            '<p>Hello {{ object.name }}</p>',
            """<p>
    {{ '<span>English Speaker</span>' if object.lang == 'en_US' else '<span>Other Speaker</span>' }}
</p>""",
            """
            <p>{{ 13 + 13 }}</p>
            <h1>This is a test</h1>
            """,
            """<b>Test</b>{{ '' if True else '<b>Code not executed</b>' }}""",
        ]
        cls.base_inline_template_bits_fr = [
            '<p>Bonjour</p>',
            '<p>Bonjour {{ object.name }}</p>',
            """<p>
    {{ '<span>Narrateur Anglais</span>' if object.lang == 'en_US' else '<span>Autre Narrateur</span>' }}
</p>"""
        ]

        # some qweb templates, their views and their xml ids
        cls.base_qweb_bits = [
            '<p>Hello</p>',
            '<p>Hello <t t-esc="object.name"/></p>',
            """<p>
    <span t-if="object.lang == 'en_US'">English Speaker</span>
    <span t-else="">Other Speaker</span>
</p>"""
        ]
        cls.base_qweb_bits_fr = [
            '<p>Bonjour</p>',
            '<p>Bonjour <t t-esc="object.name"/></p>',
            """<p>
    <span t-if="object.lang == 'en_US'">Narrateur Anglais</span>
    <span t-else="">Autre Narrateur</span>
</p>"""
        ]
        cls.base_qweb_templates = cls.env['ir.ui.view'].create([
            {'name': 'TestRender%d' % index,
             'type': 'qweb',
             'arch': qweb_content,
            } for index, qweb_content in enumerate(cls.base_qweb_bits)
        ])
        cls.base_qweb_templates_data = cls.env['ir.model.data'].create([
            {'name': template.name, 'module': 'mail',
             'model': template._name, 'res_id': template.id,
            } for template in cls.base_qweb_templates
        ])
        cls.base_qweb_templates_xmlids = [
            model_data.complete_name
            for model_data in cls.base_qweb_templates_data
        ]

        # render result
        cls.base_rendered = [
            '<p>Hello</p>',
            '<p>Hello %s</p>' % cls.render_object.name,
            """<p>
    <span>English Speaker</span>
</p>"""
        ]
        cls.base_rendered_fr = [
            '<p>Bonjour</p>',
            '<p>Bonjour %s</p>' % cls.render_object_fr.name,
            """<p>
    <span>Autre Narrateur</span>
</p>"""
        ]

        # link to mail template
        cls.test_template = cls.env['mail.template'].create({
            'name': 'Test Template',
            'subject': cls.base_inline_template_bits[0],
            'body_html': cls.base_qweb_bits[1],
            'model_id': cls.env['ir.model']._get('res.partner').id,
            'lang': '{{ object.lang }}'
        })

        # some translations
        cls.test_template.with_context(lang='fr_FR').subject = cls.base_qweb_bits_fr[0]
        cls.test_template.with_context(lang='fr_FR').body_html = cls.base_qweb_bits_fr[1]

        cls.env['ir.model.data'].create({
            'name': 'test_template_xmlid',
            'module': 'mail',
            'model': cls.test_template._name,
            'res_id': cls.test_template.id,
        })

        # Enable group-based template management
        cls.env['ir.config_parameter'].set_param('mail.restrict.template.rendering', True)

        # User without the group "mail.group_mail_template_editor"
        cls.user_rendering_restricted = common.mail_new_test_user(
            cls.env, login='user_rendering_restricted',
            groups='base.group_user',
            company_id=cls.company_admin.id,
            name='Code Template Restricted User',
            notification_type='inbox',
            signature='--\nErnest'
        )
        cls.user_rendering_restricted.groups_id -= cls.env.ref('mail.group_mail_template_editor')
        cls.user_employee.groups_id += cls.env.ref('mail.group_mail_template_editor')


@tagged('mail_render')
class TestMailRender(TestMailRenderCommon):

    @users('employee')
    def test_evaluation_context(self):
        """ Test evaluation context and various ways of tweaking it. """
        partner = self.env['res.partner'].browse(self.render_object.ids)
        MailRenderMixin = self.env['mail.render.mixin']

        custom_ctx = {'custom_ctx': 'Custom Context Value'}
        add_context = {
            'custom_value': 'Custom Render Value'
        }
        srces = [
            '<b>I am {{ user.name }}</b>',
            '<span>Datetime is {{ format_datetime(datetime.datetime(2021, 6, 1), dt_format="MM - d - YYY") }}</span>',
            '<span>Context {{ ctx.get("custom_ctx") }}, value {{ custom_value }}</span>',
        ]
        results = [
            '<b>I am %s</b>' % self.env.user.name,
            '<span>Datetime is 06 - 1 - 2021</span>',
            '<span>Context Custom Context Value, value Custom Render Value</span>'
        ]
        for src, expected in zip(srces, results):
            for engine in ['inline_template']:
                result = MailRenderMixin.with_context(**custom_ctx)._render_template(
                    src, partner._name, partner.ids,
                    engine=engine, add_context=add_context
                )[partner.id]
                self.assertEqual(expected, result)

    @users('employee')
    def test_prepend_preview_inline_template_to_qweb(self):
        body = 'body'
        preview = 'foo{{"false" if 1 > 2 else "true"}}bar'
        result = self.env['mail.render.mixin']._prepend_preview(Markup(body), preview)
        self.assertEqual(result, '''<div style="display:none;font-size:1px;height:0px;width:0px;opacity:0;">
                    foo<t t-out="&#34;false&#34; if 1 &gt; 2 else &#34;true&#34;"/>bar
                </div>body''')

    @users('employee')
    def test_render_field(self):
        template = self.env['mail.template'].browse(self.test_template.ids)
        partner = self.env['res.partner'].browse(self.render_object.ids)
        for fname, expected in zip(['subject', 'body_html'], self.base_rendered):
            rendered = template._render_field(
                fname,
                partner.ids,
                compute_lang=True
            )[partner.id]
            self.assertEqual(rendered, expected)

    @users('employee')
    def test_render_field_lang(self):
        """ Test translation in french """
        template = self.env['mail.template'].browse(self.test_template.ids)
        partner = self.env['res.partner'].browse(self.render_object_fr.ids)
        for fname, expected in zip(['subject', 'body_html'], self.base_rendered_fr):
            rendered = template._render_field(
                fname,
                partner.ids,
                compute_lang=True
            )[partner.id]
            self.assertEqual(rendered, expected)

    @users('employee')
    def test_render_template_inline_template(self):
        partner = self.env['res.partner'].browse(self.render_object.ids)
        for source, expected in zip(self.base_inline_template_bits, self.base_rendered):
            rendered = self.env['mail.render.mixin']._render_template(
                source,
                partner._name,
                partner.ids,
                engine='inline_template',
            )[partner.id]
            self.assertEqual(rendered, expected)

    @users('employee')
    def test_render_template_qweb(self):
        partner = self.env['res.partner'].browse(self.render_object.ids)
        for source, expected in zip(self.base_qweb_bits, self.base_rendered):
            rendered = self.env['mail.render.mixin']._render_template(
                source,
                partner._name,
                partner.ids,
                engine='qweb',
            )[partner.id]
            self.assertEqual(rendered, expected)

    @users('employee')
    def test_render_template_qweb_view(self):
        partner = self.env['res.partner'].browse(self.render_object.ids)
        for source, expected in zip(self.base_qweb_templates_xmlids, self.base_rendered):
            rendered = self.env['mail.render.mixin']._render_template(
                source,
                partner._name,
                partner.ids,
                engine='qweb_view',
            )[partner.id]
            self.assertEqual(rendered, expected)

    @users('employee')
    def test_render_template_various(self):
        """ Test static rendering """
        partner = self.env['res.partner'].browse(self.render_object.ids)
        MailRenderMixin = self.env['mail.render.mixin']

        # static string
        src = 'This is a string'
        expected = 'This is a string'
        for engine in ['inline_template']:
            result = MailRenderMixin._render_template(
                src, partner._name, partner.ids, engine=engine,
            )[partner.id]
            self.assertEqual(expected, result)

        # code string
        src = 'This is a string with a number {{ 13+13 }}'
        expected = 'This is a string with a number 26'
        for engine in ['inline_template']:
            result = MailRenderMixin._render_template(
                src, partner._name, partner.ids, engine=engine,
            )[partner.id]
            self.assertEqual(expected, result)

        # block string
        src = "This is a string with a block {{ 'hidden' if False else 'displayed' }}"
        expected = 'This is a string with a block displayed'
        for engine in ['inline_template']:
            result = MailRenderMixin._render_template(
                src, partner._name, partner.ids, engine=engine,
            )[partner.id]
            self.assertEqual(expected, result)

        # static xml
        src = '<p class="text-muted"><span>This is a string</span></p>'
        expected = '<p class="text-muted"><span>This is a string</span></p>'
        for engine in ['inline_template', 'qweb']:
            result = MailRenderMixin._render_template(
                src, partner._name, partner.ids, engine=engine,
            )[partner.id]
            self.assertEqual(expected, result)  # tde: checkme

        # code xml
        srces = [
            '<p class="text-muted"><span>This is a string with a number {{ 13+13 }}</span></p>',
            '<p class="text-muted"><span>This is a string with a number <t t-out="13+13"/></span></p>',
        ]
        expected = '<p class="text-muted"><span>This is a string with a number 26</span></p>'
        for engine, src in zip(['inline_template', 'qweb'], srces):
            result = MailRenderMixin._render_template(
                src, partner._name, partner.ids, engine=engine,
            )[partner.id]
            self.assertEqual(expected, str(result))
        src = """<p>
<t t-set="line_statement_variable" t-value="3" />
<span>We have <t t-out="line_statement_variable" /> cookies in stock</span>
<span>We have <t t-set="block_variable" t-value="4" /><t t-out="block_variable" /> cookies in stock</span>
</p>"""
        expected = """<p>
<span>We have 3 cookies in stock</span>
<span>We have 4 cookies in stock</span>
</p>"""
        for engine in ['qweb']:
            result = MailRenderMixin._render_template(
                src, partner._name, partner.ids, engine=engine,
            )[partner.id]
            self.assertEqual(result, expected)

    @users('employee')
    def test_replace_local_links(self):
        local_links_template_bits = [
            '<div style="background-image:url(/web/path?a=a&b=b);"/>',
            '<div style="background-image:url(\'/web/path?a=a&b=b\');"/>',
            '<div style="background-image:url(&#34;/web/path?a=a&b=b&#34;);"/>',
        ]
        base_url = self.env['mail.render.mixin'].get_base_url()
        rendered_local_links = [
            '<div style="background-image:url(%s/web/path?a=a&b=b);"/>' % base_url,
            '<div style="background-image:url(\'%s/web/path?a=a&b=b\');"/>' % base_url,
            '<div style="background-image:url(&#34;%s/web/path?a=a&b=b&#34;);"/>' % base_url
        ]
        for source, expected in zip(local_links_template_bits, rendered_local_links):
            rendered = self.env['mail.render.mixin']._replace_local_links(source)
            self.assertEqual(rendered, expected)


@tagged('mail_render')
class TestMailRenderSecurity(TestMailRenderCommon):
    """ Test security of rendering, based on qweb finding + restricted rendering
    group usage. """

    @users('employee')
    def test_render_inline_template_impersonate(self):
        """ Test that the use of SUDO do not change the current user. """
        partner = self.env['res.partner'].browse(self.render_object.ids)
        src = '{{ user.name }} - {{ object.name }}'
        expected = '%s - %s' % (self.env.user.name, partner.name)
        result = self.env['mail.render.mixin'].sudo()._render_template_inline_template(
            src, partner._name, partner.ids
        )[partner.id]
        self.assertIn(expected, result)

    @users('user_rendering_restricted')
    def test_render_inline_template_restricted(self):
        """Test if we correctly detect static template."""
        res_ids = self.env['res.partner'].search([], limit=1).ids
        with self.assertRaises(AccessError, msg='Simple user should not be able to render dynamic code'):
            self.env['mail.render.mixin']._render_template_inline_template(
                self.base_inline_template_bits[3],
                'res.partner',
                res_ids
            )

        src = """<h1>This is a static template</h1>"""
        result = self.env['mail.render.mixin']._render_template_inline_template(
            src,
            'res.partner',
            res_ids
        )[res_ids[0]]
        self.assertEqual(src, str(result))

    @users('user_rendering_restricted')
    def test_render_inline_template_restricted_static(self):
        """Test that we render correctly static templates (without placeholders)."""
        model = 'res.partner'
        res_ids = self.env[model].search([], limit=1).ids
        MailRenderMixin = self.env['mail.render.mixin']

        result = MailRenderMixin._render_template_inline_template(
            self.base_inline_template_bits[0],
            model,
            res_ids
        )[res_ids[0]]
        self.assertEqual(result, self.base_inline_template_bits[0])

    @users('employee')
    def test_render_inline_template_unrestricted(self):
        """ Test if we correctly detect static template. """
        res_ids = self.env['res.partner'].search([], limit=1).ids
        result = self.env['mail.render.mixin']._render_template_inline_template(
            self.base_inline_template_bits[3],
            'res.partner',
            res_ids
        )[res_ids[0]]
        self.assertIn('26', result, 'Template Editor should be able to render inline_template code')

    @users('user_rendering_restricted')
    def test_render_template_qweb_restricted(self):
        model = 'res.partner'
        res_ids = self.env[model].search([], limit=1).ids
        partner = self.env[model].browse(res_ids)

        src = """<h1>This is a static template</h1>"""

        result = self.env['mail.render.mixin']._render_template_qweb(src, model, res_ids)[
            partner.id]
        self.assertEqual(src, str(result))

    @users('user_rendering_restricted')
    def test_security_function_call(self):
        """Test the case when the template call a custom function.

        This function should not be called when the template is not rendered.
        """
        model = 'res.partner'
        res_ids = self.env[model].search([], limit=1).ids
        partner = self.env[model].browse(res_ids)
        MailRenderMixin = self.env['mail.render.mixin']

        def cust_function():
            # Can not use "MagicMock" in a Jinja sand-boxed environment
            # so create our own function
            cust_function.call = True
            return 'return value'

        cust_function.call = False

        src = """<h1>This is a test</h1>
<p>{{ cust_function() }}</p>"""
        expected = """<h1>This is a test</h1>
<p>return value</p>"""
        context = {'cust_function': cust_function}

        result = self.env['mail.render.mixin'].with_user(self.user_admin)._render_template_inline_template(
            src, partner._name, partner.ids,
            add_context=context
        )[partner.id]
        self.assertEqual(expected, result)
        self.assertTrue(cust_function.call)

        with self.assertRaises(AccessError, msg='Simple user should not be able to render dynamic code'):
            MailRenderMixin._render_template_inline_template(src, model, res_ids, add_context=context)

    @users('user_rendering_restricted')
    def test_security_inline_template_restricted(self):
        """Test if we correctly detect condition block (which might contains code)."""
        res_ids = self.env['res.partner'].search([], limit=1).ids
        with self.assertRaises(AccessError, msg='Simple user should not be able to render dynamic code'):
            self.env['mail.render.mixin']._render_template_inline_template(self.base_inline_template_bits[4], 'res.partner', res_ids)

    @users('employee')
    def test_security_inline_template_unrestricted(self):
        """Test if we correctly detect condition block (which might contains code)."""
        res_ids = self.env['res.partner'].search([], limit=1).ids
        result = self.env['mail.render.mixin']._render_template_inline_template(self.base_inline_template_bits[4], 'res.partner', res_ids)[res_ids[0]]
        self.assertNotIn('Code not executed', result, 'The condition block did not work')

    @users('user_rendering_restricted')
    def test_security_qweb_template_restricted(self):
        """Test if we correctly detect condition block (which might contains code)."""
        res_ids = self.env['res.partner'].search([], limit=1).ids
        with self.assertRaises(AccessError, msg='Simple user should not be able to render qweb code'):
            self.env['mail.render.mixin']._render_template_qweb(self.base_qweb_bits[1], 'res.partner', res_ids)

    @users('user_rendering_restricted')
    def test_security_qweb_template_restricted_cached(self):
        """Test if we correctly detect condition block (which might contains code)."""
        res_ids = self.env['res.partner'].search([], limit=1).ids

        # Render with the admin first to fill the cache
        self.env['mail.render.mixin'].with_user(self.user_admin)._render_template_qweb(
            self.base_qweb_bits[1], 'res.partner', res_ids)

        # Check that it raise even when rendered previously by an admin
        with self.assertRaises(AccessError, msg='Simple user should not be able to render qweb code'):
            self.env['mail.render.mixin']._render_template_qweb(
                self.base_qweb_bits[1], 'res.partner', res_ids)

    @users('employee')
    def test_security_qweb_template_unrestricted(self):
        """Test if we correctly detect condition block (which might contains code)."""
        res_ids = self.env['res.partner'].search([], limit=1).ids
        result = self.env['mail.render.mixin']._render_template_qweb(self.base_qweb_bits[1], 'res.partner', res_ids)[res_ids[0]]
        self.assertNotIn('Code not executed', result, 'The condition block did not work')
