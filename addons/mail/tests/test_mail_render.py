# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests import common
from odoo.tests import tagged, users


@tagged('mail_render')
class TestMailRender(common.MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailRender, cls).setUpClass()

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
        cls.base_jinja_bits = [
            '<p>Hello</p>',
            '<p>Hello ${object.name}</p>',
            """<p>
% set english = object.lang == 'en_US'
% if english
    <span>English Speaker</span>
% else
    <span>Other Speaker</span>
% endif
</p>"""
        ]
        cls.base_jinja_bits_fr = [
            '<p>Bonjour</p>',
            '<p>Bonjour ${object.name}</p>',
            """<p>
% set english = object.lang == 'en_US'
% if english
    <span>Narrateur Anglais</span>
% else
    <span>Autre Narrateur</span>
% endif
</p>"""
        ]

        # some qweb templates and their xml ids
        cls.base_qweb_templates = cls.env['ir.ui.view'].create([
            {'name': 'TestRender', 'type': 'qweb',
             'arch': '<p>Hello</p>',
            },
            {'name': 'TestRender2', 'type': 'qweb',
             'arch': '<p>Hello <t t-esc="object.name"/></p>',
            },
            {'name': 'TestRender3', 'type': 'qweb',
             'arch': """<p>
    <span t-if="object.lang == 'en_US'">English Speaker</span>
    <span t-else="">Other Speaker</span>
</p>""",
            },
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
        cls.test_template_jinja = cls.env['mail.template'].create({
            'name': 'Test Template',
            'subject': cls.base_jinja_bits[0],
            'body_html': cls.base_jinja_bits[1],
            'model_id': cls.env['ir.model']._get('res.partner').id,
            'lang': '${object.lang}'
        })

        # some translations
        cls.env['ir.translation'].create({
            'type': 'model',
            'name': 'mail.template,subject',
            'lang': 'fr_FR',
            'res_id': cls.test_template_jinja.id,
            'src': cls.test_template_jinja.subject,
            'value': cls.base_jinja_bits_fr[0],
        })
        cls.env['ir.translation'].create({
            'type': 'model',
            'name': 'mail.template,body_html',
            'lang': 'fr_FR',
            'res_id': cls.test_template_jinja.id,
            'src': cls.test_template_jinja.body_html,
            'value': cls.base_jinja_bits_fr[1],
        })
        cls.env['ir.model.data'].create({
            'name': 'test_template_xmlid',
            'module': 'mail',
            'model': cls.test_template_jinja._name,
            'res_id': cls.test_template_jinja.id,
        })

    @users('employee')
    def test_render_jinja(self):
        source = """<p>
% set line_statement_variable = 3
<span>We have ${line_statement_variable} cookies in stock</span>
<span>We have <% set block_variable = 4 %>${block_variable} cookies in stock</span>
</p>"""
        partner = self.env['res.partner'].browse(self.render_object.ids)
        result = self.env['mail.render.mixin']._render_template(
            source,
            partner._name,
            partner.ids,
            engine='jinja',
        )[partner.id]
        self.assertEqual(result, """<p>
<span>We have 3 cookies in stock</span>
<span>We have 4 cookies in stock</span>
</p>""")

    @users('employee')
    def test_render_mail_template_jinja(self):
        template = self.env['mail.template'].browse(self.test_template_jinja.ids)
        partner = self.env['res.partner'].browse(self.render_object.ids)
        for fname, expected in zip(['subject', 'body_html'], self.base_rendered):
            rendered = template._render_field(
                fname,
                partner.ids,
                compute_lang=True
            )[partner.id]
            self.assertEqual(rendered, expected)

        partner = self.env['res.partner'].browse(self.render_object_fr.ids)
        for fname, expected in zip(['subject', 'body_html'], self.base_rendered_fr):
            rendered = template._render_field(
                fname,
                partner.ids,
                compute_lang=True
            )[partner.id]
            self.assertEqual(rendered, expected)

    @users('employee')
    def test_render_template_jinja(self):
        partner = self.env['res.partner'].browse(self.render_object.ids)
        for source, expected in zip(self.base_jinja_bits, self.base_rendered):
            rendered = self.env['mail.render.mixin']._render_template(
                source,
                partner._name,
                partner.ids,
                engine='jinja',
            )[partner.id]
            self.assertEqual(rendered, expected)

    @users('employee')
    def test_render_template_qweb(self):
        partner = self.env['res.partner'].browse(self.render_object.ids)
        for source, expected in zip(self.base_qweb_templates_xmlids, self.base_rendered):
            rendered = self.env['mail.render.mixin']._render_template(
                source,
                partner._name,
                partner.ids,
                engine='qweb',
            )[partner.id].decode()
            self.assertEqual(rendered, expected)
