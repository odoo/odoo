import logging
from collections import defaultdict
from unittest.mock import patch

from lxml import etree

from odoo import Command, exceptions, fields
from odoo.tests import Form, TransactionCase, tagged

_logger = logging.getLogger(__name__)


class TestResConfig(TransactionCase):
    def setUp(self):
        super().setUp()
        self.ResConfig = self.env["res.config.settings"]

        self.menu_xml_id = "base.menu_action_res_users"
        self.full_field_name = "res.partner.lang"
        self.error_msg = "WarningRedirect test string: %(field:res.partner.lang)s - %(menu:base.menu_action_res_users)s."
        self.error_msg_wo_menu = (
            "WarningRedirect test string: %(field:res.partner.lang)s."
        )

        menu = self.env.ref(self.menu_xml_id)

        model_name, field_name = self.full_field_name.rsplit(".", 1)

        self.expected_path = menu.complete_name
        self.expected_action_id = menu.action.id
        self.expected_name = self.env[model_name].fields_get([field_name])[field_name][
            "string"
        ]
        self.expected_final_error_msg = self.error_msg % {
            "field:res.partner.lang": self.expected_name,
            "menu:base.menu_action_res_users": self.expected_path,
        }
        self.expected_final_error_msg_wo_menu = self.error_msg_wo_menu % {
            "field:res.partner.lang": self.expected_name,
        }

    def test_00_get_option_path(self):
        res = self.ResConfig.get_option_path(self.menu_xml_id)

        self.assertIsInstance(res, tuple)
        self.assertEqual(len(res), 2, "The result should contain 2 elements")
        self.assertIsInstance(res[0], str)
        self.assertIsInstance(res[1], int)

        self.assertEqual(res[0], self.expected_path)
        self.assertEqual(res[1], self.expected_action_id)

    def test_10_get_option_name(self):
        res = self.ResConfig.get_option_name(self.full_field_name)

        self.assertIsInstance(res, str)

        self.assertEqual(res, self.expected_name)

    def test_20_get_config_warning(self):
        res = self.ResConfig.prepare_config_warning(self.error_msg)

        self.assertIsInstance(res, exceptions.RedirectWarning)

        self.assertEqual(res.args[0], self.expected_final_error_msg)
        self.assertEqual(res.args[1], self.expected_action_id)

    def test_30_get_config_warning_wo_menu(self):
        res = self.ResConfig.prepare_config_warning(self.error_msg_wo_menu)

        self.assertIsInstance(res, exceptions.UserError)

        self.assertEqual(res.args[0], self.expected_final_error_msg_wo_menu)

    def test_40_view_expected_architecture(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "foo",
                "type": "form",
                "model": "res.config.settings",
                "inherit_id": self.env.ref("base.res_config_settings_view_form").id,
                "arch": """
                <xpath expr="//form" position="inside">
                    <t groups="base.group_system">
                        <app data-string="Foo" string="Foo" name="foo">
                            <h2>Foo</h2>
                        </app>
                    </t>
                </xpath>
            """,
            }
        )
        arch = self.env["res.config.settings"].get_view(view.id)["arch"]
        tree = etree.fromstring(arch)
        self.assertTrue(
            tree.xpath("""
            //form[@class="oe_form_configuration"]
            /app[@name="foo"]
        """),
            "The res.config.settings form view architecture is not what is expected by the web client.",
        )

    def test_50_view_expected_architecture_t_node_groups(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "foo",
                "type": "form",
                "model": "res.config.settings",
                "inherit_id": self.env.ref("base.res_config_settings_view_form").id,
                "arch": """
                <xpath expr="//form" position="inside">
                    <t groups="base.group_system">
                        <app data-string="Foo"
                            string="Foo" name="foo" groups="base.group_no_one">
                            <h2>Foo</h2>
                        </app>
                    </t>
                </xpath>
            """,
            }
        )
        with self.debug_mode():
            arch = self.env["res.config.settings"].get_view(view.id)["arch"]
            tree = etree.fromstring(arch)
            self.assertFalse(
                tree.xpath("//t"),
                'The `<t groups="...">` block must not remain in the view',
            )
            self.assertTrue(
                tree.xpath("""
                //form
                /app[@name="foo"]
            """),
                "The `app` block must be a direct child of the `form` block",
            )


