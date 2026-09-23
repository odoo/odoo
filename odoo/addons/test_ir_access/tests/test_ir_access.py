import re
from contextlib import contextmanager

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger


class TestIrAccessCase(TransactionCase):
    MODEL = "test_ir_access.item"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group1 = cls.env["res.groups"].create({"name": "Group 1"})
        cls.group2 = cls.env["res.groups"].create({"name": "Group 2"})
        cls.group3 = cls.env["res.groups"].create({"name": "Group 3"})
        groups = cls.env.ref("base.group_user") + cls.group1 + cls.group2
        cls.user = cls.env["res.users"].create(
            {
                "login": "bob",
                "name": "Bob Bobman",
                "group_ids": [Command.set(groups.ids)],
            }
        )
        cls.env["ir.access"].search(
            [
                ("model_id.model", "like", "test_ir_access.%"),
                ("model_id.model", "!=", "test_ir_access.node"),
            ]
        ).unlink()
        cls.records = (
            cls.env[cls.MODEL]
            .create(
                [
                    {"name": name}
                    for name in ("Mario", "Luigi", "Peach", "Toad", "Yoshi", "Bowser")
                ]
            )
            .with_user(cls.user)
        )
        cls.mario, cls.luigi, cls.peach, cls.toad, cls.yoshi, cls.bowser = cls.records
        cls.model = cls.records.browse()

    def make_access(
        self,
        name="",
        records=None,
        group=None,
        operation="r",
        kind="permission",
        model=None,
        **kwargs,
    ):
        return self.env["ir.access"].create(
            {
                "name": name or "access",
                "model_id": self.env["ir.model"]._get_id(model or self.MODEL),
                "group_id": (group or self.env.ref("base.group_everyone")).id,
                "kind": kind,
                "operation": operation,
                "domain": str([("id", "in", records.ids)]) if records else False,
                **kwargs,
            }
        )

    def make_guard(self, name="", records=None, group=None, operation="r", **kwargs):
        return self.make_access(name, records, group, operation, kind="guard", **kwargs)

    def assertAccess(self, allowed, operation="read"):
        self.assertTrue(self.model.has_access(operation))
        self.model.check_access(operation)
        for record in self.records:
            if record in allowed:
                self.assertTrue(record.has_access(operation))
                record.check_access(operation)
            else:
                self.assertFalse(record.has_access(operation))
                with self.assertAccessError():
                    record.check_access(operation)
        allowed.check_access(operation)
        if self.records - allowed:
            with self.assertAccessError():
                self.records.check_access(operation)
        self.assertEqual(self.records._filtered_access(operation), allowed)
        if operation == "read":
            self.assertEqual(
                self.model.search([("id", "in", self.records.ids)], order="id"),
                allowed.sorted("id"),
            )

    @contextmanager
    def assertAccessError(self, message=None):
        with mute_logger("odoo.addons.base.models.ir_access"):
            if message:
                with self.assertRaisesRegex(
                    AccessError, re.compile(message, re.DOTALL)
                ):
                    yield
            else:
                with self.assertRaises(AccessError):
                    yield


