from contextlib import contextmanager

from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tools.convert import xml_import
from odoo.tools.misc import mute_logger

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


@contextmanager
def registry_loading(registry, loading):
    previous = registry.ready
    registry.ready = not loading
    try:
        yield
    finally:
        registry.ready = previous


@contextmanager
def module_marked_loaded(registry, module):
    registry.loaded_modules.add(module)
    try:
        yield
    finally:
        registry.loaded_modules.discard(module)


class TestACL(TransactionCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.TEST_GROUP = "base.base_test_group"
        cls.test_group = cls.env["res.groups"].create(
            {
                "name": "test with implied user",
                "implied_ids": [Command.link(cls.env.ref("base.group_user").id)],
            }
        )
        cls.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "base_test_group",
                "model": "res.groups",
                "res_id": cls.test_group.id,
            }
        )

    def _set_field_groups(self, model, field_name, groups):
        field = model._fields[field_name]
        self.patch(field, "groups", groups)
        self.env.invalidate_all()
        self.env.registry.clear_cache("templates")

    def test_reading_every_field_leaves_out_an_x2many_whose_model_is_unreadable(self):
        self.env["ir.model.access"].search(
            [("model_id.model", "=", "res.partner.tag")]
        ).perm_read = False
        partner = self.user_demo.partner_id
        demo_partner = partner.with_user(self.user_demo)
        self.assertFalse(
            self.env["res.partner.tag"].with_user(self.user_demo).has_access("read")
        )
        for rows in (
            demo_partner.read(),
            demo_partner.search_read([("id", "=", partner.id)]),
        ):
            self.assertIn("name", rows[0])
            self.assertNotIn("tag_ids", rows[0])
        self.assertIn("tag_ids", partner.read()[0])

    def test_field_visibility_restriction(self):
        currency = self.env["res.currency"].with_user(self.user_demo)

        primary = self.env["ir.ui.view"].create(
            {
                "name": "Add separate label for decimal_places",
                "model": "res.currency",
                "type": "form",
                "priority": 1,
                "arch": """<form>
                <group>
                    <group string="Price Accuracy">
                        <field name="rounding"/>
                        <label for="decimal_places"/>
                        <field name="decimal_places" nolabel="1"/>
                    </group>
                </group>
            </form>""",
            }
        )

        original_fields = currency.fields_get([])
        form_view = currency.get_view(primary.id, "form")
        view_arch = etree.fromstring(form_view.get("arch"))
        has_group_test = self.user_demo.has_group(self.TEST_GROUP)
        self.assertFalse(
            has_group_test,
            "`demo` user should not belong to the restricted group before the test",
        )
        self.assertIn(
            "decimal_places",
            original_fields,
            "'decimal_places' field must be properly visible before the test",
        )
        self.assertNotEqual(
            view_arch.xpath("//field[@name='decimal_places'][@nolabel='1']"),
            [],
            "Field 'decimal_places' must be found in view definition before the test",
        )
        self.assertNotEqual(
            view_arch.xpath("//label[@for='decimal_places']"),
            [],
            "Label for 'decimal_places' must be found in view definition before the test",
        )

        self._set_field_groups(currency, "decimal_places", self.TEST_GROUP)

        fields = currency.fields_get([])
        form_view = currency.get_view(primary.id, "form")
        view_arch = etree.fromstring(form_view.get("arch"))
        self.assertNotIn(
            "decimal_places", fields, "'decimal_places' field should be gone"
        )
        self.assertEqual(
            view_arch.xpath("//field[@name='decimal_places']"),
            [],
            "Field 'decimal_places' must not be found in view definition",
        )
        self.assertEqual(
            view_arch.xpath("//label[@for='decimal_places']"),
            [],
            "Label for 'decimal_places' must not be found in view definition",
        )

        self.test_group.user_ids += self.user_demo
        has_group_test = self.user_demo.has_group(self.TEST_GROUP)
        fields = currency.fields_get([])
        form_view = currency.get_view(primary.id, "form")
        view_arch = etree.fromstring(form_view.get("arch"))
        self.assertTrue(
            has_group_test,
            "`demo` user should now belong to the restricted group",
        )
        self.assertIn(
            "decimal_places",
            fields,
            "'decimal_places' field must be properly visible again",
        )
        self.assertNotEqual(
            view_arch.xpath("//field[@name='decimal_places']"),
            [],
            "Field 'decimal_places' must be found in view definition again",
        )
        self.assertNotEqual(
            view_arch.xpath("//label[@for='decimal_places']"),
            [],
            "Label for 'decimal_places' must be found in view definition again",
        )

    @mute_logger("odoo.models")
    def test_field_crud_restriction(self):
        partner = self.env["res.partner"].browse(1).with_user(self.user_demo)

        has_group_test = self.user_demo.has_group(self.TEST_GROUP)
        self.assertFalse(
            has_group_test,
            "`demo` user should not belong to the restricted group",
        )
        self.assertTrue(partner.read(["bank_ids"]))
        self.assertTrue(partner.write({"bank_ids": []}))

        self._set_field_groups(partner, "bank_ids", self.TEST_GROUP)

        with self.assertRaises(AccessError):
            partner.search_fetch([], ["bank_ids"])
        with self.assertRaises(AccessError):
            partner.fetch(["bank_ids"])
        with self.assertRaises(AccessError):
            partner.read(["bank_ids"])
        with self.assertRaises(AccessError):
            partner.write({"bank_ids": []})

        self.test_group.user_ids += self.user_demo
        has_group_test = self.user_demo.has_group(self.TEST_GROUP)
        self.assertTrue(
            has_group_test,
            "`demo` user should now belong to the restricted group",
        )
        self.assertTrue(partner.read(["bank_ids"]))
        self.assertTrue(partner.write({"bank_ids": []}))

    @mute_logger("odoo.models")
    def test_fields_browse_restriction(self):
        partner = self.env["res.partner"].with_user(self.user_demo)
        self._set_field_groups(partner, "email", self.TEST_GROUP)

        partner = partner.search([], limit=1)
        _ = partner.name
        with self.assertRaises(AccessError):
            with mute_logger("odoo.models"):
                _ = partner.email

    def test_view_create_edit_button(self):
        methods = ["create", "edit", "delete"]
        company = self.env["res.company"].with_user(self.user_demo)
        company_view = company.get_view(False, "form")
        view_arch = etree.fromstring(company_view["arch"])

        for method in methods:
            self.assertEqual(view_arch.get(method), "False")

        company = self.env["res.company"].with_user(self.env.ref("base.user_admin"))
        company_view = company.get_view(False, "form")
        view_arch = etree.fromstring(company_view["arch"])
        for method in methods:
            self.assertIsNone(view_arch.get(method))

    def test_m2o_field_create_edit(self):
        methods = ["create", "write"]
        company = self.env["res.company"].with_user(self.user_demo)
        company_view = company.get_view(False, "form")
        view_arch = etree.fromstring(company_view["arch"])
        field_node = view_arch.xpath("//field[@name='currency_id']")
        self.assertTrue(
            len(field_node), "currency_id field should be in company from view"
        )
        for method in methods:
            self.assertEqual(field_node[0].get("can_" + method), "False")

        company = self.env["res.company"].with_user(self.env.ref("base.user_admin"))
        company_view = company.get_view(False, "form")
        view_arch = etree.fromstring(company_view["arch"])
        field_node = view_arch.xpath("//field[@name='currency_id']")
        for method in methods:
            self.assertEqual(field_node[0].get("can_" + method), "True")

    def test_get_views_fields(self):
        Partner = self.env["res.partner"]
        self._set_field_groups(Partner, "email", self.TEST_GROUP)
        views = Partner.with_user(self.user_demo).get_views([(False, "form")])
        self.assertFalse("email" in views["models"]["res.partner"]["fields"])
        self.user_demo.group_ids = [Command.link(self.test_group.id)]
        views = Partner.with_user(self.user_demo).get_views([(False, "form")])
        self.assertTrue("email" in views["models"]["res.partner"]["fields"])


