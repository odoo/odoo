import contextlib
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.orm.models.mixins.read import PrefetchBatchDenied
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestRules(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        ObjCateg = cls.env["test_access_right.obj_categ"]
        SomeObj = cls.env["test_access_right.some_obj"]
        cls.categ = ObjCateg.create({"name": "Food"})
        cls.allowed = SomeObj.create({"val": 1, "categ_id": cls.categ.id})
        cls.forbidden = SomeObj.create({"val": -1, "categ_id": cls.categ.id})
        cls.env["ir.rule"].create(
            {
                "name": "Forbid negatives",
                "model_id": cls.env.ref(
                    "test_access_rights.model_test_access_right_some_obj"
                ).id,
                "domain_force": "[('val', '>', 0)]",
            }
        )
        cls.env["ir.rule"].create(
            {
                "name": "See all categories",
                "model_id": cls.env.ref(
                    "test_access_rights.model_test_access_right_some_obj"
                ).id,
                "domain_force": "[('categ_id', 'in', user.env['test_access_right.obj_categ'].search([]).ids)]",
            }
        )

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_basic_access(self):
        env = self.env(user=self.env.ref("base.public_user"))
        allowed = self.allowed.with_env(env)
        forbidden = self.forbidden.with_env(env)

        self.assertEqual(allowed.val, 1)

        allowed.invalidate_model(["val"])
        with self.assertRaises(AccessError):
            self.assertEqual(forbidden.val, -1)

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_group_rule(self):
        env = self.env(user=self.env.ref("base.public_user"))
        allowed = self.allowed.with_env(env)
        forbidden = self.forbidden.with_env(env)

        self.env["ir.rule"].create(
            {
                "name": "Forbid public group",
                "model_id": self.env.ref(
                    "test_access_rights.model_test_access_right_some_obj"
                ).id,
                "groups": [Command.set([self.env.ref("base.group_public").id])],
                "domain_force": "[(0, '=', 1)]",
            }
        )

        (allowed + forbidden).invalidate_model(["val"])
        with self.assertRaises(AccessError):
            self.assertEqual(forbidden.val, -1)
        with self.assertRaises(AccessError):
            self.assertEqual(allowed.val, 1)

    def test_many2many(self):
        ids = [self.allowed.id, self.forbidden.id]

        container_admin = self.env["test_access_right.container"].create(
            {"some_ids": [Command.set(ids)]}
        )
        self.assertItemsEqual(container_admin.some_ids.ids, ids)

        container_user = container_admin.with_user(self.env.ref("base.public_user"))
        container_user.invalidate_model(["some_ids"])
        self.assertItemsEqual(container_user.some_ids.ids, [self.allowed.id])

        with self.assertRaises(AccessError):
            container_user.write({"some_ids": [Command.set(ids)]})

        container_admin.write({"some_ids": [Command.set(ids)]})
        container_user.invalidate_model(["some_ids"])
        self.assertItemsEqual(container_user.some_ids.ids, [self.allowed.id])
        container_admin.invalidate_model(["some_ids"])
        self.assertItemsEqual(container_admin.some_ids.ids, ids)

        container_user.write({"some_ids": [Command.clear()]})
        container_user.invalidate_model(["some_ids"])
        self.assertItemsEqual(container_user.some_ids.ids, [])
        container_admin.invalidate_model(["some_ids"])
        self.assertItemsEqual(container_admin.some_ids.ids, [self.forbidden.id])

    def _container_holding_both(self):
        container = self.env["test_access_right.container"].create(
            {"some_ids": [Command.set([self.allowed.id, self.forbidden.id])]}
        )
        return container, container.with_user(self.env.ref("base.public_user"))

    def test_a_user_clear_keeps_the_links_the_user_cannot_read_whatever_is_cached(self):
        container_admin, container_user = self._container_holding_both()
        container_admin.invalidate_model(["some_ids"])
        self.assertEqual(len(container_admin.some_ids), 2)
        container_user.write({"some_ids": [Command.clear()]})
        container_admin.invalidate_model(["some_ids"])
        self.assertEqual(container_admin.some_ids, self.forbidden)

    def test_a_user_set_replaces_only_the_links_the_user_can_read(self):
        other = self.env["test_access_right.some_obj"].create(
            {"val": 2, "categ_id": self.categ.id}
        )
        container_admin, container_user = self._container_holding_both()
        container_user.write({"some_ids": [Command.set(other.ids)]})
        container_admin.invalidate_model(["some_ids"])
        self.assertEqual(container_admin.some_ids, other | self.forbidden)

    def test_a_superuser_clear_removes_every_link(self):
        container_admin, _container_user = self._container_holding_both()
        container_admin.sudo().write({"some_ids": [Command.clear()]})
        container_admin.invalidate_model(["some_ids"])
        self.assertFalse(container_admin.some_ids)

    def test_access_rule_performance(self):
        env = self.env(user=self.env.ref("base.public_user"))
        Model = env["test_access_right.some_obj"]
        Model.check_access("read")
        with self.assertQueryCount(0):
            Model._filtered_access("read")

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_check_access_newid_bypasses_ir_rule(self):
        env = self.env(user=self.env.ref("base.public_user"))
        SomeObj = env["test_access_right.some_obj"]

        new_record = SomeObj.new({"val": -42})
        self.assertEqual(new_record.val, -42)
        new_record.check_access("read")
        self.assertTrue(new_record.has_access("read"))

        allowed_user = self.allowed.with_env(env)
        mixed_ok = new_record | allowed_user
        mixed_ok.check_access("read")
        self.assertTrue(mixed_ok.has_access("read"))

        forbidden_user = self.forbidden.with_env(env)
        mixed_bad = new_record | forbidden_user
        result = mixed_bad._check_access("read")
        self.assertIsNotNone(result, "real-forbidden record should still trip the rule")
        forbidden_records = result[0]
        self.assertIn(forbidden_user, forbidden_records)
        self.assertNotIn(
            new_record,
            forbidden_records,
            "NewId must not be reported as forbidden by ir.rule",
        )

        filtered = mixed_bad._filtered_access("read")
        self.assertIn(new_record, filtered)
        self.assertNotIn(forbidden_user, filtered)

    def test_no_context_in_ir_rules(self):
        ObjCateg = self.env["test_access_right.obj_categ"]
        SomeObj = self.env["test_access_right.some_obj"]

        self.assertTrue(ObjCateg.search([]))
        self.assertFalse(ObjCateg.with_context(only_media=True).search([]))

        self.env.registry.clear_cache()
        records = SomeObj.search([("id", "=", self.allowed.id)])
        self.assertTrue(records)

        self.env.registry.clear_cache()
        records = SomeObj.with_context(only_media=True).search(
            [("id", "=", self.allowed.id)]
        )
        self.assertTrue(records)

    def test_check_access_rule_with_inherits(self):
        ChildModel = self.env["test_access_right.inherits"]
        allowed_child, __ = children = ChildModel.create(
            [
                {"some_id": self.allowed.id},
                {"some_id": self.forbidden.id},
            ]
        )

        user = self.env.ref("base.public_user")
        search_result = children.with_user(user).search(
            [("id", "in", children.ids)], order="id"
        )
        filter_result = children.with_user(user)._filtered_access("read")

        self.assertEqual(search_result, allowed_child)
        self.assertEqual(filter_result, allowed_child)

    def test_flush_with_inherits(self):
        ChildModel = self.env["test_access_right.inherits"]
        child = ChildModel.create([{"some_id": self.allowed.id}])
        self.env.flush_all()

        self.env["ir.rule"].create(
            {
                "name": "Forbid 0 value",
                "model_id": self.env["ir.model"]._get("test_access_right.some_obj").id,
                "domain_force": str([("val", "!=", 0)]),
            }
        )

        user = self.env.ref("base.public_user")

        search_result = ChildModel.with_user(user).search(
            [("id", "=", child.id)], order="id"
        )
        self.assertEqual(search_result, child)

        self.allowed.val = 0
        search_result = ChildModel.with_user(user).search(
            [("id", "=", child.id)], order="id"
        )
        self.assertEqual(search_result, ChildModel)

    def test_domain_constrains(self):

        rule = self.env["ir.rule"].create(
            {
                "name": "Test record rule",
                "model_id": self.env.ref(
                    "test_access_rights.model_test_access_right_some_obj"
                ).id,
                "domain_force": [],
            }
        )
        invalid_domains = [
            "A really bad domain!",
            [(1, "!=", 1)],
            [("non_existing_field", "=", "value")],
        ]

        for domain in invalid_domains:
            with self.assertRaisesRegex(ValidationError, "Invalid domain"):
                rule.domain_force = domain

        valid_domains = [
            False,
            [(1, "=", 1)],
            [("val", "=", 12)],
        ]
        for domain in valid_domains:
            rule.domain_force = domain

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_ir_rule_cache_after_error(self):
        NB_RECORD = 14
        SomeObj = self.env["test_access_right.some_obj"]
        forbiddens = SomeObj.create(
            [{"val": -1, "categ_id": self.categ.id}] * NB_RECORD
        )
        forbiddens.invalidate_model()

        env = self.env(user=self.env.ref("base.public_user"))
        forbiddens = forbiddens.with_env(env)
        forbiddens.browse().check_access("read")

        with contextlib.suppress(AccessError):
            forbiddens.check_access("read")
            self.fail("Previous line should raise AccessError")

        with contextlib.suppress(AccessError):
            forbiddens[0].val
            self.fail("Previous line should raise AccessError")

        with contextlib.suppress(AccessError):
            forbiddens[NB_RECORD - 1].val
            self.fail("Previous line should raise AccessError")

    def _count_rule_reports(self):
        IrRule = type(self.env["ir.rule"])
        return patch.object(
            IrRule, "_get_failing", autospec=True, side_effect=IrRule._get_failing
        )

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_a_prefetch_batch_holding_an_unreadable_record_builds_no_rule_report(self):
        env = self.env(user=self.env.ref("base.public_user"))
        records = (
            self.env["test_access_right.some_obj"]
            .with_env(env)
            .browse([self.forbidden.id, self.allowed.id])
        )
        records.invalidate_model()
        with self._count_rule_reports() as get_failing:
            self.assertEqual(records[1].val, 1)
            self.assertEqual(records[1].categ_id, self.categ.with_env(env))
        get_failing.assert_not_called()

        with (
            self._count_rule_reports() as get_failing,
            self.assertRaises(AccessError) as caught,
        ):
            records[0].val
        self.assertNotIsInstance(caught.exception, PrefetchBatchDenied)
        self.assertEqual(get_failing.call_count, 1)

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_a_prefetch_batch_of_x2many_values_with_an_unreadable_record(self):
        Container = self.env["test_access_right.container"]
        hidden, shown = Container.create(
            [
                {"some_ids": [Command.set(self.allowed.ids)]},
                {"some_ids": [Command.set(self.allowed.ids)]},
            ]
        )
        self.env["ir.rule"].create(
            {
                "name": "Hide one container",
                "model_id": self.env.ref(
                    "test_access_rights.model_test_access_right_container"
                ).id,
                "domain_force": f"[('id', '!=', {hidden.id})]",
            }
        )
        env = self.env(user=self.env.ref("base.public_user"))
        containers = Container.with_env(env).browse([hidden.id, shown.id])
        containers.invalidate_model()
        with self._count_rule_reports() as get_failing:
            self.assertEqual(containers[1].some_ids.ids, self.allowed.ids)
        get_failing.assert_not_called()
        with self.assertRaises(AccessError) as caught:
            containers[0].some_ids
        self.assertNotIsInstance(caught.exception, PrefetchBatchDenied)


@tagged("post_install", "-at_install")
class TestWebSearchReadOverride(TransactionCase):
    def test_web_search_read_goes_through_search_fetch(self):
        ObjCateg = self.env["test_access_right.obj_categ"]
        ObjCateg.create([{"name": "Media"}, {"name": "Other"}])

        result = ObjCateg.with_context(only_media=True).web_search_read(
            [], {"name": {}}, limit=80
        )
        self.assertEqual([r["name"] for r in result["records"]], ["Media"])
        self.assertEqual(result["length"], 1)

        result = ObjCateg.web_search_read([], {"name": {}}, limit=80)
        self.assertEqual(
            sorted(r["name"] for r in result["records"]), ["Media", "Other"]
        )