class TestIrAccess(TestIrAccessCase):
    def test_for_fields(self):
        access = self.make_access(records=self.records, operation="ru")
        self.assertTrue(access.for_read)
        self.assertTrue(access.for_write)
        self.assertFalse(access.for_create)
        self.assertFalse(access.for_unlink)

        access.operation = "cr"
        self.assertTrue(access.for_read)
        self.assertFalse(access.for_write)
        self.assertTrue(access.for_create)
        self.assertFalse(access.for_unlink)

        access.write({"for_write": True, "for_create": False})
        self.assertEqual(access.operation, "ru")

        access = self.env["ir.access"].create(
            {
                "name": "no operation",
                "model_id": self.env["ir.model"]._get_id(self.MODEL),
                "group_id": self.group1.id,
                "kind": "permission",
                "for_create": True,
            }
        )
        self.assertEqual(access.operation, "c")

    def test_a_row_without_group_is_everyone_s(self):
        with mute_logger("odoo.addons.base.models.ir_access"):
            access = self.env["ir.access"].create(
                {
                    "name": "no group",
                    "model_id": self.env["ir.model"]._get_id(self.MODEL),
                    "kind": "permission",
                    "operation": "r",
                }
            )
        self.assertEqual(access.group_id, self.env.ref("base.group_everyone"))
        self.assertAccess(self.records)

    def test_everyone_is_implied_by_every_user_type(self):
        everyone = self.env.ref("base.group_everyone")
        for xmlid in ("base.group_user", "base.group_portal", "base.group_public"):
            self.assertIn(everyone, self.env.ref(xmlid).all_implied_ids)
        self.assertIn(everyone, self.user.all_group_ids)
        self.assertIn(everyone, self.env.ref("base.public_user").all_group_ids)

    def test_sudo(self):
        records = self.records.sudo()
        for operation in ("read", "write", "create", "unlink"):
            self.assertTrue(records.has_access(operation))
            self.assertEqual(records._filtered_access(operation), records)
            records.check_access(operation)

    def test_no_access(self):
        for operation in ("read", "write", "create", "unlink"):
            self.assertFalse(self.records.has_access(operation))
            self.assertFalse(self.records._filtered_access(operation))
            with self.assertAccessError():
                self.records.check_access(operation)

    def test_a_guard_alone_grants_nothing(self):
        self.make_guard(records=self.records)

        self.assertFalse(self.model.has_access("read"))
        self.assertFalse(self.model.has_access("write"))
        self.assertFalse(self.records._filtered_access("read"))
        with self.assertAccessError():
            self.model.check_access("read")
        with self.assertAccessError():
            self.records.check_access("read")

    def test_one_permission(self):
        humans = self.mario + self.luigi + self.peach
        self.make_access(group=self.group1, operation="r")
        self.make_access(records=humans, group=self.group1, operation="u")

        self.assertAccess(self.records, "read")
        self.assertAccess(humans, "write")

    def test_two_permissions_in_group(self):
        self.make_access(records=self.mario + self.luigi, group=self.group1)
        self.make_access(records=self.mario + self.peach, group=self.group1)

        self.assertAccess(self.mario + self.luigi + self.peach)

    def test_two_permissions_in_distinct_groups(self):
        self.make_access(records=self.mario + self.luigi, group=self.group1)
        self.make_access(records=self.mario + self.peach, group=self.group2)
        self.make_access(records=self.mario + self.yoshi, group=self.group3)

        self.assertAccess(self.mario + self.luigi + self.peach)

    def test_one_permission_one_guard(self):
        self.make_access(
            records=self.mario + self.peach + self.bowser, group=self.group1
        )
        self.make_guard(records=self.records - self.bowser)

        self.assertAccess(self.mario + self.peach)

    def test_two_permissions_one_guard(self):
        self.make_access(
            records=self.mario + self.luigi + self.bowser, group=self.group1
        )
        self.make_access(
            records=self.mario + self.peach + self.bowser, group=self.group2
        )
        self.make_guard(records=self.records - self.bowser)

        self.assertAccess(self.mario + self.luigi + self.peach)

    def test_two_permissions_two_guards(self):
        self.make_access(
            records=self.mario + self.luigi + self.bowser, group=self.group1
        )
        self.make_access(
            records=self.mario + self.peach + self.bowser, group=self.group2
        )
        self.make_guard(records=self.records - self.bowser)
        self.make_guard(records=self.records - self.peach)

        self.assertAccess(self.mario + self.luigi)

    def test_special_user_manager(self):
        self.make_access(
            records=self.mario + self.luigi + self.bowser, group=self.group1
        )
        self.make_access(group=self.group2)
        self.make_guard(records=self.records - self.bowser)

        self.assertAccess(self.records - self.bowser)

    def test_guards_bind_their_operations_only(self):
        self.make_access(group=self.group1, operation="r")
        self.make_access(group=self.group2, operation="crud")
        self.make_guard(records=self.records - self.bowser, operation="cud")

        self.assertAccess(self.records, operation="read")
        self.assertAccess(self.records - self.bowser, operation="write")
        self.assertAccess(self.records - self.bowser, operation="create")
        self.assertAccess(self.records - self.bowser, operation="unlink")

    def test_a_member_guard_binds_only_the_members_of_its_group(self):
        self.make_access(group=self.group1)
        self.make_guard(
            records=self.mario + self.luigi, group=self.group3, guard_scope="members"
        )

        self.assertAccess(self.records)

        self.user.group_ids = [Command.link(self.group3.id)]
        self.assertAccess(self.mario + self.luigi)

    def test_adding_a_group_never_takes_records_away(self):
        self.make_access(records=self.mario + self.luigi, group=self.group1)
        self.make_access(records=self.peach, group=self.group3)
        self.make_guard(records=self.records - self.bowser)
        before = self.records._filtered_access("read")
        self.assertEqual(before, self.mario + self.luigi)

        self.user.group_ids = [Command.link(self.group3.id)]
        after = self.records._filtered_access("read")
        self.assertLessEqual(before, after)
        self.assertEqual(after, self.mario + self.luigi + self.peach)

    def test_a_domain_that_tests_the_user_s_groups_is_refused(self):
        for domain in (
            "[('id', '!=', user.has_group('base.group_system') and 0 or 1)]",
            "[('val', 'not in', user.group_ids.ids)]",
            "['!', ('id', 'in', user.all_group_ids.ids)]",
            "[('id', '=', 0)] if user.has_group('base.group_system') else []",
        ):
            with (
                self.subTest(domain=domain),
                self.assertRaisesRegex(ValidationError, "tests the user's groups"),
            ):
                self.make_access(group=self.group1, domain=domain)

    def test_a_domain_that_only_widens_with_the_user_s_groups_is_accepted(self):
        # membership in the ids of the user's groups, and a domain a group's
        # members are exempt from, give more records to more groups
        for domain in (
            "[('id', 'in', user.all_group_ids.ids)]",
            "[('val', 'in', user.group_ids.ids)]",
            "[] if user.has_group('base.group_system') else [('id', '=', 0)]",
            (
                "(['|', ('id', '=', 1)] if user.has_group('base.group_system') else [])"
                " + [('id', '=', 2)]"
            ),
        ):
            with self.subTest(domain=domain):
                self.make_access(group=self.group1, domain=domain)

    def test_an_invalid_domain_is_refused(self):
        with self.assertRaisesRegex(ValidationError, "Invalid domain"):
            self.make_access(group=self.group1, domain="[('no_such_field', '=', 1)]")
        with self.assertRaisesRegex(ValidationError, "Invalid domain"):
            self.make_access(group=self.group1, domain="[('val', 'access', 'read')]")
        with self.assertRaisesRegex(ValidationError, "Invalid domain"):
            self.make_access(
                group=self.group1, domain="[('category_id', 'access', 'fly')]"
            )

    def test_error_message_no_access(self):
        self.make_access(group=self.group3, operation="cd")

        with self.assertAccessError(
            r"You are not allowed to access.*No group currently allows this operation"
        ):
            self.records.check_access("read")
        with self.assertAccessError(
            r"You are not allowed to create.*"
            r"This operation is allowed for the following groups:\s*- Group 3"
        ):
            self.records.check_access("create")

    def test_error_message_names_the_failing_rows(self):
        humans = self.records[:3]
        self.make_access("See good guys", records=self.records[:5], group=self.group1)
        self.make_guard("Restrict to humans", records=humans)

        self.assertEqual(self.records._filtered_access("read"), humans)
        with self.assertAccessError(
            rf"Sorry, Bob Bobman \(id={self.user.id}\) doesn't have 'read' access to:\s*"
            r"- Item read through ir.access \(test_ir_access\.item\)\s*"
            r"If you really"
        ):
            self.records.check_access("read")

        with (
            self.debug_mode(),
            self.assertAccessError(
                r"Blame the following accesses:\s*- See good guys\s*- Restrict to humans"
            ),
        ):
            self.records.check_access("read")

    def test_customize_edits_a_copy_of_a_module_row(self):
        standard = self.env.ref("test_ir_access.access_node_system")
        self.assertTrue(standard.is_standard)
        self.assertIn(
            standard, self.env["ir.access"].search([("is_standard", "=", True)])
        )
        action = standard.customize()
        copy = self.env["ir.access"].browse(action["res_id"])
        self.assertNotEqual(copy, standard)
        self.assertFalse(standard.active)
        self.assertFalse(copy.is_standard)
        self.assertEqual(copy.customize()["res_id"], copy.id)

    def test_every_model_reads_its_access_from_ir_access(self):
        partner = self.env["res.partner"].create({"name": "Somebody"})
        self.assertTrue(partner.with_user(self.user).has_access("read"))
        self.make_guard(model="res.partner", domain="[(0, '=', 1)]")
        self.assertFalse(partner.with_user(self.user).has_access("read"))