class TestIrRule(TransactionCaseWithUserDemo):
    def test_a_rule_evaluated_record_by_record_fetches_the_batch_once(self):
        self.env["ir.rule"].create(
            {
                "name": "partners of a company",
                "model_id": self.env.ref("base.model_res_partner").id,
                "domain_force": "[('company_id', 'in', [False] + company_ids)]",
                "groups": [Command.set(self.env.ref("base.group_user").ids)],
            }
        )
        partners = self.env["res.partner"].create(
            [{"name": f"rule batch {i}"} for i in range(60)]
        )
        self.env.flush_all()
        self.env.invalidate_all()
        as_demo = partners.with_user(self.user_demo)
        # the first write pays for the user, its groups, the rules and the
        # batch's rows: every later write checks the rule on its one record,
        # which keeps the batch's prefetch ids, so no row is fetched alone
        as_demo[0].write({"comment": "note 0"})
        with self.assertQueryCount(8):
            for index, partner in enumerate(as_demo[1:], start=1):
                partner.write({"comment": f"note {index}"})
            self.env.flush_all()
        self.assertEqual(partners[3].comment, "<p>note 3</p>")

    def test_ir_rule(self):
        model_res_partner = self.env.ref("base.model_res_partner")
        group_user = self.env.ref("base.group_user")

        rule1 = self.env["ir.rule"].create(
            {
                "name": "test_rule1",
                "model_id": model_res_partner.id,
                "domain_force": False,
                "groups": [Command.set(group_user.ids)],
            }
        )

        partners_demo = self.env["res.partner"].with_user(self.user_demo)
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        rule1.domain_force = "[(1,'=',1)]"
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        rule1.domain_force = "[]"
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        rule2 = self.env["ir.rule"].create(
            {
                "name": "test_rule2",
                "model_id": model_res_partner.id,
                "domain_force": False,
                "groups": [Command.set(group_user.ids)],
            }
        )

        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        rule1.domain_force = "[(1,'=',1)]"
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        rule2.domain_force = "[(1,'=',1)]"
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        rule3 = self.env["ir.rule"].create(
            {
                "name": "test_rule3",
                "model_id": model_res_partner.id,
                "domain_force": False,
                "groups": [Command.set(group_user.ids)],
            }
        )

        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        rule3.domain_force = "[(1,'=',1)]"
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        global_rule = self.env.ref("base.res_company_rule_employee")
        global_rule.domain_force = "[('id','in', company_ids)]"

        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        rule2.domain_force = "[('id','=',False),('name','=',False)]"

        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        group_test = self.env["res.groups"].create(
            {
                "name": "Test Group",
                "user_ids": [Command.set(self.user_demo.ids)],
            }
        )

        rule3.write(
            {
                "domain_force": "[('name','!=',False),('id','!=',False)]",
                "groups": [Command.set(group_test.ids)],
            }
        )

        partners = partners_demo.search([])
        self.assertTrue(
            partners,
            "Demo user should see partners even with the combined rules.",
        )

        self.env["ir.rule"].search([("groups", "=", False)]).unlink()

        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partners.")

    def test_ir_rule_superuser_bypass(self):
        model_res_partner = self.env.ref("base.model_res_partner")
        self.env["ir.rule"].create(
            {
                "name": "test_rule_su_bypass",
                "model_id": model_res_partner.id,
                "domain_force": "[('id', '=', False)]",
            }
        )

        su_rule = self.env(su=True)["ir.rule"]
        self.assertFalse(
            su_rule._get_rules("res.partner", "read"),
            "Superuser must get no record rules (env.su bypass).",
        )
        self.assertTrue(
            su_rule._get_domain_accessible_records("res.partner", "read").is_true(),
            "Superuser domain must be unrestricted (Domain.TRUE).",
        )

        demo_rule = self.env(user=self.user_demo)["ir.rule"]
        self.assertTrue(
            demo_rule._get_rules("res.partner", "read"),
            "Demo user must get the global rule.",
        )
        self.assertFalse(
            demo_rule._get_domain_accessible_records("res.partner", "read").is_true(),
            "Demo user domain must be restricted by the global rule.",
        )

    def test_ir_rule_get_rules_modes(self):
        model_res_partner = self.env.ref("base.model_res_partner")
        group_user = self.env.ref("base.group_user")
        unlink_rule = self.env["ir.rule"].create(
            {
                "name": "test_rule_unlink_only",
                "model_id": model_res_partner.id,
                "domain_force": "[('id', '!=', False)]",
                "groups": [Command.set(group_user.ids)],
                "perm_read": False,
                "perm_write": False,
                "perm_create": False,
                "perm_unlink": True,
            }
        )

        demo_rule = self.env(user=self.user_demo)["ir.rule"]
        self.assertIn(
            unlink_rule,
            demo_rule._get_rules("res.partner", "unlink"),
            "Rule with only perm_unlink must appear for the 'unlink' mode.",
        )
        for mode in ("read", "write", "create"):
            self.assertNotIn(
                unlink_rule,
                demo_rule._get_rules("res.partner", mode),
                f"Unlink-only rule must not appear for the {mode!r} mode.",
            )

        with self.assertRaises(ValueError):
            demo_rule._get_rules("res.partner", "bogus")

    def _registry_loading(self, loading):
        return registry_loading(self.env.registry, loading)

    def _restricting_rule_from(self, module, name):
        rule = self.env["ir.rule"].create(
            {
                "name": name,
                "model_id": self.env.ref("base.model_res_partner").id,
                "domain_force": "[('id', '=', False)]",
            }
        )
        self.env["ir.model.data"].create(
            {"module": module, "name": name, "model": "ir.rule", "res_id": rule.id}
        )
        return rule

    def test_ir_rule_of_the_module_being_loaded_applies_to_its_own_files(self):
        self._restricting_rule_from("a_module_being_loaded", "test_rule_own_files")
        demo_partner = self.env(user=self.user_demo)["res.partner"]

        with self._registry_loading(True):
            self.assertTrue(demo_partner.search_count([]))
            self.assertTrue(
                demo_partner.with_context(install_module="another_module").search_count(
                    []
                )
            )
            self.assertEqual(
                demo_partner.with_context(
                    install_module="a_module_being_loaded"
                ).search_count([]),
                0,
                "A record in the module's own data or demo files must be bound by "
                "the rules that module ships",
            )

    def test_ir_rule_domain_computed_while_loading_does_not_outlive_the_module_loading(
        self,
    ):
        self._restricting_rule_from("a_module_being_loaded", "test_rule_generation")
        demo_partner = self.env(user=self.user_demo)["res.partner"]

        with self._registry_loading(True):
            self.assertTrue(demo_partner.search_count([]))
            with module_marked_loaded(self.env.registry, "a_module_being_loaded"):
                self.assertEqual(
                    demo_partner.search_count([]),
                    0,
                    "A domain computed before a module was loaded must not be "
                    "served once it is",
                )

    def test_ir_rule_from_an_unloaded_module_is_skipped_while_loading(self):
        model_res_partner = self.env.ref("base.model_res_partner")
        rule = self.env["ir.rule"].create(
            {
                "name": "test_rule_from_a_later_module",
                "model_id": model_res_partner.id,
                "domain_force": "[('id', '!=', False)]",
            }
        )
        self.env["ir.model.data"].create(
            {
                "module": "a_module_this_registry_has_not_loaded",
                "name": "test_rule_from_a_later_module",
                "model": "ir.rule",
                "res_id": rule.id,
            }
        )
        demo_rule = self.env(user=self.user_demo)["ir.rule"]

        with self._registry_loading(False):
            self.assertIn(rule, demo_rule._get_rules("res.partner", "read"))

        with self._registry_loading(True):
            self.assertNotIn(rule, demo_rule._get_rules("res.partner", "read"))
            hand_written = self.env["ir.rule"].create(
                {
                    "name": "test_rule_written_by_hand",
                    "model_id": model_res_partner.id,
                    "domain_force": "[('id', '!=', False)]",
                }
            )
            self.assertIn(hand_written, demo_rule._get_rules("res.partner", "read"))

    def test_ir_rule_domain_computed_while_loading_is_not_reused_after(self):
        model_res_partner = self.env.ref("base.model_res_partner")
        rule = self.env["ir.rule"].create(
            {
                "name": "test_rule_cache_key_on_init",
                "model_id": model_res_partner.id,
                "domain_force": "[('id', '=', False)]",
            }
        )
        self.env["ir.model.data"].create(
            {
                "module": "a_module_this_registry_has_not_loaded",
                "name": "test_rule_cache_key_on_init",
                "model": "ir.rule",
                "res_id": rule.id,
            }
        )
        demo_partner = self.env(user=self.user_demo)["res.partner"]

        with self._registry_loading(True):
            self.assertTrue(
                demo_partner.search_count([]),
                "A rule from an unloaded module must not restrict during loading",
            )

        with self._registry_loading(False):
            self.assertEqual(
                demo_partner.search_count([]),
                0,
                "The loading-time domain must not survive into a serving registry",
            )

    @mute_logger("odoo.addons.base.models.ir_rule", "odoo.models")
    def test_ir_rule_access_error_message(self):
        model_res_partner = self.env.ref("base.model_res_partner")
        group_user = self.env.ref("base.group_user")

        partner = self.env["res.partner"].create({"name": "T3 partner"})

        self.env["ir.rule"].create(
            {
                "name": "test_rule_t3_deny",
                "model_id": model_res_partner.id,
                "domain_force": "[('id', '=', False)]",
                "groups": [Command.set(group_user.ids)],
            }
        )

        partner_demo = partner.with_user(self.user_demo)
        with self.assertRaises(AccessError):
            partner_demo.check_access("read")

        UserCls = type(self.env.user)
        original_has_group = UserCls.has_group

        def fake_has_group(user, group_ext_id):
            if group_ext_id == "base.group_no_one":
                return True
            return original_has_group(user, group_ext_id)

        rule_env = self.env(user=self.user_demo)["ir.rule"]
        self.patch(UserCls, "has_group", fake_has_group)
        exception = rule_env._prepare_access_error("read", partner_demo)
        self.assertIn(
            "test_rule_t3_deny",
            str(exception),
            "Debug access-error message should name the blaming rule.",
        )

    def _partner_rule(self, name, domain, groups, composition="grant"):
        return self.env["ir.rule"].create(
            {
                "name": name,
                "model_id": self.env.ref("base.model_res_partner").id,
                "domain_force": domain,
                "groups": [Command.set(groups.ids)],
                "composition": composition,
            }
        )

    def test_a_grant_rule_widens_what_another_grant_rule_denied(self):
        group_user = self.env.ref("base.group_user")
        partner = self.env["res.partner"].create({"name": "composition partner"})
        self._partner_rule("deny", "[('id', '=', False)]", group_user)
        with self.assertRaises(AccessError):
            partner.with_user(self.user_demo).check_access("read")
        self._partner_rule("allow everything", "[]", group_user)
        partner.with_user(self.user_demo).check_access("read")

    def test_a_restrict_rule_is_not_widened_by_a_grant_rule(self):
        group_user = self.env.ref("base.group_user")
        partner = self.env["res.partner"].create({"name": "composition partner"})
        self._partner_rule("allow everything", "[]", group_user)
        self._partner_rule(
            "deny for members", "[('id', '=', False)]", group_user, "restrict"
        )
        demo_partner = partner.with_user(self.user_demo)
        with self.assertRaises(AccessError):
            demo_partner.check_access("read")
        blamed = self.env(user=self.user_demo)["ir.rule"]._get_failing(
            demo_partner, "read"
        )
        self.assertEqual(blamed.mapped("name"), ["deny for members"])

    def test_a_restrict_rule_binds_only_its_own_group(self):
        group_system = self.env.ref("base.group_system")
        partner = self.env["res.partner"].create({"name": "composition partner"})
        self._partner_rule(
            "deny for admins only", "[('id', '=', False)]", group_system, "restrict"
        )
        partner.with_user(self.user_demo).check_access("read")