@tagged("post_install", "-at_install")
class TestResConfigClassification(TransactionCase):
    def _patched_fields(self, **fake_fields):
        cls = self.env["res.config.settings"].__class__
        return patch.object(cls, "_fields", {**cls._fields, **fake_fields})

    def test_module_field_must_be_boolean(self):
        Settings = self.env["res.config.settings"]
        selection_field = fields.Selection([("0", "No"), ("1", "Yes")])
        with self._patched_fields(module_fake_selection=selection_field):
            with self.assertRaises(TypeError):
                Settings._get_fields_classified(["module_fake_selection"])
        boolean_field = fields.Boolean()
        with self._patched_fields(module_fake_boolean=boolean_field):
            classified = Settings._get_fields_classified(["module_fake_boolean"])
        self.assertFalse(classified["module"])

    def test_group_selection_fields_still_accepted(self):
        Settings = self.env["res.config.settings"]
        group_field = fields.Selection([("0", "No"), ("1", "Yes")])
        group_field.implied_group = "base.group_multi_currency"
        with self._patched_fields(group_fake_selection=group_field):
            classified = Settings._get_fields_classified(["group_fake_selection"])
        self.assertEqual(len(classified["group"]), 1)
        name, groups, implied_group = classified["group"][0]
        self.assertEqual(name, "group_fake_selection")
        self.assertTrue(groups)
        self.assertEqual(implied_group, self.env.ref("base.group_multi_currency"))

    def test_execute_classifies_fields_once(self):
        Settings = self.env["res.config.settings"]
        settings = Settings.create({})
        original = Settings.__class__._get_fields_classified
        full_classifications = []

        def spy(model, fnames=None):
            if fnames is None:
                full_classifications.append(model._name)
            return original(model, fnames)

        with patch.object(
            Settings.__class__, "_get_fields_classified", side_effect=spy, autospec=True
        ):
            settings.execute()
        self.assertEqual(
            len(full_classifications),
            1,
            "execute() must classify the full field set exactly once",
        )

    def test_set_values_standalone_falls_back_lazily(self):
        settings = self.env["res.config.settings"].create({})
        settings.set_values()


@tagged("post_install", "-at_install")
class TestResConfigExecute(TransactionCase):
    def test_01_execute_res_config(self):
        all_config_settings = self.env["ir.model"].search(
            [("name", "like", "config.settings")]
        )
        for config_settings in all_config_settings:
            _logger.info("Testing %s", config_settings.name)
            self.env[config_settings.name].create({}).execute()

    def test_settings_access(self):
        ResUsers = self.env["res.users"]
        group_system = self.env.ref("base.group_system")
        self.settings_view = self.env.ref("base.res_config_settings_view_form")
        settings_only_user = ResUsers.create(
            {
                "name": "Sleepy Joe",
                "login": "sleepy",
                "group_ids": [Command.link(group_system.id)],
            }
        )

        group_order_template = self.env.ref(
            "sale.group_sale_order_template",
            raise_if_not_found=False,
        )
        if group_order_template:
            self.env.ref("base.group_user").write(
                {"implied_ids": [(4, group_order_template.id)]}
            )

        _logger.info("Testing settings access for group %s", group_system.full_name)
        forbidden_models = self._test_user_settings_fields_access(settings_only_user)
        self._test_user_settings_view_save(settings_only_user)

        for model in forbidden_models:
            _logger.warning(
                "Settings user doesn't have read access to the model %s", model
            )

    def _test_user_settings_fields_access(self, user):
        settings = self.env["res.config.settings"].with_user(user).create({})

        settings.set_values()

        settings_view_arch = etree.fromstring(
            settings.get_view(view_id=self.settings_view.id)["arch"]
        )
        seen_fields = set()
        for node in settings_view_arch.iterdescendants(tag="field"):
            fname = node.get("name")
            if fname not in settings._fields:
                continue
            seen_fields.add(fname)

        models_to_check = defaultdict(set)
        for field_name in seen_fields:
            field = settings._fields[field_name]
            if field.relational:
                models_to_check[field.comodel_name].add(field)

        forbidden_models_fields = defaultdict(set)
        for model in models_to_check:
            has_read_access = self.env[model].with_user(user).has_access("read")
            if not has_read_access:
                forbidden_models_fields[model] = models_to_check[model]

        return forbidden_models_fields

    def _test_user_settings_view_save(self, user):
        ResConfigSettings = self.env["res.config.settings"].with_user(user)

        settings_form = Form(ResConfigSettings)
        settings_form.save()