class TestAccessOperator(TestIrAccessCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Category = cls.env["test_ir_access.category"]
        cls.heroes, cls.villains = Category.create(
            [{"name": "Heroes"}, {"name": "Villains"}]
        )
        (cls.records - cls.bowser).sudo().category_id = cls.heroes
        cls.bowser.sudo().category_id = cls.villains

    def delegate_to_category(self, operation="read"):
        return self.make_access(
            "through the category",
            group=self.group1,
            domain=str([("category_id", "access", operation)]),
        )

    def test_a_record_is_reachable_when_its_category_is(self):
        self.delegate_to_category()
        self.make_access(
            records=self.heroes, group=self.group1, model="test_ir_access.category"
        )
        self.assertAccess(self.records - self.bowser)

    def test_no_access_to_the_category_is_no_access_to_the_model(self):
        self.delegate_to_category()
        self.assertFalse(self.model.has_access("read"))
        self.assertFalse(self.records._filtered_access("read"))

    def test_the_operator_reads_the_category_s_own_operation(self):
        self.delegate_to_category("write")
        self.make_access(group=self.group1, model="test_ir_access.category")
        self.make_access(
            records=self.villains,
            group=self.group1,
            operation="u",
            model="test_ir_access.category",
        )
        self.assertAccess(self.bowser)

    def test_a_read_verdict_follows_a_write_the_category_rule_reads(self):
        self.delegate_to_category()
        self.make_access(
            group=self.group1,
            model="test_ir_access.category",
            domain="[('name', '!=', 'Hidden')]",
        )
        self.assertTrue(self.mario.has_access("read"))
        self.heroes.sudo().name = "Hidden"
        self.assertFalse(self.mario.has_access("read"))
        self.assertTrue(self.bowser.has_access("read"))

    def test_a_cycle_through_the_operator_is_refused(self):
        self.delegate_to_category()
        with self.assertRaisesRegex(
            ValidationError,
            r"form a cycle: .*test_ir_access\.category\.read.*test_ir_access\.item\.read",
        ):
            self.make_access(
                group=self.group2,
                model="test_ir_access.category",
                domain=str([("featured_item_id", "access", "read")]),
            )

    def test_a_self_referencing_row_is_refused(self):
        with self.assertRaisesRegex(ValidationError, "form a cycle"):
            self.make_access(
                group=self.group1,
                model="test_ir_access.node",
                domain=str(
                    ["|", ("parent_id", "=", False), ("parent_id", "access", "read")]
                ),
            )

    def test_a_cycle_written_behind_the_constraint_fails_clearly(self):
        self.delegate_to_category()
        back = self.make_access(group=self.group2, model="test_ir_access.category")
        self.env.cr.execute(
            "UPDATE ir_access SET domain = %s WHERE id = %s",
            [str([("featured_item_id", "access", "read")]), back.id],
        )
        self.env.registry.clear_cache("stable")
        self.env.invalidate_all()
        with self.assertRaisesRegex(ValueError, "form a cycle"):
            self.model.search([])


class TestDelegatedAccess(TestIrAccessCase):
    def test_a_stored_delegate_binds_its_parent_s_access(self):
        self._check_delegation("test_ir_access.delegated", "item_id")

    def test_a_computed_delegate_binds_its_parent_s_access(self):
        self._check_delegation("test_ir_access.delegated_computed", "held_id")

    def _check_delegation(self, model_name, link):
        children = self.env[model_name].create(
            [{link: record.id} for record in self.mario + self.bowser]
        )
        allowed, forbidden = children
        self.make_access(group=self.group1, model=model_name)
        user_children = children.with_user(self.user)
        self.assertFalse(user_children.browse().has_access("read"))

        self.make_access(records=self.mario, group=self.group1)
        self.assertEqual(
            user_children.search([("id", "in", children.ids)]),
            allowed.with_user(self.user),
        )
        self.assertEqual(user_children._filtered_access("read"), allowed)
        with self.assertAccessError():
            forbidden.with_user(self.user).check_access("read")


class TestRetiredAccessTables(TestIrAccessCase):
    """ir.model.access and ir.rule stay only for the callers that still name
    them: every access is an ir.access row, and base's 1.97 migration converted
    what the two tables held."""

    def test_an_access_line_cannot_be_created(self):
        with self.assertRaisesRegex(UserError, "ir.access"):
            self.env["ir.model.access"].create(
                {
                    "name": "acl",
                    "model_id": self.env["ir.model"]._get_id(self.MODEL),
                    "group_id": self.group1.id,
                    "perm_read": True,
                }
            )

    def test_a_record_rule_cannot_be_created(self):
        with self.assertRaisesRegex(UserError, "ir.access"):
            self.env["ir.rule"].create(
                {
                    "name": "rule",
                    "model_id": self.env["ir.model"]._get_id(self.MODEL),
                    "domain_force": "[]",
                }
            )

    def test_rows_do_not_load_while_an_id_still_names_an_old_record(self):
        self.env["ir.model.data"].create(
            {
                "module": "test_ir_access",
                "name": "an_unconverted_rule",
                "model": "ir.rule",
                "res_id": 1,
            }
        )
        data = {
            "xml_id": "test_ir_access.a_row_of_a_module_file",
            "values": {
                "name": "row",
                "model_id": self.env["ir.model"]._get_id(self.MODEL),
                "group_id": self.group1.id,
                "kind": "permission",
                "operation": "r",
            },
        }
        with self.assertRaisesRegex(UserError, r"-u base"):
            self.env["ir.access"]._load_records([data])

    def test_the_failing_guard_is_blamed_by_name(self):
        self.make_access(group=self.group1, operation="ru")
        self.make_guard("only mario", records=self.mario, operation="u")
        with (
            self.debug_mode(),
            self.assertAccessError(r"Blame the following accesses:\s*- only mario"),
        ):
            self.luigi.check_access("write")
