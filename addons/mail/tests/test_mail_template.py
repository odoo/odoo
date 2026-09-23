from unittest.mock import patch

from markupsafe import Markup

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import Form, HttpCase, tagged, users
from odoo.tools import convert_file, mute_logger
from odoo.tools.translate import TranslationImporter, get_po_paths

from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user


@tagged("mail_template")
class TestMailTemplate(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].set_param(
            "mail.restrict.template.rendering", True
        )
        cls.user_employee.group_ids -= cls.env.ref("mail.group_mail_template_editor")
        cls.test_partner = cls.env["res.partner"].create(
            {
                "email": "test.rendering@test.example.com",
                "name": "Test Rendering",
            }
        )

        cls.mail_template = cls.env["mail.template"].create(
            {
                "name": "Test template",
                "subject": "{{ 1 + 5 }}",
                "body_html": '<t t-out="4 + 9"/>',
                "lang": "{{ object.lang }}",
                "auto_delete": True,
                "model_id": cls.env.ref("base.model_res_partner").id,
                "use_default_to": False,
            }
        )

        cls.user_employee_2 = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email="employee_2@test.com",
            groups="base.group_user",
            login="employee_2",
            name="Albertine Another Employee",
        )

    @users("admin")
    @mute_logger("odoo.addons.mail.models.mail_template")
    @mute_logger("odoo.addons.mail.models.mixin_mail_render")
    def test_invalid_template_on_save(self):
        mail_template = self.env["mail.template"].create(
            {
                "name": "Test template",
                "model_id": self.env["ir.model"]._get_id("res.users"),
                "subject": "Template {{ object.company_id.email }}",
                "lang": "{{ object.partner_id.lang }}",
            }
        )

        for fname in [
            "body_html",
            "email_cc",
            "email_from",
            "email_to",
            "lang",
            "partner_to",
            "reply_to",
            "scheduled_date",
            "subject",
        ]:
            with self.subTest(fname=fname):
                if fname == "body_html":
                    value_field = '<p>Hello <t t-out="object.unknown_field"/></p>'
                    value_fun = '<p>Hello <t t-out="object.is_portal_0()"/></p>'
                else:
                    value_field = "{{ object.unknown_field }}"
                    value_fun = "{{ object.is_portal_0() }}"
                with self.assertRaises(ValidationError):
                    mail_template.write(
                        {
                            fname: value_field,
                        }
                    )
                with self.assertRaises(ValidationError):
                    mail_template.write(
                        {
                            fname: value_fun,
                        }
                    )
                with self.assertRaises(ValidationError):
                    self.env["mail.template"].create(
                        {
                            "name": "Test template",
                            "model_id": self.env["ir.model"]._get("res.users").id,
                            fname: value_field,
                        }
                    )

        with self.assertRaises(ValidationError):
            mail_template.write(
                {
                    "model_id": self.env["ir.model"]._get_id("res.partner"),
                }
            )

    @users("admin")
    @mute_logger("odoo.addons.mail.models.mixin_mail_render")
    def test_guarded_unknown_attribute_is_accepted_on_save(self):
        mail_template = self.env["mail.template"].create(
            {
                "name": "Guarded template",
                "model_id": self.env["ir.model"]._get_id("res.users"),
                "subject": "ok",
            }
        )
        for fname, value in [
            (
                "body_html",
                (
                    "<p><t t-if=\"hasattr(object, 'timesheet_count') and "
                    'object.timesheet_count">PS: review your timesheets</t></p>'
                ),
            ),
            (
                "body_html",
                "<p><t t-out=\"getattr(object, 'timesheet_count', 0)\"/></p>",
            ),
            (
                "subject",
                "{{ hasattr(object, 'timesheet_count') and object.timesheet_count }}",
            ),
        ]:
            with self.subTest(fname=fname, value=value):
                mail_template.write({fname: value})
                self.assertEqual(mail_template[fname], value)

        with self.assertRaises(ValidationError):
            mail_template.write(
                {"subject": "{{ hasattr(object, 'other') and object.timesheet_count }}"}
            )

    @users("admin")
    @mute_logger("odoo.addons.mail.models.mail_template")
    @mute_logger("odoo.addons.mail.models.mixin_mail_render")
    def test_invalid_template_skipped_during_install(self):
        mail_template = self.env["mail.template"].create(
            {
                "name": "Installed template",
                "model_id": self.env["ir.model"]._get_id("res.users"),
                "subject": "ok",
            }
        )
        mail_template.with_context(install_mode=True).write(
            {"subject": "{{ object.unknown_field }}"}
        )
        self.assertEqual(mail_template.subject, "{{ object.unknown_field }}")
        with self.assertRaises(ValidationError):
            mail_template.write({"subject": "{{ object.another_unknown }}"})

    @users("employee")
    def test_mail_compose_message_content_from_template(self):
        form = Form(
            self.env["mail.compose.message"].with_context(
                default_model="res.partner", active_ids=self.test_partner.ids
            )
        )
        form.template_id = self.mail_template
        mail_compose_message = form.save()

        self.assertEqual(
            mail_compose_message.subject, "6", "We must trust mail template values"
        )

    @users("employee")
    def test_mail_compose_message_content_from_template_mass_mode(self):
        mail_compose_message = self.env["mail.compose.message"].create(
            {
                "composition_mode": "mass_mail",
                "model": "res.partner",
                "template_id": self.mail_template.id,
                "subject": "{{ 1 + 5 }}",
            }
        )

        values = mail_compose_message._prepare_mail_values(self.partner_employee.ids)

        self.assertEqual(
            values[self.partner_employee.id]["subject"],
            "6",
            "We must trust mail template values",
        )
        self.assertIn(
            "13",
            values[self.partner_employee.id]["body_html"],
            "We must trust mail template values",
        )

    @users("admin")
    def test_mail_template_abstract_model(self):
        with self.assertRaises(ValidationError):
            self.env["mail.template"].create(
                {
                    "name": "Test abstract template",
                    "model_id": self.env["ir.model"]._get("mixin.mail.thread").id,
                }
            )
        template = self.env["mail.template"].create(
            {
                "name": "Test abstract template",
                "model_id": self.env["ir.model"]._get("res.partner").id,
            }
        )
        with self.assertRaises(ValidationError):
            template.write(
                {
                    "name": "Test abstract template",
                    "model_id": self.env["ir.model"]._get("mixin.mail.thread").id,
                }
            )

    def test_mail_template_acl(self):
        self.assertTrue(self.user_admin.has_group("mail.group_mail_template_editor"))
        self.assertTrue(self.user_admin.has_group("base.group_sanitize_override"))
        self.assertFalse(
            self.user_employee.has_group("mail.group_mail_template_editor")
        )
        self.assertFalse(self.user_employee.has_group("base.group_sanitize_override"))

        model = self.env["ir.model"]._get_id("res.users")
        record = self.user_employee

        mail_template = (
            self.env["mail.template"]
            .with_user(self.user_admin)
            .create(
                {
                    "name": "Test template",
                    "model_id": model,
                }
            )
        )
        self.assertEqual(mail_template.name, "Test template")

        mail_template.with_user(self.user_admin).name = "New name"
        self.assertEqual(mail_template.name, "New name")

        employee_template = (
            self.env["mail.template"]
            .with_user(self.user_employee)
            .create({"body_html": "<p>foo</p>", "model_id": model})
        )
        employee_template.with_user(self.user_employee).body_html = "<p>bar</p>"

        employee_template = (
            self.env["mail.template"]
            .with_user(self.user_employee)
            .create(
                {
                    "email_to": "foo@bar.com",
                    "model_id": model,
                }
            )
        )
        employee_template = employee_template.with_user(self.user_employee)

        employee_template.email_to = "bar@foo.com"

        with self.assertRaises(AccessError):
            self.env["mail.template"].with_user(self.user_employee).create(
                {"body_html": """<p t-out="'foo'"></p>""", "model_id": model}
            )

        with self.assertRaises(AccessError):
            self.env["mail.template"].with_user(self.user_employee).create(
                {"body_html": """<p t-out="object.name"></p>"""}
            )

        with self.assertRaises(AccessError):
            mail_template.with_user(self.user_employee).body_html = "<p>foo</p>"
        with self.assertRaises(AccessError):
            mail_template.with_user(
                self.user_employee
            ).body_html = """<p t-out="'foo'"></p>"""

        employee_template.body_html = "<p>foo</p>"

        with self.assertRaises(AccessError):
            self.env["mail.template"].with_user(self.user_employee).create(
                {"email_to": "{{ object.partner_id.email }}", "model_id": model}
            )

        with self.assertRaises(AccessError):
            employee_template.body_html = """<p t-out="'foo'"></p>"""

        forbidden_expressions = (
            "object.partner_id.email",
            "object.password",
            "object.name or (1+1)",
            "user.password",
            "object.name or object.name",
            "[a for a in (1,)]",
            "object.name or f''",
            "object.name or ''.format",
            "object.name or f'{1+1}'",
            "object.name or len('')",
            "'abcd' or object.name",
            "object.name and ''",
        )
        for expression in forbidden_expressions:
            with self.assertRaises(AccessError):
                employee_template.email_to = "{{ %s }}" % expression

            with self.assertRaises(AccessError):
                employee_template.email_to = "{{ %s ||| Bob}}" % expression

            with self.assertRaises(AccessError):
                employee_template.body_html = '<p t-out="%s"></p>' % expression

            with self.assertRaises(AccessError):
                employee_template.body_html = '<p t-esc="%s"></p>' % expression

            with self.assertRaises(AccessError):
                employee_template.with_context(
                    raise_on_forbidden_code=False
                ).email_to = "{{ %s }}" % expression
            with self.assertRaises(AccessError):
                employee_template.with_context(
                    raise_on_forbidden_code=False
                ).body_html = '<p t-esc="%s"></p>' % expression

            mail_template.with_user(self.user_admin).email_to = "{{ %s }}" % expression
            mail_template.with_user(self.user_admin).email_to = (
                "{{ %s ||| Bob }}" % expression
            )
            mail_template.with_user(self.user_admin).body_html = (
                '<p t-out="%s">Default</p>' % expression
            )
            mail_template.with_user(self.user_admin).body_html = (
                '<p t-esc="%s">Default</p>' % expression
            )

        code = """<t t-inner-content="<p t-out='1+11'>Test</p>"></t>"""
        body = self.env["mixin.mail.render"]._render_template_qweb(
            code, "res.partner", record.ids
        )[record.id]
        self.assertNotIn("12", body)
        code = """<t t-inner-content="&lt;p t-out='1+11'&gt;Test&lt;/p&gt;"></t>"""
        body = self.env["mixin.mail.render"]._render_template_qweb(
            code, "res.partner", record.ids
        )[record.id]
        self.assertNotIn("12", body)

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
            '<p t-out="object.name"><img/></p>',
            '<p t-out="object.password"></p>',
        )
        for expression in forbidden_qweb_expressions:
            with self.assertRaises(AccessError):
                employee_template.body_html = expression
            self.assertTrue(
                self.env["mixin.mail.render"]._has_unsafe_expression_template_qweb(
                    expression, "res.partner"
                )
            )

        allowed_qweb_expressions = (
            '<p t-out="object.name"></p>',
            '<p t-out="object.name"></p><img/>',
            '<p t-out="object.name"></p><img title="Test"/>',
            '<p t-out="object.name">Default</p>',
            '<p t-out="object.name" title="Test"></p>',
            '<p t-out="object.partner_id.name">Default</p>',
        )
        o_qweb_render = self.env.registry["ir.qweb"]._render_prepared
        for expression in allowed_qweb_expressions:
            template = (
                self.env["mail.template"]
                .with_user(self.user_employee)
                .create(
                    {
                        "body_html": expression,
                        "model_id": model,
                    }
                )
            )
            self.assertFalse(
                self.env["mixin.mail.render"]._has_unsafe_expression_template_qweb(
                    expression, "res.partner"
                )
            )

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
                rendered = template._render_field("body_html", record.ids)[record.id]
                self.assertNotIn("t-out", rendered)
                self.assertFalse(qweb_render.called)
                self.assertFalse(unsafe_eval.called)

        mail_template.body_html = '<t t-out="1+1"/>'
        with patch(
            "odoo.addons.base.models.ir_qweb.IrQweb._render_prepared",
            autospec=True,
            side_effect=o_qweb_render,
        ) as qweb_render:
            rendered = mail_template._render_field("body_html", record.ids)[record.id]
            self.assertEqual(rendered, "2")
            self.assertTrue(qweb_render.called)

        employee_template.email_to = "Test {{ object.name }}"
        with patch("odoo.tools.safe_eval.unsafe_eval", side_effect=eval) as unsafe_eval:  # noqa: S307 - the spy calls through to real eval so the rendered value is still asserted
            employee_template._render_field("email_to", record.ids)
            self.assertFalse(unsafe_eval.called)

        mail_template.email_to = "Test {{ 1+1 }}"
        with patch("odoo.tools.safe_eval.unsafe_eval", side_effect=eval) as unsafe_eval:  # noqa: S307 - the spy calls through to real eval so the rendered value is still asserted
            mail_template._render_field("email_to", record.ids)
            self.assertTrue(unsafe_eval.called)

        templates = (
            (
                """<p ou="<p t-out="object.name">"</p>""",
                '<p ou="&lt;p t-out=" object.name"="">"</p>',
            ),
            (
                """<p title="'<p t-out='object.name'/>">""",
                """<p title="'&lt;p t-out='object.name'/&gt;"></p>""",
            ),
        )
        o_render = self.env["mixin.mail.render"]._render_template_qweb_static
        for template, excepted in templates:
            mail_template.body_html = template
            with patch(
                "odoo.addons.mail.models.mixin_mail_render.MixinMailRender._render_template_qweb_static",
                side_effect=o_render,
            ) as render:
                rendered = mail_template._render_field("body_html", record.ids)[
                    record.id
                ]
                self.assertEqual(rendered, excepted)
                self.assertTrue(render.called)

        record.name = "<b> test </b>"
        mail_template.body_html = '<t t-out="object.name"/>'
        with patch(
            "odoo.addons.mail.models.mixin_mail_render.MixinMailRender._render_template_qweb_static",
            side_effect=o_render,
        ) as render:
            rendered = mail_template._render_field("body_html", record.ids)[record.id]
            self.assertEqual(rendered, "&lt;b&gt; test &lt;/b&gt;")
            self.assertTrue(render.called)

        mail_template.with_user(self.user_admin).email_to = "{{ env.user.name }}"
        rendered = mail_template._render_field("email_to", record.ids)[record.id]
        self.assertIn(self.user_admin.name, rendered)

    def test_mail_template_acl_translation(self):
        self.env.ref("base.lang_fr").sudo().active = True

        employee_template = (
            self.env["mail.template"]
            .with_user(self.user_employee)
            .create(
                {
                    "model_id": self.env.ref("base.model_res_partner").id,
                    "subject": "The subject",
                    "body_html": "<p>foo</p>",
                }
            )
        )

        employee_template.with_context(lang="fr_FR").body_html = "non-qweb"

        with self.assertRaises(AccessError):
            employee_template.with_context(lang="fr_FR").body_html = '<t t-esc="foo"/>'

        employee_template.with_context(
            lang="fr_FR"
        ).sudo().body_html = '<t t-esc="foo"/>'

        employee_template.body_html = False
        employee_template.body_html = "<p>foo</p>"

        employee_template.with_context(lang="fr_FR").subject = "non-qweb"

        with self.assertRaises(AccessError):
            employee_template.with_context(lang="fr_FR").subject = "{{ object.city }}"

        employee_template.with_context(
            lang="fr_FR"
        ).sudo().subject = "{{ object.city }}"

    def test_mail_template_copy(self):
        (self.user_employee + self.user_employee_2).write(
            {
                "group_ids": [(4, self.env.ref("mail.group_mail_template_editor").id)],
            }
        )
        attachment_data_list = self._generate_attachments_data(
            4, self.mail_template._name, self.mail_template.id
        )
        self.mail_template.write(
            {
                "attachment_ids": [
                    (0, 0, attachment_data)
                    for attachment_data in attachment_data_list[:2]
                ],
            }
        )
        original_attachments = self.mail_template.attachment_ids
        for test_user in (self.user_employee, self.user_employee_2):
            with self.subTest(user_name=test_user.name):
                template = self.mail_template.with_user(test_user)
                self.assertEqual(
                    set(template.attachment_ids.mapped("name")),
                    {"AttFileName_00.txt", "AttFileName_01.txt"},
                )
        mail_template_2 = self.env["mail.template"].create(
            {
                "name": "Test Template 2",
            }
        )

        new_template, new_template_2 = (
            (self.mail_template + mail_template_2).with_user(self.user_employee).copy()
        )
        new_template.user_id = self.user_employee
        self.assertEqual(
            set(new_template.attachment_ids.mapped("name")),
            {"AttFileName_00.txt", "AttFileName_01.txt"},
        )
        self.assertFalse(
            new_template.attachment_ids & original_attachments,
            "Template copy should copy attachments, not keep the same, to avoid ACLs / ownership issues",
        )
        self.assertFalse(
            new_template_2.attachment_ids,
            "Should not take attachments from first template in multi copy",
        )
        self.assertEqual(
            new_template.name,
            f"{self.mail_template.name} (copy)",
            "Default name should be the old one + copy",
        )
        self.assertEqual(
            new_template_2.name,
            f"{mail_template_2.name} (copy)",
            "Default name should be the old one + copy",
        )
        self.assertEqual(
            new_template.attachment_ids.mapped("res_id"), new_template.ids * 2
        )
        self.assertEqual(
            original_attachments.mapped("res_id"), self.mail_template.ids * 2
        )

        new_template_as2 = new_template.with_user(self.user_employee_2)
        self.assertEqual(
            set(new_template_as2.attachment_ids.mapped("name")),
            {"AttFileName_00.txt", "AttFileName_01.txt"},
        )

        newer_template, newer_template_2 = (
            (self.mail_template + mail_template_2)
            .with_user(self.user_employee)
            .copy(
                default={
                    "attachment_ids": [
                        (0, 0, attachment_data_list[2]),
                        (0, 0, attachment_data_list[3]),
                    ],
                    "name": "My Copy",
                }
            )
        )
        self.assertEqual(
            set(newer_template.attachment_ids.mapped("name")),
            {"AttFileName_02.txt", "AttFileName_03.txt"},
        )
        self.assertEqual(
            set(newer_template_2.attachment_ids.mapped("name")),
            {"AttFileName_02.txt", "AttFileName_03.txt"},
        )
        self.assertFalse(
            newer_template.attachment_ids
            & (original_attachments & new_template.attachment_ids),
            "Template copy should copy attachments, not keep the same, to avoid ACLs / ownership issues",
        )
        self.assertFalse(
            newer_template_2.attachment_ids & newer_template.attachment_ids,
            "Template copy should copy attachments, not keep the same, to avoid ACLs / ownership issues",
        )
        self.assertEqual(
            newer_template.name, "My Copy", "Copy should respect given default"
        )
        self.assertEqual(
            newer_template_2.name, "My Copy", "Copy should respect given default"
        )
        self.assertEqual(
            newer_template.attachment_ids.mapped("res_id"), newer_template.ids * 2
        )
        self.assertEqual(
            newer_template_2.attachment_ids.mapped("res_id"), newer_template_2.ids * 2
        )
        self.assertEqual(
            newer_template.attachment_ids.mapped("res_model"),
            [newer_template._name] * 2,
        )
        self.assertEqual(
            newer_template.attachment_ids.mapped("res_id"), newer_template.ids * 2
        )
        self.assertEqual(
            newer_template.attachment_ids.mapped("res_model"),
            [newer_template._name] * 2,
        )
        self.assertEqual(
            original_attachments.mapped("res_id"), self.mail_template.ids * 2
        )
        self.assertEqual(
            original_attachments.mapped("res_model"), [self.mail_template._name] * 2
        )

    def test_mail_template_parse_partner_to(self):
        for partner_to, expected in [
            ("1", [1]),
            ("1,2,3", [1, 2, 3]),
            ("1, 2,  3", [1, 2, 3]),
            ("[1, 2, 3]", [1, 2, 3]),
            ("(1, 2, 3)", [1, 2, 3]),
            ('1,[],2,"3"', [1, 2, 3]),
            ('(1, "wrong", 2, "partner_name", "3")', [1, 2, 3]),
            ("res.partner(1, 2, 3)", [2]),
        ]:
            with self.subTest(partner_to=partner_to):
                parsed = self.mail_template._parse_partner_to(partner_to)
                self.assertListEqual(parsed, expected)

    def test_server_archived_usage_protection(self):
        IrMailServer = self.env["ir.mail_server"]
        server = IrMailServer.create(
            {
                "name": "Server",
                "smtp_host": "archive-test.smtp.local",
            }
        )
        self.mail_template.mail_server_id = server.id
        with self.assertRaises(
            UserError, msg="Server cannot be archived because it is used"
        ):
            server.action_archive()
        self.assertTrue(server.active)
        self.mail_template.mail_server_id = IrMailServer
        server.action_archive()
        self.assertFalse(server.active)


