import time
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.service import api_scope
from odoo.service.model import call_kw
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


class ScopeCase(TransactionCase):
    """A scope over `res.partner` hiding `vat` and `email`, enforced through
    `call_kw` as every API door enforces it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="scope_probe", groups="base.group_user")
        partner_model = cls.env["ir.model"]._get("res.partner")
        fields_ = cls.env["ir.model.fields"].search(
            [("model_id", "=", partner_model.id), ("name", "in", ("vat", "email"))]
        )
        cls.scope = cls.env["res.users.apikeys.scope"].create(
            {
                "name": "Probe",
                "key": "probe",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "model_id": partner_model.id,
                            "allow_read": True,
                            "allow_create": True,
                            "allow_write": True,
                            "denied_field_ids": [(6, 0, fields_.ids)],
                        },
                    )
                ],
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Oracle Probe", "vat": "LEAKED-ORACLE-1", "email": "p@x.mx"}
        )
        cls.child = cls.env["res.partner"].create(
            {"name": "Oracle Child", "parent_id": cls.partner.id}
        )

    def _call(self, method, *args, model="res.partner", **kwargs):
        records = (
            self.env[model]
            .with_user(self.user)
            .with_context(api_scope_id=self.scope.id)
        )
        return call_kw(records, method, list(args), kwargs)


@tagged("post_install", "-at_install")
class TestScopeReach(ScopeCase):
    def test_a_model_the_scope_does_not_name_is_refused(self):
        with self.assertRaisesRegex(AccessError, "does not reach 'res.users'"):
            self._call("search_read", [], ["login"], model="res.users")

    def test_an_operation_the_scope_withholds_is_refused(self):
        with self.assertRaisesRegex(AccessError, "does not allow unlink"):
            self._call("unlink", [self.child.id])
        with self.assertRaisesRegex(AccessError, "does not allow call"):
            self._call("onchange", [self.child.id], {}, [], {})

    def test_a_scope_with_no_line_reaches_everything(self):
        everything = self.env["res.users.apikeys.scope"].create(
            {"name": "All", "key": "probe_all"}
        )
        records = (
            self.env["res.users"]
            .with_user(self.user)
            .with_context(api_scope_id=everything.id)
        )
        rows = call_kw(
            records, "search_read", [[("id", "=", self.user.id)]], {"fields": ["login"]}
        )
        self.assertEqual(rows[0]["login"], "scope_probe")

    def test_a_scope_closed_when_empty_reaches_nothing_until_a_line_names_a_model(
        self,
    ):
        closed = self.env["res.users.apikeys.scope"].create(
            {"name": "Closed", "key": "probe_closed", "closed_when_empty": True}
        )
        records = (
            self.env["res.users"]
            .with_user(self.user)
            .with_context(api_scope_id=closed.id)
        )
        self.assertEqual(closed._rules().models, {})
        with self.assertRaisesRegex(AccessError, "does not reach 'res.users'"):
            call_kw(records, "search_read", [[]], {"fields": ["login"]})

        closed.line_ids = [
            (0, 0, {"model_id": self.env["ir.model"]._get_id("res.users")})
        ]
        rows = call_kw(
            records, "search_read", [[("id", "=", self.user.id)]], {"fields": ["login"]}
        )
        self.assertEqual(rows[0]["login"], "scope_probe")

    def test_no_scope_leaves_call_kw_untouched(self):
        rows = call_kw(
            self.env["res.partner"].with_user(self.user),
            "read",
            [[self.partner.id]],
            {"fields": ["vat"]},
        )
        self.assertEqual(rows[0]["vat"], "LEAKED-ORACLE-1")


@tagged("post_install", "-at_install")
class TestHiddenColumns(ScopeCase):
    def test_a_named_hidden_field_is_refused(self):
        with self.assertRaisesRegex(
            UserError, "vat \\(on res.partner\\) is not available"
        ):
            self._call("read", [self.partner.id], fields=["name", "vat"])

    def test_read_without_a_field_list_strips_hidden_fields(self):
        rows = self._call("read", [self.partner.id])
        self.assertNotIn("vat", rows[0])
        self.assertNotIn("email", rows[0])
        self.assertEqual(rows[0]["name"], "Oracle Probe")

    def test_a_domain_a_sort_and_a_grouping_on_a_hidden_field_are_refused(self):
        with self.assertRaisesRegex(UserError, "not available"):
            self._call("search_read", [("vat", "=", "LEAKED-ORACLE-1")])
        with self.assertRaisesRegex(UserError, "not available"):
            self._call("search", [], order="vat")
        with self.assertRaisesRegex(UserError, "not available"):
            self._call("read_group", [], ["id:count"], ["email"])

    def test_writing_a_hidden_field_is_refused(self):
        with self.assertRaisesRegex(UserError, "not available"):
            self._call("write", [self.child.id], {"vat": "X"})
        with self.assertRaisesRegex(UserError, "not available"):
            self._call("create", {"name": "N", "email": "n@x.mx"})

    def test_an_x2many_create_command_cannot_write_a_hidden_column(self):
        with self.assertRaisesRegex(UserError, "not available"):
            self._call(
                "write",
                [self.partner.id],
                {"child_ids": [[0, 0, {"name": "C", "vat": "X"}]]},
            )

    def test_a_dotted_domain_cannot_read_a_hidden_column(self):
        with self.assertRaisesRegex(UserError, "not available"):
            self._call("search_count", [("parent_id.vat", "=", "LEAKED-ORACLE-1")])

    def test_an_any_domain_is_walked_to_the_bottom(self):
        with self.assertRaisesRegex(UserError, "not available"):
            self._call("search_count", [("child_ids", "any", [("email", "=", "x")])])

    def test_a_path_past_the_depth_cap_is_refused_not_truncated(self):
        self.scope.max_depth = 2
        with self.assertRaisesRegex(UserError, "may not cross more than 2"):
            self._call(
                "search_count", [("parent_id.parent_id.parent_id.name", "=", "x")]
            )

    def test_fields_get_does_not_describe_a_hidden_column(self):
        described = self._call("fields_get")
        self.assertIn("name", described)
        self.assertNotIn("vat", described)

    def test_a_visible_field_still_works(self):
        rows = self._call("search_read", [("id", "=", self.partner.id)], ["name"])
        self.assertEqual(rows, [{"id": self.partner.id, "name": "Oracle Probe"}])


@tagged("post_install", "-at_install")
class TestHiddenColumnOracles(ScopeCase):
    """`res.partner` searches `vat` and `email` by name, so a hidden column
    was a value oracle through `name_search`, a `display_name` condition and
    a string operator on any many2one pointing at the model."""

    def test_name_search_no_longer_matches_the_hidden_column(self):
        self.assertEqual(self._call("name_search", "LEAKED-ORACLE"), [])

    def test_name_search_still_matches_the_visible_columns(self):
        found = self._call("name_search", "Oracle Probe")
        self.assertIn(self.partner.id, [row[0] for row in found])

    def test_a_display_name_condition_does_not_reach_the_hidden_column(self):
        self.assertEqual(
            self._call("search_count", [("display_name", "ilike", "LEAKED-ORACLE")]), 0
        )

    def test_a_many2one_string_operator_does_not_reach_the_hidden_column(self):
        self.assertEqual(
            self._call("search_count", [("parent_id", "ilike", "LEAKED-ORACLE")]), 0
        )
        self.assertEqual(
            self._call("search_count", [("parent_id", "ilike", "Oracle Probe")]), 1
        )

    def test_the_client_context_cannot_switch_the_enforcement_off(self):
        # `show_vat` embeds the column in the label, and a context of the
        # caller's replaces the environment's: only the allowlisted keys pass.
        rows = self._call(
            "read",
            [self.partner.id],
            fields=["display_name"],
            context={"api_scope_id": False, "show_vat": True},
        )
        self.assertEqual(rows[0]["display_name"], "Oracle Probe")
        self.assertEqual(
            self._call(
                "search_count",
                [("display_name", "ilike", "LEAKED-ORACLE")],
                context={"show_vat": True},
            ),
            0,
        )

    def test_the_orm_is_untouched_outside_a_scoped_call(self):
        self.assertIsNone(api_scope.active_rules())
        found = self.env["res.partner"].name_search("LEAKED-ORACLE")
        self.assertIn(self.partner.id, [row[0] for row in found])


@tagged("post_install", "-at_install")
class TestComputedDerivationsAreHidden(ScopeCase):
    def _hidden(self, model):
        return api_scope.hidden_field_names(self.env, self.scope._rules(), model)

    def test_a_computed_field_that_prints_the_column_is_hidden_with_it(self):
        self.assertIn("email_formatted", self._hidden("res.partner"))

    def test_a_computed_field_that_answers_about_the_column_is_hidden_with_it(self):
        self.assertIn("same_vat_partner_id", self._hidden("res.partner"))

    def test_the_label_is_never_hidden(self):
        hidden = self._hidden("res.partner")
        self.assertNotIn("display_name", hidden)
        self.assertNotIn("name", hidden)

    def test_the_closure_crosses_a_relation_into_a_model_the_scope_names_not(self):
        # `res.users.email` is related to `partner_id.email`; the scope does
        # not reach res.users at all, and the closure still says what its
        # rows would leak if it did.
        self.assertIn("email", self._hidden("res.users"))
        self.assertIn("email_formatted", self._hidden("res.users"))

    def test_the_closure_is_one_pass_over_the_registry(self):
        # A closure taken per model recursed into every model a dependency
        # path crossed, again for every path and every iteration, and on a
        # registry of several hundred models a search timed out; one
        # fixpoint over the registry answers every model at once.
        rules = self.scope._rules()
        started = time.monotonic()
        self._hidden("res.partner")
        self.assertLess(time.monotonic() - started, 2.0)
        self.assertIn("res.users", rules._hidden, "every model, in the one pass")
        started = time.monotonic()
        self._hidden("res.company")
        self.assertLess(
            time.monotonic() - started, 0.01, "the second model is a lookup"
        )

    def test_the_rules_follow_a_write(self):
        before = self.scope._rules()
        self.scope.line_ids.write({"denied_field_ids": [(5, 0, 0)]})
        after = self.scope._rules()
        self.assertNotEqual(before, after)
        self.assertEqual(after.denied("res.partner"), frozenset())


@tagged("post_install", "-at_install")
class TestUnknownFieldsAreTheCallersMistake(ScopeCase):
    def test_a_close_match_is_suggested(self):
        with self.assertRaisesRegex(UserError, "did you mean 'name'"):
            self._call("search_read", [], ["nmae"])

    def test_a_reordered_name_is_suggested_first(self):
        with self.assertRaisesRegex(UserError, "did you mean 'email_formatted'"):
            self._call("search_read", [("formatted_email", "=", "x")])

    def test_sorting_across_a_relation_is_a_caller_error(self):
        with self.assertRaisesRegex(UserError, "sorting across a relation"):
            self._call("search", [], order="parent_id.name")

    def test_a_malformed_domain_is_a_caller_error(self):
        with self.assertRaisesRegex(UserError, "Malformed domain"):
            self._call("search_count", [["name"]])


@tagged("post_install", "-at_install")
class TestKeysAndScopes(TransactionCase):
    def test_a_key_bound_to_a_scope_opens_that_door_alone(self):
        user = new_test_user(self.env, login="scope_key_user", groups="base.group_user")
        keys = self.env["res.users.apikeys"].with_user(user)
        expires = fields.Datetime.now() + timedelta(hours=1)
        bound = keys._generate("rpc", "bound", expires)
        universal = keys._generate(None, "universal", expires)
        self.assertEqual(keys._check_credentials(scope="rpc", key=bound), user.id)
        self.assertIsNone(keys._check_credentials(scope="mcp", key=bound))
        self.assertEqual(keys._check_credentials(scope="mcp", key=universal), user.id)
        self.assertEqual(keys._check_credentials(scope="rpc", key=universal), user.id)

    def test_a_key_bound_to_an_archived_scope_opens_nothing(self):
        user = new_test_user(
            self.env, login="scope_archived_user", groups="base.group_user"
        )
        scope = self.env["res.users.apikeys.scope"].create(
            {"name": "Archived door", "key": "archived_door"}
        )
        keys = self.env["res.users.apikeys"].with_user(user)
        key = keys._generate(
            "archived_door", "k", fields.Datetime.now() + timedelta(hours=1)
        )
        self.assertEqual(
            keys._check_credentials(scope="archived_door", key=key), user.id
        )
        scope.action_archive()
        self.assertIsNone(keys._check_credentials(scope="archived_door", key=key))
        with self.assertRaises(AccessDenied):
            self.env["res.users"]._check_uid_passwd(user.id, key)

    def test_a_scope_string_nobody_described_is_a_record_reaching_everything(self):
        scope = self.env["res.users.apikeys.scope"]._get_or_create("never_seen")
        self.assertEqual((scope.key, scope.name), ("never_seen", "never_seen"))
        self.assertIsNone(scope._rules().models)
        self.assertEqual(
            self.env["res.users.apikeys.scope"]._get_or_create("never_seen"), scope
        )

    def test_the_rpc_password_check_names_the_rpc_scope_for_a_key(self):
        user = new_test_user(self.env, login="scope_rpc_user", groups="base.group_user")
        key = (
            self.env["res.users.apikeys"]
            .with_user(user)
            ._generate("rpc", "k", fields.Datetime.now() + timedelta(hours=1))
        )
        Users = self.env["res.users"]
        self.assertEqual(
            Users._check_uid_passwd(user.id, key),
            self.env.ref("base.apikeys_scope_rpc").id,
        )
        self.assertIsNone(Users._check_uid_passwd(user.id, "scope_rpc_user"))

    def test_a_user_without_a_password_still_enters_rpc_with_a_key(self):
        user = new_test_user(
            self.env, login="scope_nopass_user", groups="base.group_user"
        )
        key = (
            self.env["res.users.apikeys"]
            .with_user(user)
            ._generate("rpc", "k", fields.Datetime.now() + timedelta(hours=1))
        )
        user._clear_password()
        self.env.flush_all()
        Users = self.env["res.users"]
        self.assertEqual(
            Users._check_uid_passwd(user.id, key),
            self.env.ref("base.apikeys_scope_rpc").id,
        )
        with self.assertRaises(AccessDenied):
            Users._check_uid_passwd(user.id, "anything")

    def test_a_key_bound_to_another_door_enters_xmlrpc_under_its_own_scope(self):
        user = new_test_user(
            self.env, login="scope_bound_user", groups="base.group_user"
        )
        mcp = self.env["res.users.apikeys.scope"].create({"name": "MCP", "key": "mcp"})
        key = (
            self.env["res.users.apikeys"]
            .with_user(user)
            ._generate("mcp", "k", fields.Datetime.now() + timedelta(hours=1))
        )
        self.assertEqual(self.env["res.users"]._check_uid_passwd(user.id, key), mcp.id)


@tagged("post_install", "-at_install")
class TestScopeRecords(TransactionCase):
    def test_a_data_record_adopts_the_row_a_migration_made_for_its_key(self):
        """base 1.89 makes a row per scope string keys already carry, before
        the module that describes that door loads its data record."""
        Scope = self.env["res.users.apikeys.scope"]
        made = Scope._get_or_create("door.described.later")
        self.assertEqual(made.name, "door.described.later")

        described, other = Scope.create(
            [
                {"name": "Described", "key": "door.described.later", "max_depth": 3},
                {"name": "Other", "key": "door.other"},
            ]
        )

        self.assertEqual(described, made, "the same row, in the caller's order")
        self.assertEqual((described.name, described.max_depth), ("Described", 3))
        self.assertEqual(other.key, "door.other")
        self.assertEqual(Scope.search_count([("key", "=", "door.described.later")]), 1)

    def test_a_door_only_scope_reaches_no_model_at_the_universal_door(self):
        Scope = self.env["res.users.apikeys.scope"]
        door = Scope.create({"name": "Door", "key": "door.only", "door_only": True})
        self.assertIsNone(door._rules().rule("res.partner"))
        with self.assertRaises(AccessError):
            call_kw(
                self.env["res.partner"].with_context(api_scope_id=door.id),
                "search_count",
                [[]],
                {},
            )
        door.door_only = False
        self.assertIsNotNone(door._rules().rule("res.partner"), "every model again")
