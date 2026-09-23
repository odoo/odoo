from contextlib import contextmanager

from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tools.convert import convert_csv_import, xml_import
from odoo.tools.misc import mute_logger

from odoo.addons.base.tests.common import (
    TransactionCaseWithUserDemo,
    make_access_row,
    make_guard_row,
)


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
        self.env["ir.access"].search(
            [
                ("model_id.model", "=", "res.partner.tag"),
                ("kind", "=", "permission"),
                ("for_read", "=", True),
            ]
        ).active = False
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
        self.assertTrue(partner.read(["bank_account_ids"]))
        self.assertTrue(partner.write({"bank_account_ids": []}))

        self._set_field_groups(partner, "bank_account_ids", self.TEST_GROUP)

        with self.assertRaises(AccessError):
            partner.search_fetch([], ["bank_account_ids"])
        with self.assertRaises(AccessError):
            partner.fetch(["bank_account_ids"])
        with self.assertRaises(AccessError):
            partner.read(["bank_account_ids"])
        with self.assertRaises(AccessError):
            partner.write({"bank_account_ids": []})

        self.test_group.user_ids += self.user_demo
        has_group_test = self.user_demo.has_group(self.TEST_GROUP)
        self.assertTrue(
            has_group_test,
            "`demo` user should now belong to the restricted group",
        )
        self.assertTrue(partner.read(["bank_account_ids"]))
        self.assertTrue(partner.write({"bank_account_ids": []}))

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