@tagged("mail_template")
class TestMailTemplateReset(MailCommon):
    def _load(self, module, filepath):
        # pylint: disable=no-value-for-parameter
        convert_file(
            self.env,
            module="mail",
            filename=filepath,
            idref={},
            mode="init",
            noupdate=False,
        )

    def test_mail_template_reset(self):
        self._load("mail", "tests/test_mail_template.xml")

        mail_template = self.env.ref("mail.mail_template_test").with_context(
            lang=self.env.user.lang
        )

        mail_template.write(
            {
                "body_html": "<div>Hello</div>",
                "name": "Mail: Mail Template",
                "subject": "Test",
                "email_from": "admin@example.com",
                "email_to": "user@example.com",
                "attachment_ids": False,
            }
        )

        context = {"default_template_ids": mail_template.ids}
        mail_template_reset = (
            self.env["mail.template.reset"].with_context(context).create({})
        )
        reset_action = mail_template_reset.reset_template()
        self.assertTrue(reset_action)

        self.assertEqual(
            mail_template.body_html.strip(), Markup("<div>Hello Odoo</div>")
        )
        self.assertEqual(mail_template.name, "Mail: Test Mail Template")
        self.assertEqual(
            mail_template.email_from,
            '"{{ object.company_id.name }}" <{{ (object.company_id.email or user.email) }}>',
        )
        self.assertEqual(mail_template.email_to, "{{ object.email_formatted }}")
        self.assertEqual(
            mail_template.attachment_ids,
            self.env.ref("mail.mail_template_test_attachment"),
        )

        self.assertFalse(mail_template.subject, "Subject should be set to False")

    def test_resetting_a_template_reads_the_real_translation_files(self):
        # the other reset tests replace load_file; this one keeps it, so a
        # signature the reset no longer matches fails here
        self._load("mail", "tests/test_mail_template.xml")
        self.env["res.lang"]._activate_lang("fr_FR")
        self.env["mail.template"]._override_translation_term(
            "mail", ["mail.mail_template_test"]
        )

    def test_an_empty_xmlid_filter_loads_nothing(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        po_path = next(get_po_paths("mail", "fr_FR"))
        for xmlids, loaded in ((None, True), (set(), False)):
            with self.subTest(xmlids=xmlids):
                importer = TranslationImporter(self.env.cr)
                importer.load_file(po_path, "fr_FR", xmlids=xmlids)
                self.assertEqual(bool(importer.model_translations), loaded)

    def test_mail_template_reset_translation(self):
        self._load("mail", "tests/test_mail_template.xml")

        self.env["res.lang"]._activate_lang("en_GB")
        self.env["res.lang"]._activate_lang("fr_FR")
        mail_template = self.env.ref("mail.mail_template_test").with_context(
            lang="en_US"
        )
        mail_template.write(
            {
                "body_html": "<div>Hello</div>",
                "name": "Mail: Mail Template",
            }
        )

        mail_template.with_context(lang="en_GB").write(
            {
                "body_html": "<div>Hello UK</div>",
                "name": "Mail: Mail Template UK",
            }
        )

        context = {"default_template_ids": mail_template.ids, "lang": "fr_FR"}

        def fake_load_file(translation_importer, filepath, lang, xmlids=None):
            if lang == "fr_FR":
                translation_importer.model_translations["mail.template"] = {
                    "body_html": {
                        "mail.mail_template_test": {"fr_FR": "<div>Hello Odoo FR</div>"}
                    },
                    "name": {
                        "mail.mail_template_test": {
                            "fr_FR": "Mail: Test Mail Template FR"
                        }
                    },
                }

        with patch(
            "odoo.tools.translate.TranslationImporter.load_file", fake_load_file
        ):
            mail_template_reset = (
                self.env["mail.template.reset"].with_context(context).create({})
            )
            reset_action = mail_template_reset.reset_template()
        self.assertTrue(reset_action)

        self.assertEqual(
            mail_template.body_html.strip(), Markup("<div>Hello Odoo</div>")
        )
        self.assertEqual(
            mail_template.with_context(lang="en_GB").body_html.strip(),
            Markup("<div>Hello Odoo</div>"),
        )
        self.assertEqual(
            mail_template.with_context(lang="fr_FR").body_html.strip(),
            Markup("<div>Hello Odoo FR</div>"),
        )

        self.assertEqual(mail_template.name, "Mail: Test Mail Template")
        self.assertEqual(
            mail_template.with_context(lang="en_GB").name, "Mail: Test Mail Template"
        )
        self.assertEqual(
            mail_template.with_context(lang="fr_FR").name, "Mail: Test Mail Template FR"
        )


@tagged("mail_template")
class TestMailTemplateBodyEditorOptions(MailCommon):
    def test_body_html_strips_iframes(self):
        template = self.env["mail.template"].create(
            {
                "name": "Video template",
                "model_id": self.env["ir.model"]._get("res.partner").id,
                "body_html": '<div><iframe src="https://www.youtube.com/embed/x"></iframe></div>',
            }
        )
        self.assertNotIn("iframe", template.body_html)

    def test_form_view_disables_video(self):
        arch = self.env.ref("mail.email_template_form").arch
        self.assertIn(
            "'allowVideo': false",
            arch,
            "mail.template's body_html must disable video embedding through the "
            "option name the html_mail widget reads (see class docstring).",
        )
        self.assertNotIn(
            "allowCommandVideo",
            arch,
            "allowCommandVideo is not an html_mail option; it is ignored, which "
            "silently re-enables video embedding on body_html.",
        )


@tagged("mail_template", "-at_install", "post_install")
class TestMailTemplateUI(HttpCase):
    def test_mail_template_dynamic_placeholder_tour(self):
        self.start_tour(
            "/odoo?debug=1", "mail_template_dynamic_placeholder_tour", login="admin"
        )


@tagged("mail_template", "-at_install", "post_install")
class TestTemplateConfigRestrictEditor(MailCommon):
    def test_switch_icp_value(self):
        group = self.env.ref("mail.group_mail_template_editor")

        self.assertTrue(self.user_employee.has_group("mail.group_mail_template_editor"))
        self.assertFalse(self.user_employee.has_group("base.group_system"))

        self.assertIn(group, self.user_employee.all_group_ids)
        self.assertNotIn(group, self.user_employee.group_ids)

        self.env["ir.config_parameter"].set_param(
            "mail.restrict.template.rendering", True
        )
        self.assertFalse(
            self.user_employee.has_group("mail.group_mail_template_editor")
        )

        self.env["ir.config_parameter"].set_param(
            "mail.restrict.template.rendering", False
        )
        self.assertTrue(self.user_employee.has_group("mail.group_mail_template_editor"))


@tagged("mail_template", "-at_install", "post_install")
class TestSearchTemplateCategory(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        MailTemplate = cls.env["mail.template"].with_context(active_test=False)
        ModelData = cls.env["ir.model.data"]

        cls.existing = MailTemplate.search([])

        cls.hidden_templates = MailTemplate.create(
            [
                {"name": "Hidden Template 1", "active": False},
                {"name": "Hidden Template 2", "description": ""},
            ]
        )
        last = cls.hidden_templates[-1]
        ModelData.create(
            {
                "name": f"mail_template_{last.id}",
                "module": "test_module",
                "model": "mail.template",
                "res_id": last.id,
            }
        )

        cls.custom_templates = MailTemplate.create(
            [
                {"name": f"Custom Template {i + 1}", "description": f"Desc {i + 1}"}
                for i in range(4)
            ]
        )
        cls.custom_templates |= MailTemplate.create(
            {"name": "Custom Template empty", "description": ""}
        )

        cls.base_templates = MailTemplate.create(
            [
                {"name": f"Base Template {i + 1}", "description": f"Desc Base {i + 1}"}
                for i in range(4)
            ]
        )

        for template in cls.base_templates:
            ModelData.create(
                {
                    "name": f"mail_template_{template.id}",
                    "module": "test_module",
                    "model": "mail.template",
                    "res_id": template.id,
                }
            )

    @users("employee")
    def test_search_template_category(self):
        MailTemplate = self.env["mail.template"].with_context(active_test=False)

        hidden_domain = [("template_category", "in", ["hidden_template"])]
        hidden_templates = MailTemplate.search(hidden_domain) - self.existing
        self.assertEqual(
            len(hidden_templates),
            len(self.hidden_templates),
            "Hidden templates count mismatch",
        )
        self.assertEqual(
            set(hidden_templates.mapped("template_category")),
            {"hidden_template"},
            "Computed field doesn't match 'hidden_template'",
        )

        base_domain = [("template_category", "in", ["base_template"])]
        base_templates = MailTemplate.search(base_domain) - self.existing
        self.assertEqual(
            len(base_templates),
            len(self.base_templates),
            "Base templates count mismatch",
        )
        self.assertEqual(
            set(base_templates.mapped("template_category")),
            {"base_template"},
            "Computed field doesn't match 'base_template'",
        )

        custom_domain = [("template_category", "in", ["custom_template"])]
        custom_templates = MailTemplate.search(custom_domain) - self.existing
        self.assertEqual(
            len(custom_templates),
            len(self.custom_templates),
            "Custom templates count mismatch",
        )
        self.assertEqual(
            set(custom_templates.mapped("template_category")),
            {"custom_template"},
            "Computed field doesn't match 'custom_template'",
        )

        combined_domain = [
            (
                "template_category",
                "in",
                ["hidden_template", "base_template", "custom_template"],
            )
        ]
        combined_templates = MailTemplate.search(combined_domain) - self.existing
        total_templates = (
            len(self.hidden_templates)
            + len(self.base_templates)
            + len(self.custom_templates)
        )
        self.assertEqual(
            len(combined_templates),
            total_templates,
            "Combined templates count mismatch",
        )

        hidden_domain = [("template_category", "=", "hidden_template")]
        hidden_templates = MailTemplate.search(hidden_domain) - self.existing
        self.assertEqual(
            len(hidden_templates),
            len(self.hidden_templates),
            "Hidden templates count mismatch",
        )

        not_in_domain = [("template_category", "!=", "hidden_template")]
        not_in_templates = MailTemplate.search(not_in_domain) - self.existing
        expected_templates = len(self.base_templates) + len(self.custom_templates)
        self.assertEqual(
            len(not_in_templates), expected_templates, "Not in templates count mismatch"
        )

        not_in_domain = [("template_category", "not in", ["hidden_template"])]
        not_in_templates = MailTemplate.search(not_in_domain) - self.existing
        expected_templates = len(self.base_templates) + len(self.custom_templates)
        self.assertEqual(
            len(not_in_templates), expected_templates, "Not in templates count mismatch"
        )

        not_in_domain = [
            ("template_category", "not in", ["hidden_template", "base_template"])
        ]
        not_in_templates = MailTemplate.search(not_in_domain) - self.existing
        expected_templates = len(self.custom_templates)
        self.assertEqual(
            len(not_in_templates),
            expected_templates,
            "Not in multi templates count mismatch",
        )
