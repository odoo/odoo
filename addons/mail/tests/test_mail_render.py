import base64
from unittest.mock import patch

from markupsafe import Markup

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import Form, tagged, users

from odoo.addons.mail.tests import common


class TestMailRenderCommon(common.MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env["res.lang"]._activate_lang("fr_FR")
        cls.user_admin.write({"lang": "en_US"})

        cls.render_object = cls.env["res.partner"].create(
            {
                "name": "TestRecord",
                "lang": "en_US",
            }
        )
        cls.render_object_fr = cls.env["res.partner"].create(
            {
                "name": "Element de Test",
                "lang": "fr_FR",
            }
        )

        cls.base_inline_template_bits = [
            "<p>Hello</p>",
            "<p>Hello {{ object.name }}</p>",
            """<p>
    {{ '<span>English Speaker</span>' if object.lang == 'en_US' else '<span>Other Speaker</span>' }}
</p>""",
            """
            <p>{{ 13 + 13 }}</p>
            <h1>This is a test</h1>
            """,
            """<b>Test</b>{{ '' if True else '<b>Code not executed</b>' }}""",
            """<b>Test</b> {{ '' ||| Bob }}""",
            """<b>Test</b> {{ '' ||| Bob }} |||""",
            """<b>Test</b> {{ '' ||| Bob }} ||| }}""",
        ]
        cls.base_inline_template_bits_fr = [
            "<p>Bonjour</p>",
            "<p>Bonjour {{ object.name }}</p>",
            """<p>
    {{ '<span>Narrateur Anglais</span>' if object.lang == 'en_US' else '<span>Autre Narrateur</span>' }}
</p>""",
        ]

        cls.base_qweb_bits = [
            "<p>Hello</p>",
            '<p>Hello <t t-esc="object.name"/></p>',
            """<p>
    <span t-if="object.lang == 'en_US'">English Speaker</span>
    <span t-else="">Other Speaker</span>
</p>""",
        ]
        cls.base_qweb_bits_fr = [
            "<p>Bonjour</p>",
            '<p>Bonjour <t t-esc="object.name"/></p>',
            """<p>
    <span t-if="object.lang == 'en_US'">Narrateur Anglais</span>
    <span t-else="">Autre Narrateur</span>
</p>""",
        ]
        cls.base_qweb_templates = cls.env["ir.ui.view"].create(
            [
                {
                    "name": "TestRender%d" % index,
                    "type": "qweb",
                    "arch": qweb_content,
                }
                for index, qweb_content in enumerate(cls.base_qweb_bits)
            ]
        )
        cls.base_qweb_templates_data = cls.env["ir.model.data"].create(
            [
                {
                    "name": template.name,
                    "module": "mail",
                    "model": template._name,
                    "res_id": template.id,
                }
                for template in cls.base_qweb_templates
            ]
        )
        cls.base_qweb_templates_xmlids = [
            model_data.complete_name for model_data in cls.base_qweb_templates_data
        ]

        cls.base_rendered = [
            "<p>Hello</p>",
            "<p>Hello %s</p>" % cls.render_object.name,
            """<p>
    <span>English Speaker</span>
</p>""",
            """
            <p>26</p>
            <h1>This is a test</h1>
            """,
            """<b>Test</b>""",
            """<b>Test</b> Bob """,
            """<b>Test</b> Bob  |||""",
            """<b>Test</b> Bob  ||| }}""",
        ]
        cls.base_rendered_fr = [
            "<p>Bonjour</p>",
            "<p>Bonjour %s</p>" % cls.render_object_fr.name,
            """<p>
    <span>Autre Narrateur</span>
</p>""",
        ]
        cls.base_rendered_void = [
            "<p>Hello</p>",
            "<p>Hello </p>",
            """<p>
    <span>English Speaker</span>
</p>""",
        ]

        cls.test_template = cls.env["mail.template"].create(
            {
                "name": "Test Template",
                "subject": cls.base_inline_template_bits[0],
                "body_html": cls.base_qweb_bits[1],
                "model_id": cls.env["ir.model"]._get("res.partner").id,
                "lang": "{{ object.lang }}",
                "use_default_to": True,
            }
        )

        cls.test_template.with_context(lang="fr_FR").subject = cls.base_qweb_bits_fr[0]
        cls.test_template.with_context(lang="fr_FR").body_html = cls.base_qweb_bits_fr[
            1
        ]

        cls.env["ir.model.data"].create(
            {
                "name": "test_template_xmlid",
                "module": "mail",
                "model": cls.test_template._name,
                "res_id": cls.test_template.id,
            }
        )

        cls.env["ir.config_parameter"].set_param(
            "mail.restrict.template.rendering", True
        )

        cls.user_rendering_restricted = common.mail_new_test_user(
            cls.env,
            login="user_rendering_restricted",
            groups="base.group_user",
            company_id=cls.company_admin.id,
            name="Code Template Restricted User",
            notification_type="inbox",
            signature="--\nErnest",
        )
        cls.env.ref("mail.group_mail_template_editor").write(
            {"implied_by_ids": [Command.clear()]}
        )
        cls.user_employee.group_ids += cls.env.ref("mail.group_mail_template_editor")


@tagged("mail_render")
class TestMailRender(TestMailRenderCommon):
    @users("employee")
    def test_evaluation_context(self):
        partner = self.env["res.partner"].browse(self.render_object.ids)
        MixinMailRender = self.env["mixin.mail.render"]

        custom_ctx = {"custom_ctx": "Custom Context Value"}
        add_context = {"custom_value": "Custom Render Value"}
        srces = [
            "<b>I am {{ user.name }}</b>",
            '<span>Datetime is {{ format_datetime(datetime.datetime(2021, 6, 1), dt_format="MM - d - YYY") }}</span>',
            '<span>Context {{ ctx.get("custom_ctx") }}, value {{ custom_value }}</span>',
        ]
        results = [
            "<b>I am %s</b>" % self.env.user.name,
            "<span>Datetime is 06 - 1 - 2021</span>",
            "<span>Context Custom Context Value, value Custom Render Value</span>",
        ]
        for src, expected in zip(srces, results, strict=False):
            for engine in ["inline_template"]:
                result = MixinMailRender.with_context(**custom_ctx)._render_template(
                    src,
                    partner._name,
                    partner.ids,
                    engine=engine,
                    add_context=add_context,
                )[partner.id]
                self.assertEqual(expected, result)

    @users("employee")
    def test_prepend_preview_inline_template_to_qweb(self):
        body = "body"
        preview = 'foo{{"false" if 1 > 2 else "true"}}bar'
        result = self.env["mixin.mail.render"]._prepend_preview(Markup(body), preview)
        self.assertEqual(
            result,
            """<div style="display:none;font-size:1px;height:0px;width:0px;opacity:0;">
                    foo<t t-out="&#34;false&#34; if 1 &gt; 2 else &#34;true&#34;"></t>bar
                </div>body""",
        )

    @users("employee")
    def test_render_field(self):
        template = self.env["mail.template"].browse(self.test_template.ids)
        partner = self.env["res.partner"].browse(self.render_object.ids)
        for fname, expected in zip(
            ["subject", "body_html"], self.base_rendered, strict=False
        ):
            rendered = template._render_field(fname, partner.ids, compute_lang=True)[
                partner.id
            ]
            self.assertEqual(rendered, expected)

    @users("employee")
    def test_render_qweb_compiles_once_per_batch(self):
        template = self.env["mail.template"].create(
            {
                "name": "Batch perf",
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "body_html": '<p>Hi <t t-out="object.name"/> #<t t-out="object.id"/></p>',
            }
        )
        partners = self.env["res.partner"].create(
            [{"name": "P%d" % idx} for idx in range(6)]
        )
        ir_qweb_cls = type(self.env["ir.qweb"])
        origin = ir_qweb_cls._generate_code_uncached
        compiles = []

        def _counting(self, template_arg):
            compiles.append(template_arg)
            return origin(self, template_arg)

        with patch.object(ir_qweb_cls, "_generate_code_uncached", _counting):
            rendered = template._render_field("body_html", partners.ids)
            self.assertLessEqual(
                len(compiles),
                1,
                "qweb template must be compiled once for the batch, not per record",
            )
            compiles.clear()
            template._render_field("body_html", partners.ids)
            self.assertEqual(
                len(compiles),
                0,
                "a second render of the same source must not recompile it: an "
                "etree template reaches no ormcache of its own, so mail keeps the "
                "parsed node stable for ir.qweb's node-keyed compiled cache",
            )
        for partner in partners:
            self.assertIn(partner.name, rendered[partner.id])

    @users("employee")
    def test_render_field_lang(self):
        template = self.env["mail.template"].browse(self.test_template.ids)
        partner = self.env["res.partner"].browse(self.render_object_fr.ids)
        for fname, expected in zip(
            ["subject", "body_html"], self.base_rendered_fr, strict=False
        ):
            rendered = template._render_field(fname, partner.ids, compute_lang=True)[
                partner.id
            ]
            self.assertEqual(rendered, expected)

    @users("employee")
    def test_render_field_no_records(self):
        template = self.test_template.with_env(self.env)
        partner = self.render_object.with_env(self.env)
        for res_ids in (
            [],
            (),
            [False],
            [""],
            [None],
            [False, partner.id],
        ):
            for fname, expected_obj, expected_void in zip(
                ["subject", "body_html"],
                self.base_rendered,
                self.base_rendered_void,
                strict=False,
            ):
                with self.subTest():
                    rendered_all = template._render_field(
                        fname, res_ids, compute_lang=True
                    )
                    if res_ids:
                        self.assertTrue(
                            res_ids[0] in rendered_all,
                            f"Rendering: key {res_ids[0]!r} is considered as valid and should have an entry",
                        )
                        self.assertEqual(rendered_all[res_ids[0]], expected_void)
                    if len(res_ids) == 2:
                        self.assertTrue(res_ids[1] in rendered_all)
                        self.assertEqual(rendered_all[res_ids[1]], expected_obj)
                    if not res_ids:
                        self.assertFalse(
                            rendered_all, "Rendering: void input -> void output"
                        )

    @users("employee")
    def test_render_field_not_existing(self):
        template = self.env["mail.template"].browse(self.test_template.ids)
        partner = self.env["res.partner"].browse(self.render_object_fr.ids)
        with self.assertRaises(ValueError):
            _rendered = template._render_field(
                "not_existing", partner.ids, compute_lang=True
            )[partner.id]

    @users("employee")
    def test_render_template_inline_template(self):
        partner = self.env["res.partner"].browse(self.render_object.ids)
        for source, expected in zip(
            self.base_inline_template_bits, self.base_rendered, strict=False
        ):
            rendered = self.env["mixin.mail.render"]._render_template(
                source,
                partner._name,
                partner.ids,
                engine="inline_template",
            )[partner.id]
            self.assertEqual(rendered, expected)

    @users("employee")
    def test_render_template_inline_template_w_post_process_custom_local_links(self):
        def _mock_get_base_url(recordset):
            return f"http://www.render-object-{recordset._name}-{recordset.id}-{recordset.display_name}.com"

        partner_ids = (
            self.env["res.partner"]
            .sudo()
            .create([{"name": f"test partner {n}"} for n in range(20)])
            .ids
        )
        with (
            patch("odoo.models.Model.get_base_url", new=_mock_get_base_url),
            self.assertQueryCount(13),
        ):
            self.env["res.partner"].browse(partner_ids).invalidate_recordset(
                ["name", "display_name"]
            )
            render_results = self.env["mixin.mail.render"]._render_template(
                '<a href="/test/destination"><img src="/test/image"></a>',
                "res.partner",
                partner_ids,
                engine="inline_template",
                options={"post_process": True},
            )
        Partner = self.env["res.partner"].with_prefetch(partner_ids)
        for partner_id, render_result in render_results.items():
            partner = Partner.browse(partner_id)
            expected_base_url = f"http://www.render-object-{partner._name}-{partner.id}-{partner.name}.com"
            self.assertEqual(
                render_result,
                f'<a href="{expected_base_url}/test/destination"><img src="{expected_base_url}/test/image"></a>',
            )

    @users("employee")
    def test_render_template_qweb(self):
        partner = self.env["res.partner"].browse(self.render_object.ids)
        for source, expected in zip(
            self.base_qweb_bits, self.base_rendered, strict=False
        ):
            rendered = self.env["mixin.mail.render"]._render_template(
                source,
                partner._name,
                partner.ids,
                engine="qweb",
            )[partner.id]
            self.assertEqual(rendered, expected)

    @users("employee")
    def test_render_template_qweb_keeps_a_binary_in_a_data_uri(self):
        partner = self.env["res.partner"].browse(self.render_object.ids)
        partner.sudo().image_1920 = base64.b64encode(
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff"
            b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
            b"\x00\x02\x02D\x01\x00;"
        )
        rendered = self.env["mixin.mail.render"]._render_template(
            '<img t-attf-src="data:image/png;base64,{{object.image_128}}"/>',
            partner._name,
            partner.ids,
            engine="qweb",
        )[partner.id]
        self.assertIn(
            f'src="data:image/png;base64,{partner.image_128.decode()}"',
            rendered,
            "a base64 field inlined into a data URI is text, not a blob to hide",
        )

    @users("employee")
    def test_render_template_qweb_view(self):
        partner = self.env["res.partner"].browse(self.render_object.ids)
        for source, expected in zip(
            self.base_qweb_templates_xmlids, self.base_rendered, strict=False
        ):
            rendered = self.env["mixin.mail.render"]._render_template(
                source,
                partner._name,
                partner.ids,
                engine="qweb_view",
            )[partner.id]
            self.assertEqual(rendered, expected)

    @users("employee")
    def test_render_template_various(self):
        partner = self.env["res.partner"].browse(self.render_object.ids)
        MixinMailRender = self.env["mixin.mail.render"]

        src = "This is a string"
        expected = "This is a string"
        for engine in ["inline_template"]:
            result = MixinMailRender._render_template(
                src,
                partner._name,
                partner.ids,
                engine=engine,
            )[partner.id]
            self.assertEqual(expected, result)

        src = "This is a string with a number {{ 13+13 }}"
        expected = "This is a string with a number 26"
        for engine in ["inline_template"]:
            result = MixinMailRender._render_template(
                src,
                partner._name,
                partner.ids,
                engine=engine,
            )[partner.id]
            self.assertEqual(expected, result)

        src = "This is a string with a block {{ 'hidden' if False else 'displayed' }}"
        expected = "This is a string with a block displayed"
        for engine in ["inline_template"]:
            result = MixinMailRender._render_template(
                src,
                partner._name,
                partner.ids,
                engine=engine,
            )[partner.id]
            self.assertEqual(expected, result)

        src = '<p class="text-muted"><span>This is a string</span></p>'
        expected = '<p class="text-muted"><span>This is a string</span></p>'
        for engine in ["inline_template", "qweb"]:
            result = MixinMailRender._render_template(
                src,
                partner._name,
                partner.ids,
                engine=engine,
            )[partner.id]
            self.assertEqual(expected, result)

        srces = [
            '<p class="text-muted"><span>This is a string with a number {{ 13+13 }}</span></p>',
            '<p class="text-muted"><span>This is a string with a number <t t-out="13+13"/></span></p>',
        ]
        expected = (
            '<p class="text-muted"><span>This is a string with a number 26</span></p>'
        )
        for engine, src in zip(["inline_template", "qweb"], srces, strict=False):
            result = MixinMailRender._render_template(
                src,
                partner._name,
                partner.ids,
                engine=engine,
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
        for engine in ["qweb"]:
            result = MixinMailRender._render_template(
                src,
                partner._name,
                partner.ids,
                engine=engine,
            )[partner.id]
            self.assertEqual(result, expected)

    @users("employee")
    def test_replace_local_links(self):
        local_links_template_bits = [
            '<a href="/web/path?a=a&b=b"/>',
            '<img src="/web/path?a=a&b=b"/>',
            '<v:fill src="/web/path?a=a&b=b"/>',
            '<v:image src="/web/path?a=a&b=b"/>',
            '<div style="background-image:url(/web/path?a=a&b=b);"/>',
            "<div style=\"background-image:url('/web/path?a=a&b=b');\"/>",
            '<div style="background-image:url(&#34;/web/path?a=a&b=b&#34;);"/>',
            '<div background="/web/path?a=a&b=b"/>',
            "<div style='background-image:url(\"/web/path?a=a&b=b\");'/>",
        ]
        base_url = self.env["mixin.mail.render"].get_base_url()
        rendered_local_links = [
            '<a href="%s/web/path?a=a&b=b"/>' % base_url,
            '<img src="%s/web/path?a=a&b=b"/>' % base_url,
            '<v:fill src="%s/web/path?a=a&b=b"/>' % base_url,
            '<v:image src="%s/web/path?a=a&b=b"/>' % base_url,
            '<div style="background-image:url(%s/web/path?a=a&b=b);"/>' % base_url,
            "<div style=\"background-image:url('%s/web/path?a=a&b=b');\"/>" % base_url,
            '<div style="background-image:url(&#34;%s/web/path?a=a&b=b&#34;);"/>'
            % base_url,
            '<div background="%s/web/path?a=a&b=b"/>' % base_url,
            "<div style='background-image:url(\"%s/web/path?a=a&b=b\");'/>" % base_url,
        ]
        for source, expected in zip(
            local_links_template_bits, rendered_local_links, strict=False
        ):
            rendered = self.env["mixin.mail.render"]._replace_local_links(source)
            self.assertEqual(rendered, expected)


@tagged("mail_render", "regex_render")
class TestRegexRendering(common.MailCommon):
    def test_qweb_regex_rendering(self):
        record = self.env["res.partner"].create({"name": "Alice"})

        def render(template):
            return self.env["mixin.mail.render"]._render_template_qweb(
                template, "res.partner", record.ids
            )[record.id]

        static_templates = (
            ("""<h1> Title </h1>""", "<h1> Title </h1>"),
            ("""<p t-out="object.name"/>""", "<p>Alice</p>"),
            ("""<p t-out="object.name"></p>""", "<p>Alice</p>"),
            ("""<P   t-out="object.name" ></p >""", "<p>Alice</p>"),
            ("""<t t-out="object.name"/>""", "Alice"),
            ("""<T t-out="object.name"/>""", "Alice"),
            ("""<div><T t-out="object.name"/></div>""", "<div>Alice</div>"),
            ("""<h1 t-out="object.name"/>""", "<h1>Alice</h1>"),
            ("""<p t-out='object.name'/>""", "<p>Alice</p>"),
            ("""<p t-out="object.contact_name"/>""", "<p></p>"),
            ("""<p t-out="object.name">Default</p>""", "<p>Alice</p>"),
            ("""<p t-out='object.name'>Default</p>""", "<p>Alice</p>"),
            ("""<p t-out="object.contact_name">Default</p>""", "<p>Default</p>"),
            (
                """<p t-out="object.name"/><p t-out="object.name">Default</p>""",
                "<p>Alice</p><p>Alice</p>",
            ),
            (
                """<p t-out="object.name"/><p t-out="object.contact_name">Default</p>""",
                "<p>Alice</p><p>Default</p>",
            ),
            (
                """<p
                    t-out="object.name"
                    />""",
                "<p>Alice</p>",
            ),
            (
                """<p
                    t-out="object.contact_name"
                    >
                    Default
                    </p>""",
                "<p>Default</p>",
            ),
            ("""<div><p t-out="object.name"/></div>""", "<div><p>Alice</p></div>"),
            ("""<p t-out="object.name" title="Test"/>""", '<p title="Test">Alice</p>'),
            ("""<p title="Test" t-out="object.name"/>""", '<p title="Test">Alice</p>'),
            ("""<div/aa t-out="object.name"></div/aa>""", '<div aa="">Alice</div>'),
            (
                """<div/aa='x' t-out="object.name"></div/aa='x'>""",
                '<div aa="x">Alice</div>',
            ),
        )
        o_qweb_render = self.env.registry["ir.qweb"]._render_prepared
        for template, expected in static_templates:
            with (
                patch(
                    "odoo.addons.base.models.ir_qweb.IrQweb._render_prepared",
                    autospec=True,
                    side_effect=o_qweb_render,
                ) as qweb_render,
                patch(
                    "odoo.addons.base.models.ir_qweb.unsafe_eval",
                    side_effect=eval,  # noqa: S307 - the spy calls through to real eval so the rendered value is still asserted
                ) as unsafe_eval,
            ):
                self.assertEqual(render(template), expected)
                self.assertFalse(qweb_render.called)
                self.assertFalse(unsafe_eval.called)

        with (
            patch(
                "odoo.addons.base.models.ir_qweb.IrQweb._render_prepared",
                autospec=True,
                side_effect=o_qweb_render,
            ) as qweb_render,
            patch(
                "odoo.addons.base.models.ir_qweb.unsafe_eval",
                side_effect=eval,  # noqa: S307 - the spy calls through to real eval so the rendered value is still asserted
            ) as unsafe_eval,
        ):
            self.assertNotIn("<55", render("""<55 t-out="object.name"></55>"""))
            self.assertFalse(qweb_render.called)
            self.assertFalse(unsafe_eval.called)

        non_static_templates = (
            ("""<p t-out=""/>""", "<p>()</p>"),
            ("""<p t-out="1+1"/>""", "<p>2</p>"),
            ("""<p t-out="env.context.get('test')"/>""", ""),
            ("""<p t-out="object.name"><img/></p>""", "<p>Alice</p>"),
            ("""<p t-out="object.parent_id.name"><img/></p>""", "<p><img/></p>"),
            ("""<p t-out="'<h1>test</h1>'"/>""", "<p>&lt;h1&gt;test&lt;/h1&gt;</p>"),
        )
        for template, expected in non_static_templates:
            with (
                patch(
                    "odoo.addons.base.models.ir_qweb.IrQweb._render_prepared",
                    autospec=True,
                    side_effect=o_qweb_render,
                ) as qweb_render,
                patch(
                    "odoo.addons.base.models.ir_qweb.unsafe_eval",
                    side_effect=eval,  # noqa: S307 - the spy calls through to real eval so the rendered value is still asserted
                ) as unsafe_eval,
            ):
                rendered = render(template)
                self.assertTrue(isinstance(rendered, Markup))
                self.assertEqual(rendered, expected)
                self.assertTrue(qweb_render.called)
                self.assertTrue(unsafe_eval.called)

    def test_inline_regex_rendering(self):
        record = self.env["res.partner"].create({"name": "Alice"})

        def render(template):
            return self.env["mixin.mail.render"]._render_template_inline_template(
                template, "res.partner", record.ids
            )[record.id]

        static_templates = (
            ("""{{object.name}}""", "Alice"),
            ("""{{object.contact_name}}""", ""),
            ("""{{object.name ||| Default}}""", "Alice"),
            ("""{{object.contact_name ||| Default}}""", "Default"),
        )
        for template, expected in static_templates:
            with patch(
                "odoo.tools.safe_eval.unsafe_eval",
                side_effect=eval,  # noqa: S307 - the spy calls through to real eval so the rendered value is still asserted
            ) as unsafe_eval:
                self.assertEqual(render(template), expected)
                self.assertFalse(unsafe_eval.called)
                self.assertFalse(
                    self.env[
                        "mixin.mail.render"
                    ]._has_unsafe_expression_template_inline_template(
                        template, "res.partner"
                    )
                )

        non_static_templates = (
            ("""{{''}}""", ""),
            ("""{{1+1}}""", "2"),
            ("""{{object.env.context.get('test')}}""", ""),
        )
        for template, expected in non_static_templates:
            with patch(
                "odoo.tools.safe_eval.unsafe_eval",
                side_effect=eval,  # noqa: S307 - the spy calls through to real eval so the rendered value is still asserted
            ) as unsafe_eval:
                self.assertEqual(render(template), expected)
                self.assertTrue(unsafe_eval.called)
                self.assertTrue(
                    self.env[
                        "mixin.mail.render"
                    ]._has_unsafe_expression_template_inline_template(
                        template, "res.partner"
                    )
                )


@tagged("mail_render")
class TestMailRenderSecurity(TestMailRenderCommon):
    @users("employee")
    def test_render_inline_template_impersonate(self):
        partner = self.env["res.partner"].browse(self.render_object.ids)
        src = "{{ user.name }} - {{ object.name }}"
        expected = "%s - %s" % (self.env.user.name, partner.name)
        result = (
            self.env["mixin.mail.render"]
            .sudo()
            ._render_template_inline_template(src, partner._name, partner.ids)[
                partner.id
            ]
        )
        self.assertIn(expected, result)

    @users("user_rendering_restricted")
    def test_render_inline_template_restricted(self):
        res_ids = self.env["res.partner"].search([], limit=1).ids
        with self.assertRaises(
            AccessError, msg="Simple user should not be able to render dynamic code"
        ):
            self.env["mixin.mail.render"]._render_template_inline_template(
                self.base_inline_template_bits[3], "res.partner", res_ids
            )

        src = """<h1>This is a static template</h1>"""
        result = self.env["mixin.mail.render"]._render_template_inline_template(
            src, "res.partner", res_ids
        )[res_ids[0]]
        self.assertEqual(src, str(result))

    @users("user_rendering_restricted")
    def test_render_inline_template_restricted_static(self):
        model = "res.partner"
        res_ids = self.env[model].search([], limit=1).ids
        MixinMailRender = self.env["mixin.mail.render"]

        result = MixinMailRender._render_template_inline_template(
            self.base_inline_template_bits[0], model, res_ids
        )[res_ids[0]]
        self.assertEqual(result, self.base_inline_template_bits[0])

    @users("employee")
    def test_render_inline_template_unrestricted(self):
        res_ids = self.env["res.partner"].search([], limit=1).ids
        result = self.env["mixin.mail.render"]._render_template_inline_template(
            self.base_inline_template_bits[3], "res.partner", res_ids
        )[res_ids[0]]
        self.assertIn(
            "26",
            result,
            "Template Editor should be able to render inline_template code",
        )

    @users("user_rendering_restricted")
    def test_render_restricted_allow_template_defaults(self):
        def patched_mail_template_default_values(model):
            return {
                "email_cc": "{{ object.user_ids and object.user_ids[0].email }}",
                "lang": "{{ object.user_ids and object.user_ids[0].lang }}",
                "body_html": '<p>Hi <t t-out="object.user_ids and object.user_ids[0].name"/></p>',
            }

        template_defaults = patched_mail_template_default_values(
            self.env["mail.template"]
        )
        partner_model_id = self.env["ir.model"]._get_id("res.partner")

        template = Form(
            self.env["mail.template"].with_context(
                {
                    "default_name": "test_allow_template_defaults_nodefault_valid",
                    "default_model_id": partner_model_id,
                }
            )
        )
        template = template.save()
        self.assertFalse(template.lang)
        self.assertFalse(template.email_cc)
        self.assertFalse(template.body_html)

        with self.assertRaises(
            AccessError,
            msg="Complex inline expression should fail if it is not the default.",
        ):
            template.lang = template_defaults["lang"]
        with self.assertRaises(
            AccessError,
            msg="Complex qweb expression should fail if it is not the default.",
        ):
            template.body_html = template_defaults["body_html"]

        with patch(
            "odoo.addons.base.models.res_partner.ResPartner._mail_template_default_values",
            new=patched_mail_template_default_values,
            create=True,
        ):
            template = Form(
                self.env["mail.template"].with_context(
                    {
                        "default_name": "test_allow_template_with_default",
                        "default_model_id": partner_model_id,
                    }
                )
            )
            template = template.save()
            self.assertEqual(template.lang, template_defaults["lang"])
            self.assertEqual(template.email_cc, template_defaults["email_cc"])
            self.assertEqual(template.body_html, template_defaults["body_html"])

            with self.assertRaises(
                AccessError,
                msg="Complex expressions should only be allowed if they are the default for that field.",
            ):
                template.email_cc = template_defaults["lang"]

    @users("user_rendering_restricted")
    def test_render_template_qweb_restricted(self):
        model = "res.partner"
        res_ids = self.env[model].search([], limit=1).ids
        partner = self.env[model].browse(res_ids)

        src = """<h1>This is a static template</h1>"""

        result = self.env["mixin.mail.render"]._render_template_qweb(
            src, model, res_ids
        )[partner.id]
        self.assertEqual(src, str(result))

    @users("user_rendering_restricted")
    def test_security_function_call(self):
        model = "res.partner"
        res_ids = self.env[model].search([], limit=1).ids
        partner = self.env[model].browse(res_ids)
        MixinMailRender = self.env["mixin.mail.render"]

        def cust_function():
            cust_function.call = True
            return "return value"

        cust_function.call = False

        src = """<h1>This is a test</h1>
<p>{{ cust_function() }}</p>"""
        expected = """<h1>This is a test</h1>
<p>return value</p>"""
        context = {"cust_function": cust_function}

        result = (
            self.env["mixin.mail.render"]
            .with_user(self.user_admin)
            ._render_template_inline_template(
                src, partner._name, partner.ids, add_context=context
            )[partner.id]
        )
        self.assertEqual(expected, result)
        self.assertTrue(cust_function.call)

        with self.assertRaises(
            AccessError, msg="Simple user should not be able to render dynamic code"
        ):
            MixinMailRender._render_template_inline_template(
                src, model, res_ids, add_context=context
            )

    @users("user_rendering_restricted")
    def test_security_inline_template_restricted(self):
        res_ids = self.env["res.partner"].search([], limit=1).ids
        with self.assertRaises(
            AccessError, msg="Simple user should not be able to render dynamic code"
        ):
            self.env["mixin.mail.render"]._render_template_inline_template(
                self.base_inline_template_bits[4], "res.partner", res_ids
            )

    @users("employee")
    def test_security_inline_template_unrestricted(self):
        res_ids = self.env["res.partner"].search([], limit=1).ids
        result = self.env["mixin.mail.render"]._render_template_inline_template(
            self.base_inline_template_bits[4], "res.partner", res_ids
        )[res_ids[0]]
        self.assertNotIn(
            "Code not executed", result, "The condition block did not work"
        )

    @users("user_rendering_restricted")
    def test_security_qweb_template_restricted(self):
        res_ids = self.env["res.partner"].search([], limit=1).ids
        with self.assertRaises(
            AccessError,
            msg="Simple user should not be able to render complex qweb code",
        ):
            self.env["mixin.mail.render"]._render_template_qweb(
                self.base_qweb_bits[2], "res.partner", res_ids
            )

    @users("user_rendering_restricted")
    def test_security_qweb_template_restricted_cached(self):
        res_ids = self.env["res.partner"].search([], limit=1).ids

        result = (
            self.env["mixin.mail.render"]
            .with_user(self.user_admin)
            ._render_template_qweb(self.base_qweb_bits[2], "res.partner", res_ids)
        )

        self.assertEqual(
            result[res_ids[0]], "<p>\n    <span>English Speaker</span>\n</p>"
        )

        with self.assertRaises(
            AccessError,
            msg="Simple user should not be able to render complex qweb code",
        ):
            self.env["mixin.mail.render"]._render_template_qweb(
                self.base_qweb_bits[2], "res.partner", res_ids
            )

    @users("employee")
    def test_security_qweb_template_unrestricted(self):
        res_ids = self.env["res.partner"].search([], limit=1).ids
        result = self.env["mixin.mail.render"]._render_template_qweb(
            self.base_qweb_bits[1], "res.partner", res_ids
        )[res_ids[0]]
        self.assertNotIn(
            "Code not executed", result, "The condition block did not work"
        )