class TestAccessRows(TransactionCaseWithUserDemo):
    def _partner_rows(self, **domain):
        return self.env["ir.access"].search(
            [("model_id.model", "=", "res.partner")]
            + [(name, "=", value) for name, value in domain.items()]
        )

    def test_a_rule_evaluated_record_by_record_fetches_the_batch_once(self):
        make_guard_row(
            self.env,
            "res.partner",
            "[('company_id', 'in', [False] + company_ids)]",
            self.env.ref("base.group_user"),
            name="partners of a company",
        )
        partners = self.env["res.partner"].create(
            [{"name": f"rule batch {i}"} for i in range(60)]
        )
        self.env.flush_all()
        self.env.invalidate_all()
        as_demo = partners.with_user(self.user_demo)
        # the first write pays for the user, its groups, the rows and the
        # batch's rows: every later write checks the guard on its one record,
        # which keeps the batch's prefetch ids, so no row is fetched alone
        as_demo[0].write({"comment": "note 0"})
        with self.assertQueryCount(8):
            for index, partner in enumerate(as_demo[1:], start=1):
                partner.write({"comment": f"note {index}"})
            self.env.flush_all()
        self.assertEqual(partners[3].comment, "<p>note 3</p>")

    def test_permissions_and_guards_on_partners(self):
        group_user = self.env.ref("base.group_user")
        partners_demo = self.env["res.partner"].with_user(self.user_demo)

        row1 = make_access_row(self.env, "res.partner", group_user, name="row1")
        self.assertTrue(partners_demo.search([]), "Demo user should see some partner.")
        row1.domain = "[(1,'=',1)]"
        self.assertTrue(partners_demo.search([]), "Demo user should see some partner.")
        row1.domain = "[]"
        self.assertTrue(partners_demo.search([]), "Demo user should see some partner.")

        row2 = make_access_row(self.env, "res.partner", group_user, name="row2")
        row3 = make_access_row(self.env, "res.partner", group_user, name="row3")
        self.assertTrue(partners_demo.search([]), "Demo user should see some partner.")

        self.env.ref(
            "base.res_company_rule_employee"
        ).domain = "[('id','in', company_ids)]"
        self.assertTrue(partners_demo.search([]), "Demo user should see some partner.")

        # a permission only ever adds records: one that admits nothing takes
        # nothing away from the others
        row2.domain = "[('id','=',False),('name','=',False)]"
        self.assertTrue(partners_demo.search([]), "Demo user should see some partner.")

        group_test = self.env["res.groups"].create(
            {"name": "Test Group", "user_ids": [Command.set(self.user_demo.ids)]}
        )
        row3.write(
            {
                "domain": "[('name','!=',False),('id','!=',False)]",
                "group_id": group_test.id,
            }
        )
        self.assertTrue(
            partners_demo.search([]),
            "Demo user should see partners even with the combined rows.",
        )

        self._partner_rows(kind="guard").unlink()
        self.assertTrue(partners_demo.search([]), "Demo user should see some partners.")

    def test_the_superuser_is_bound_by_no_row(self):
        make_guard_row(self.env, "res.partner", "[('id', '=', False)]")
        self.assertTrue(
            self.env(su=True)["res.partner"].search_count([]),
            "The superuser must read past every guard.",
        )
        self.assertEqual(
            self.env(user=self.user_demo)["res.partner"].search_count([]),
            0,
            "The demo user must be bound by the guard.",
        )

    def test_a_row_binds_only_its_operations(self):
        partner = self.env["res.partner"].create({"name": "unlink-only guard"})
        make_guard_row(self.env, "res.partner", "[('id', '=', False)]", operation="d")
        demo_partner = partner.with_user(self.user_demo)
        self.assertEqual(demo_partner._filtered_access("unlink"), demo_partner.browse())
        for mode in ("read", "write"):
            self.assertEqual(
                demo_partner._filtered_access(mode),
                demo_partner,
                f"An unlink-only guard must not bind the {mode!r} mode.",
            )
        with self.assertRaises(ValueError):
            self.env["ir.access"]._operation_letter("bogus")

    def _registry_loading(self, loading):
        return registry_loading(self.env.registry, loading)

    def _restricting_row_from(self, module, name):
        return make_guard_row(
            self.env,
            "res.partner",
            "[('id', '=', False)]",
            name=name,
            xmlid=f"{module}.{name}",
        )

    def _partner_row_ids(self):
        return {
            row.id
            for row in self.env(user=self.user_demo)["ir.access"]
            ._get_all_access()
            .get("res.partner", ())
        }

    def test_a_row_of_the_module_being_loaded_applies_to_its_own_files(self):
        self._restricting_row_from("a_module_being_loaded", "test_rule_own_files")
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
                "the rows that module ships",
            )

    def test_a_domain_computed_while_loading_does_not_outlive_the_module_loading(
        self,
    ):
        self._restricting_row_from("a_module_being_loaded", "test_rule_generation")
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

    def test_a_row_from_an_unloaded_module_is_skipped_while_loading(self):
        row = self._restricting_row_from(
            "a_module_this_registry_has_not_loaded", "test_rule_from_a_later_module"
        )
        row.domain = "[('id', '!=', False)]"

        with self._registry_loading(False):
            self.assertIn(row.id, self._partner_row_ids())

        with self._registry_loading(True):
            self.assertNotIn(row.id, self._partner_row_ids())
            hand_written = make_guard_row(
                self.env,
                "res.partner",
                "[('id', '!=', False)]",
                name="test_rule_written_by_hand",
            )
            self.assertIn(hand_written.id, self._partner_row_ids())

    def test_a_domain_computed_while_loading_is_not_reused_after(self):
        self._restricting_row_from(
            "a_module_this_registry_has_not_loaded", "test_rule_cache_key_on_init"
        )
        demo_partner = self.env(user=self.user_demo)["res.partner"]

        with self._registry_loading(True):
            self.assertTrue(
                demo_partner.search_count([]),
                "A row from an unloaded module must not restrict during loading",
            )

        with self._registry_loading(False):
            self.assertEqual(
                demo_partner.search_count([]),
                0,
                "The loading-time domain must not survive into a serving registry",
            )

    @mute_logger("odoo.addons.base.models.ir_access", "odoo.models")
    def test_the_debug_access_error_names_the_blamed_row(self):
        partner = self.env["res.partner"].create({"name": "T3 partner"})
        make_guard_row(
            self.env,
            "res.partner",
            "[('id', '=', False)]",
            self.env.ref("base.group_user"),
            name="test_rule_t3_deny",
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

        access = self.env(user=self.user_demo)["ir.access"]
        self.patch(UserCls, "has_group", fake_has_group)
        exception = access._make_record_access_error(partner_demo, "read")
        self.assertIn(
            "test_rule_t3_deny",
            str(exception),
            "Debug access-error message should name the blamed row.",
        )

    def test_a_permission_widens_what_another_permission_denied(self):
        # permissions are OR-ed: one admitting nothing, and the user's own
        # see-all rows switched off, deny; another admitting everything allows
        group_user = self.env.ref("base.group_user")
        partner = self.env["res.partner"].create({"name": "composition partner"})
        self._partner_rows(kind="permission").active = False
        make_access_row(
            self.env, "res.partner", group_user, domain="[('id', '=', False)]"
        )
        with self.assertRaises(AccessError):
            partner.with_user(self.user_demo).check_access("read")
        make_access_row(self.env, "res.partner", group_user, name="allow everything")
        partner.with_user(self.user_demo).check_access("read")

    def test_a_member_guard_is_not_widened_by_a_permission(self):
        group_user = self.env.ref("base.group_user")
        partner = self.env["res.partner"].create({"name": "composition partner"})
        make_access_row(self.env, "res.partner", group_user, name="allow everything")
        make_guard_row(
            self.env,
            "res.partner",
            "[('id', '=', False)]",
            group_user,
            name="deny for members",
        )
        demo_partner = partner.with_user(self.user_demo)
        with self.assertRaises(AccessError):
            demo_partner.check_access("read")
        blamed = self.env(user=self.user_demo)["ir.access"]._get_failed_accesses(
            demo_partner, "read"
        )
        self.assertEqual([row.name for row in blamed], ["deny for members"])

    def test_a_member_guard_binds_only_its_own_group(self):
        partner = self.env["res.partner"].create({"name": "composition partner"})
        make_guard_row(
            self.env,
            "res.partner",
            "[('id', '=', False)]",
            self.env.ref("base.group_system"),
            name="deny for admins only",
        )
        partner.with_user(self.user_demo).check_access("read")

    def test_a_row_on_a_table_inheritance_root_binds_its_subtypes(self):
        # an action is read through the root table: a guard on the root binds
        # a window action as it binds the root
        window = self.env["ir.actions.act_window"].search([], limit=1)
        demo_window = window.with_user(self.env.ref("base.user_admin"))
        self.assertTrue(demo_window.has_access("read"))
        make_guard_row(self.env, "ir.actions.actions", "[('id', '!=', %d)]" % window.id)
        self.assertFalse(demo_window.has_access("read"))


class TestIrAccess(TransactionCaseWithUserDemo):
    def test_invalid_access_operation(self):
        with self.assertRaises(ValueError):
            self.env["res.partner"]._access_domain("foo")
        with self.assertRaises(ValueError):
            self.env["ir.access"]._group_names_with_access("res.partner", "foo")
        with self.assertRaises(ValueError):
            self.env["ir.access"]._get_groups_with_access("res.partner", "foo")

    def test_the_access_lines_and_rules_are_gone(self):
        self.assertNotIn("ir.model.access", self.env)
        self.assertNotIn("ir.rule", self.env)
        self.env.cr.execute(
            "SELECT relname FROM pg_class WHERE relname = ANY(%s)",
            [["ir_model_access", "ir_rule", "rule_group_rel"]],
        )
        self.assertEqual(self.env.cr.fetchall(), [])
        self.assertFalse(
            self.env["ir.model.data"].search_count(
                [("model", "in", ("ir.model.access", "ir.rule"))]
            )
        )

    def test_old_format_access_data_is_refused_at_the_door(self):
        csv_content = (
            b"id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,"
            b"perm_unlink\nacl,acl,base.model_res_partner,base.group_user,1,0,0,0\n"
        )
        with self.assertRaisesRegex(
            ValueError,
            r"a_module: security/ir.model.access.csv ships ir.model.access data.*"
            r"ship security/ir.access.csv.*ir_access_convert",
        ):
            convert_csv_import(
                self.env, "a_module", "security/ir.model.access.csv", csv_content
            )
        doc = etree.fromstring(
            '<odoo><record id="a_rule" model="ir.rule">'
            '<field name="name">rule</field></record></odoo>'
        )
        importer = xml_import(self.env, "a_module", {}, "init")
        importer.xml_filename = "security/rules.xml"
        with self.assertRaises(Exception) as caught:
            importer.parse(doc)
        self.assertRegex(
            str(caught.exception.__cause__ or caught.exception),
            r"a_module: security/rules.xml ships ir.rule data.*"
            r"ship security/ir.access.csv",
        )

    def test_create_omitted_group_warns(self):
        with self.assertLogs(
            "odoo.addons.base.models.ir_access", level="WARNING"
        ) as log_cm:
            row = self.env["ir.access"].create(
                {
                    "name": "row_no_group_omitted",
                    "model_id": self.env.ref("base.model_res_partner").id,
                    "kind": "permission",
                    "operation": "r",
                }
            )
        self.assertTrue(
            any("has no group" in msg for msg in log_cm.output),
            "Omitting group_id on a permission must warn.",
        )
        self.assertEqual(row.group_id, self.env.ref("base.group_everyone"))

    def test_cache_clearing_invalidates_both_access_caches(self):
        registry = self.env.registry
        caches = registry.ormcache_lrus

        def cached(bucket, method_name):
            return [
                key
                for key in caches[bucket].snapshot
                if getattr(key[1], "__name__", None) == method_name
            ]

        registry.clear_all_caches()
        self.env(user=self.user_demo)["res.partner"]._access_domain("read")
        self.env["ir.access"]._get_groups_with_access("res.partner", "read")
        self.env["res.partner"].with_user(self.user_demo).get_view(view_type="form")
        self.assertTrue(
            caches["templates"].snapshot,
            "get_view should populate the 'templates' bucket.",
        )
        self.assertTrue(
            cached("default", "_access_domain"),
            "_access_domain should populate the 'default' bucket.",
        )
        self.assertTrue(
            cached("stable", "_group_ids_with_access"),
            "_group_ids_with_access should populate the 'stable' bucket.",
        )

        self.env["ir.access"]._clear_access_caches()
        self.assertFalse(
            cached("default", "_access_domain"),
            "_access_domain (default bucket) must be invalidated.",
        )
        self.assertFalse(
            cached("stable", "_group_ids_with_access"),
            "_group_ids_with_access (stable bucket) must be invalidated.",
        )
        self.assertFalse(
            caches["templates"].snapshot,
            "views cache the groups a model is readable by: the 'templates' "
            "bucket must be invalidated.",
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
            make_access_row(self.env, model_partner.model, group, operation="r")

        Access = self.env["ir.access"].with_context(lang="fr_FR")
        names = Access._group_names_with_access("res.partner", "read")
        ours = [n for n in names if n in ("ZZZ_zulu", "ZZZ_mike")]
        self.assertEqual(
            ours,
            ["ZZZ_mike", "ZZZ_zulu"],
            "Groups must be ordered by localized (fr_FR) name.",
        )


class TestAccessWhileLoading(TransactionCaseWithUserDemo):
    MODEL = "ir.config_parameter"
    MODULE = "a_module_being_loaded"

    def setUp(self):
        super().setUp()
        make_access_row(
            self.env,
            self.MODEL,
            "base.group_user",
            operation="r",
            xmlid=f"{self.MODULE}.test_acl_from_a_loading_module",
        )
        self.model = self.env(user=self.user_demo)[self.MODEL]

    def _allowed(self, **context):
        return self.model.with_context(**context).has_access("read")

    def test_acl_from_an_unloaded_module_is_skipped_while_loading(self):
        with registry_loading(self.env.registry, False):
            self.assertTrue(self._allowed())
        with registry_loading(self.env.registry, True):
            self.assertFalse(self._allowed())

    def test_acl_of_the_module_being_loaded_applies_to_its_own_files(self):
        with registry_loading(self.env.registry, True):
            self.assertFalse(self._allowed(install_module="another_module"))
            self.assertTrue(
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
            self.assertFalse(self._allowed())
            with module_marked_loaded(self.env.registry, self.MODULE):
                self.assertTrue(
                    self._allowed(),
                    "An answer computed before a module was loaded must not be "
                    "served once it is",
                )


class TestAccessCacheInvalidation(TransactionCaseWithUserDemo):
    # res.partner.tag: its permissions carry no domain, whereas res.partner also
    # holds permissions a write to one row cannot revoke
    def _granting_rows(self, model_name, user, mode="write"):
        group_ids = set(user._get_group_ids())
        return (
            self.env["ir.access"]
            .sudo()
            .search(
                [
                    ("model_id", "=", self.env["ir.model"]._get(model_name).id),
                    ("kind", "=", "permission"),
                    (f"for_{mode}", "=", True),
                    ("active", "=", True),
                ]
            )
            .filtered(lambda row: row.group_id.id in group_ids)
        )

    def test_revoke_takes_effect_in_the_writing_worker(self):
        admin = self.env.ref("base.user_admin")
        Tag = self.env(user=admin.id)["res.partner.tag"]
        rows = self._granting_rows("res.partner.tag", admin)
        self.assertTrue(rows, "expected admin to hold a write row on res.partner.tag")
        self.env.flush_all()
        self.env.registry.clear_cache()
        self.assertTrue(Tag.has_access("write"))

        rows.with_user(admin).write({"for_write": False})

        self.assertFalse(
            Tag.has_access("write"),
            "revoking a model's row must take effect in the worker that revoked it",
        )

    def test_grant_takes_effect_in_the_writing_worker(self):
        admin = self.env.ref("base.user_admin")
        Tag = self.env(user=admin.id)["res.partner.tag"]
        rows = self._granting_rows("res.partner.tag", admin)
        rows.with_user(admin).write({"for_write": False})
        self.env.registry.clear_cache()
        self.assertFalse(Tag.has_access("write"))

        rows.with_user(admin).write({"for_write": True})

        self.assertTrue(Tag.has_access("write"))

    def test_unlink_takes_effect_in_the_writing_worker(self):
        admin = self.env.ref("base.user_admin")
        Tag = self.env(user=admin.id)["res.partner.tag"]
        rows = self._granting_rows("res.partner.tag", admin, mode="unlink")
        self.assertTrue(rows, "expected admin to hold an unlink row on res.partner.tag")
        self.env.flush_all()
        self.env.registry.clear_cache()
        self.assertTrue(Tag.has_access("unlink"))

        rows.with_user(admin).unlink()

        self.assertFalse(Tag.has_access("unlink"))


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