class TestIrModelAccess(TransactionCaseWithUserDemo):
    def test_invalid_access_mode(self):
        Access = self.env["ir.model.access"]
        with self.assertRaises(ValueError):
            Access._get_models_allowed("foo")
        with self.assertRaises(ValueError):
            Access.group_names_with_access("res.partner", "foo")
        with self.assertRaises(ValueError):
            Access._get_groups_with_access("res.partner", "foo")

    @mute_logger("odoo.addons.base.models.ir_model_access", "odoo.db.cursor")
    def test_create_missing_name_raises_field_error(self):
        model_partner = self.env.ref("base.model_res_partner")
        with self.assertRaises(Exception) as cm:
            self.env["ir.model.access"].create(
                [
                    {
                        "model_id": model_partner.id,
                        "group_id": False,
                        "perm_read": True,
                    }
                ]
            )
        self.assertNotIsInstance(
            cm.exception, KeyError, "Missing 'name' must not raise KeyError."
        )

    def test_create_omitted_group_warns(self):
        model_partner = self.env.ref("base.model_res_partner")
        with self.assertLogs(
            "odoo.addons.base.models.ir_model_access", level="WARNING"
        ) as log_cm:
            self.env["ir.model.access"].create(
                {
                    "name": "acl_no_group_omitted",
                    "model_id": model_partner.id,
                    "perm_read": True,
                }
            )
        self.assertTrue(
            any("has no group" in msg for msg in log_cm.output),
            "Omitting group_id on an access-granting ACL must warn.",
        )

    def test_cache_clearing_invalidates_both_acl_caches(self):
        Access = self.env["ir.model.access"]
        registry = self.env.registry
        caches = registry.ormcache_lrus

        def cached(bucket, method_name):
            return [
                key
                for key in caches[bucket].snapshot
                if getattr(key[1], "__name__", None) == method_name
            ]

        registry.clear_all_caches()
        Access._get_models_allowed("read")
        Access._get_groups_with_access("res.partner", "read")
        self.assertTrue(
            cached("default", "_get_models_allowed"),
            "_get_models_allowed should populate the 'default' bucket.",
        )
        self.assertTrue(
            cached("stable", "_get_groups_with_access"),
            "_get_groups_with_access should populate the 'stable' bucket.",
        )

        Access.call_cache_clearing_methods()
        self.assertFalse(
            cached("default", "_get_models_allowed"),
            "_get_models_allowed (default bucket) must be invalidated.",
        )
        self.assertFalse(
            cached("stable", "_get_groups_with_access"),
            "_get_groups_with_access (stable bucket) must be invalidated.",
        )

    def test_allowed_models_cache_shared_across_same_group_users(self):
        self.addCleanup(self.env.registry.clear_cache)
        group_user = self.env.ref("base.group_user")
        user_a, user_b = self.env["res.users"].create(
            [
                {
                    "name": f"acl cache twin {letter}",
                    "login": f"acl_cache_twin_{letter}",
                    "group_ids": [Command.set(group_user.ids)],
                }
                for letter in "ab"
            ]
        )
        self.assertEqual(user_a._get_group_ids(), user_b._get_group_ids())
        Access = self.env["ir.model.access"]
        allowed_a = Access.with_user(user_a)._get_models_allowed("read")
        allowed_b = Access.with_user(user_b)._get_models_allowed("read")
        self.assertIs(
            allowed_a,
            allowed_b,
            "Same-group users must share one _get_models_allowed cache entry.",
        )
        self.assertIsNot(
            allowed_a, Access.with_user(user_a)._get_models_allowed("write")
        )

    def test_check_unknown_model_warns(self):
        Access = self.env["ir.model.access"].with_user(self.user_demo)
        with self.assertLogs(
            "odoo.addons.base.models.ir_model_access", level="WARNING"
        ) as log_cm:
            result = Access.check("no.such.model", "read", raise_exception=False)
        self.assertFalse(result, "Access to an unknown model must be denied.")
        self.assertTrue(
            any("no.such.model" in msg for msg in log_cm.output),
            "Unknown model must be logged at WARNING.",
        )

    def test_group_names_with_access_localized_ordering(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        model_partner = self.env.ref("base.model_res_partner")
        Groups = self.env["res.groups"]

        group_a = Groups.create({"name": "ZZZ_alpha"})
        group_b = Groups.create({"name": "ZZZ_beta"})
        group_a.with_context(lang="fr_FR").name = "ZZZ_zulu"
        group_b.with_context(lang="fr_FR").name = "ZZZ_mike"

        for group in (group_a, group_b):
            self.env["ir.model.access"].create(
                {
                    "name": f"acl_{group.name}",
                    "model_id": model_partner.id,
                    "group_id": group.id,
                    "perm_read": True,
                }
            )

        Access = self.env["ir.model.access"].with_context(lang="fr_FR")
        names = Access.group_names_with_access("res.partner", "read")
        ours = [n for n in names if n in ("ZZZ_zulu", "ZZZ_mike")]
        self.assertEqual(
            ours,
            ["ZZZ_mike", "ZZZ_zulu"],
            "Groups must be ordered by localized (fr_FR) name.",
        )


class TestIrModelAccessWhileLoading(TransactionCaseWithUserDemo):
    MODEL = "ir.config_parameter"
    MODULE = "a_module_being_loaded"

    def setUp(self):
        super().setUp()
        acl = self.env["ir.model.access"].create(
            {
                "name": "test_acl_from_a_loading_module",
                "model_id": self.env["ir.model"]._get(self.MODEL).id,
                "group_id": self.env.ref("base.group_user").id,
                "perm_read": True,
            }
        )
        self.env["ir.model.data"].create(
            {
                "module": self.MODULE,
                "name": "test_acl_from_a_loading_module",
                "model": "ir.model.access",
                "res_id": acl.id,
            }
        )
        self.access = self.env(user=self.user_demo)["ir.model.access"]

    def _allowed(self, **context):
        return self.access.with_context(**context)._get_models_allowed("read")

    def test_acl_from_an_unloaded_module_is_skipped_while_loading(self):
        with registry_loading(self.env.registry, False):
            self.assertIn(self.MODEL, self._allowed())
        with registry_loading(self.env.registry, True):
            self.assertNotIn(self.MODEL, self._allowed())

    def test_acl_of_the_module_being_loaded_applies_to_its_own_files(self):
        with registry_loading(self.env.registry, True):
            self.assertNotIn(self.MODEL, self._allowed(install_module="another_module"))
            self.assertIn(
                self.MODEL,
                self._allowed(install_module=self.MODULE),
                "A `uid=` record in a module's own data or demo files must be "
                "granted what that module's access rows grant",
            )

    def test_a_uid_function_in_the_module_files_acts_under_its_access_rows(self):
        self.env["ir.model.data"].create(
            {
                "module": self.MODULE,
                "name": "test_loading_user",
                "model": "res.users",
                "res_id": self.user_demo.id,
            }
        )
        doc = etree.fromstring(
            f'<odoo><function model="{self.MODEL}" name="search_count" '
            f'uid="test_loading_user" eval="[[]]"/></odoo>'
        )

        with registry_loading(self.env.registry, True):
            xml_import(self.env, self.MODULE, {}, "init").parse(doc)

    def test_acl_answer_computed_while_loading_does_not_outlive_the_module_loading(
        self,
    ):
        with registry_loading(self.env.registry, True):
            self.assertNotIn(self.MODEL, self._allowed())
            with module_marked_loaded(self.env.registry, self.MODULE):
                self.assertIn(
                    self.MODEL,
                    self._allowed(),
                    "An answer computed before a module was loaded must not be "
                    "served once it is",
                )


class TestIrModelAccessUnknownModel(TransactionCaseWithUserDemo):
    def test_unknown_model_raises_clear_error(self):
        Access = self.env["ir.model.access"].with_user(self.user_demo)
        with self.assertRaises(ValueError) as capture:
            Access.check("no.such.model")
        self.assertIn("no.such.model", str(capture.exception))

    @mute_logger("odoo.addons.base.models.ir_model_access")
    def test_unknown_model_lenient_path_returns_false(self):
        Access = self.env["ir.model.access"].with_user(self.user_demo)
        self.assertFalse(Access.check("no.such.model", raise_exception=False))

    def test_unknown_model_superuser_short_circuit(self):
        self.assertTrue(self.env["ir.model.access"].sudo().check("no.such.model"))


class TestIrModelAccessCacheInvalidation(TransactionCaseWithUserDemo):
    def _granting_acls(self, model_name, user, mode="write"):
        group_ids = set(user._get_group_ids())
        return (
            self.env["ir.model.access"]
            .sudo()
            .search(
                [
                    ("model_id", "=", self.env["ir.model"]._get(model_name).id),
                    (f"perm_{mode}", "=", True),
                    ("active", "=", True),
                ]
            )
            .filtered(lambda a: not a.group_id or a.group_id.id in group_ids)
        )

    def test_revoke_takes_effect_in_the_writing_worker(self):
        admin = self.env.ref("base.user_admin")
        Access = self.env(user=admin.id)["ir.model.access"]
        acls = self._granting_acls("res.partner", admin)
        self.assertTrue(acls, "expected admin to have a write ACL on res.partner")

        self.env.flush_all()
        self.env.registry.clear_cache()
        self.assertIn("res.partner", Access._get_models_allowed("write"))

        Access.browse(acls.ids).write({"perm_write": False})

        self.assertNotIn(
            "res.partner",
            Access._get_models_allowed("write"),
            "revoking a model ACL must take effect in the worker that revoked it",
        )

    def test_grant_takes_effect_in_the_writing_worker(self):
        admin = self.env.ref("base.user_admin")
        Access = self.env(user=admin.id)["ir.model.access"]
        acls = self._granting_acls("res.partner", admin)
        Access.browse(acls.ids).write({"perm_write": False})
        self.env.registry.clear_cache()
        self.assertNotIn("res.partner", Access._get_models_allowed("write"))

        Access.browse(acls.ids).write({"perm_write": True})

        self.assertIn("res.partner", Access._get_models_allowed("write"))

    def test_unlink_takes_effect_in_the_writing_worker(self):
        admin = self.env.ref("base.user_admin")
        Access = self.env(user=admin.id)["ir.model.access"]
        acls = self._granting_acls("res.partner", admin, mode="unlink")
        self.assertTrue(acls, "expected admin to have an unlink ACL on res.partner")
        self.env.flush_all()
        self.env.registry.clear_cache()
        self.assertIn("res.partner", Access._get_models_allowed("unlink"))

        Access.browse(acls.ids).unlink()

        self.assertNotIn("res.partner", Access._get_models_allowed("unlink"))


class TestResGroupsCacheInvalidation(TransactionCaseWithUserDemo):
    def test_self_affecting_implication_revoke_takes_effect(self):
        admin = self.env.ref("base.user_admin")
        holder = self.env["res.groups"].sudo().create({"name": "rgl4_holder"})
        granter = self.env["res.groups"].sudo().create({"name": "rgl4_granter"})
        holder.write({"implied_ids": [Command.link(granter.id)]})
        admin.sudo().write({"group_ids": [Command.link(holder.id)]})
        self.env.flush_all()
        self.env.registry.clear_cache()
        self.assertIn(granter.id, admin._get_group_ids())

        self.env(user=admin.id)["res.groups"].browse(holder.id).write(
            {"implied_ids": [Command.unlink(granter.id)]}
        )

        self.assertNotIn(
            granter.id,
            admin._get_group_ids(),
            "revoking an implication from a group the writer holds must take"
            " effect in the writing worker",
        )

    def test_self_affecting_implication_grant_takes_effect(self):
        admin = self.env.ref("base.user_admin")
        holder = self.env["res.groups"].sudo().create({"name": "rgl4_holder2"})
        granter = self.env["res.groups"].sudo().create({"name": "rgl4_granter2"})
        admin.sudo().write({"group_ids": [Command.link(holder.id)]})
        self.env.flush_all()
        self.env.registry.clear_cache()
        self.assertNotIn(granter.id, admin._get_group_ids())

        self.env(user=admin.id)["res.groups"].browse(holder.id).write(
            {"implied_ids": [Command.link(granter.id)]}
        )

        self.assertIn(granter.id, admin._get_group_ids())


class TestResGroupsFullNameOrder(TransactionCaseWithUserDemo):
    def test_full_name_desc_is_case_insensitive(self):
        Groups = self.env["res.groups"]
        ascending = Groups.search([], order="full_name").mapped("full_name")
        self.assertTrue(len(ascending) > 1, "precondition: several groups exist")
        for spec in ("full_name desc", "full_name DESC", "full_name Desc"):
            with self.subTest(order=spec):
                descending = Groups.search([], order=spec).mapped("full_name")
                self.assertEqual(
                    descending,
                    list(reversed(ascending)),
                    "any spelling of a descending sort must reverse the order",
                )


class TestFieldDescriptionCachePerGroupSet(TransactionCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env["res.users"]
        Partner = cls.env["res.partner"]
        cls.internal_user = Users.create(
            {
                "login": "fdesc_internal",
                "partner_id": Partner.create({"name": "FDesc Internal"}).id,
                "group_ids": [Command.set([cls.env.ref("base.group_user").id])],
            }
        )
        cls.portal_user = Users.create(
            {
                "login": "fdesc_portal",
                "partner_id": Partner.create({"name": "FDesc Portal"}).id,
                "group_ids": [Command.set([cls.env.ref("base.group_portal").id])],
            }
        )

    def _answers(self, user, model_name, fname):
        env = self.env(user=user.id)
        field = env[model_name]._fields[fname]
        return (field._description_sortable(env), field._description_groupable(env))

    def test_two_group_sets_do_not_share_an_answer(self):
        internal_first = self._answers(self.internal_user, "res.partner", "tag_ids")
        portal_after = self._answers(self.portal_user, "res.partner", "tag_ids")

        self.assertNotEqual(
            internal_first,
            portal_after,
            "a portal user must not be served the internal user's cached answer",
        )
        self.assertEqual(
            self._answers(self.internal_user, "res.partner", "tag_ids"),
            internal_first,
            "and the internal user's answer must survive the portal read",
        )

    def test_the_order_the_users_ask_in_does_not_matter(self):
        portal_first = self._answers(self.portal_user, "res.partner", "tag_ids")
        internal_after = self._answers(self.internal_user, "res.partner", "tag_ids")
        self.env.registry.clear_cache()

        self.assertEqual(
            self._answers(self.portal_user, "res.partner", "tag_ids"),
            portal_first,
        )
        self.assertEqual(
            self._answers(self.internal_user, "res.partner", "tag_ids"),
            internal_after,
        )

    def test_a_cached_answer_matches_a_freshly_computed_one(self):
        env = self.env(user=self.internal_user.id)
        model = env["res.users"]
        for fname, field in model._fields.items():
            warm = (field._description_sortable(env), field._description_groupable(env))
            self.env.registry.clear_cache()
            cold = (field._description_sortable(env), field._description_groupable(env))
            self.assertEqual(
                warm, cold, f"cached and freshly computed must agree for {fname!r}"
            )
