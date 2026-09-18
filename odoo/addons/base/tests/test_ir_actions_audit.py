from unittest.mock import patch

from psycopg.errors import IntegrityError

from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger
from odoo.tools.safe_eval import safe_eval

from odoo.addons.base.models.ir_actions_actions import _eval_dict_or_default

_ACTIONS_LOGGER = _eval_dict_or_default.__module__

_ABOLISHED_ACTION_METHODS = (
    "_apply_unenforced_ondelete",
    "_as_concrete",
    "_cache_invalidating_fields",
    "_compute_embedded_actions",
    "_concrete_model_names",
    "_empty_list_help",
    "_for_xml_id",
    "_get_client_only_keys",
    "_get_readable_fields",
    "_inheritance_tree_model_names",
    "_menu_access_model_field",
    "_reserve_paths",
    "_root_model_names",
    "_tree_model_names_by_table",
    "_unconditional_clear_fields",
    "_unenforced_reference_fields",
    "_unenforced_reference_relations",
    "_unenforced_reference_selections",
    "_window_view_types",
)


def raises_without_rolling_back(case, exception, func):
    try:
        func()
    except exception as exc:
        return exc
    case.fail(f"{exception.__name__} was not raised")
    return None


@tagged("post_install", "-at_install")
class TestIrActionsExists(TransactionCase):
    def test_exists_reflects_uncommitted_create(self):
        model = self.env["ir.actions.act_url"]
        action = model.create({"name": "audit-ira-l1", "url": "/audit/ira-l1"})
        self.assertEqual(action.exists(), action)

    def test_get_bindings_still_resolves(self):
        Actions = self.env["ir.actions.actions"]
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-binding-shape",
                "res_model": "res.partner",
                "binding_model_id": self.env["ir.model"]._get_id("res.partner"),
            }
        )
        bindings = Actions._get_bindings("res.partner")
        self.assertTrue(bindings, "the action just created must show up")

        vocabulary = set(
            self.env["ir.actions.actions"]._fields["binding_type"].get_values(self.env)
        )
        for binding_type, bucket in bindings.items():
            with self.subTest(binding_type=binding_type):
                self.assertIn(binding_type, vocabulary)
                self.assertIsInstance(bucket, tuple)
                for entry in bucket:
                    self.assertIn("id", entry)
        self.assertIn(
            action.id,
            [entry["id"] for bucket in bindings.values() for entry in bucket],
        )


@tagged("post_install", "-at_install")
class TestIrActionsBindingsCacheOnCreate(TransactionCase):
    def test_unbound_create_keeps_bindings_cache(self):
        Actions = self.env["ir.actions.actions"]
        before = Actions._get_bindings("res.partner")
        self.env["ir.actions.act_window"].create(
            {"name": "audit-unbound-action", "res_model": "res.partner"}
        )
        self.assertIs(Actions._get_bindings("res.partner"), before)

    def test_bound_create_clears_bindings_cache(self):
        Actions = self.env["ir.actions.actions"]
        Actions._get_bindings("res.partner")
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-bound-action",
                "res_model": "res.partner",
                "binding_model_id": self.env["ir.model"]._get("res.partner").id,
            }
        )
        bindings = Actions._get_bindings("res.partner")
        self.assertIn(
            action.id,
            [a["id"] for bucket in bindings.values() for a in bucket],
            "a bound create must invalidate the cache so the binding shows up",
        )


@tagged("post_install", "-at_install")
class TestSafeEvalDict(TransactionCase):
    def test_eval_dict_or_default_degrades(self):
        self.assertEqual(_eval_dict_or_default("{'a': 1}", {}, {}), {"a": 1})
        self.assertEqual(_eval_dict_or_default(False, {}, {"d": 1}), {})
        sentinel = {"d": 1}
        self.assertIs(_eval_dict_or_default("1/0", {}, sentinel), sentinel)
        self.assertIs(_eval_dict_or_default("[(", {}, sentinel), sentinel)
        self.assertIs(_eval_dict_or_default("[1, 2]", {}, sentinel), sentinel)
        self.assertEqual(_eval_dict_or_default("{'u': uid}", {"uid": 7}, {}), {"u": 7})

    def test_a_missing_name_reads_as_false_and_keeps_the_rest(self):
        self.assertEqual(
            _eval_dict_or_default(
                "{'search_default_x': 1, 'default_p': active_id, 'q': other}", {}, {}
            ),
            {"search_default_x": 1, "default_p": False, "q": False},
        )
        given = {"uid": 7}
        _eval_dict_or_default("{'a': missing}", given, {})
        self.assertEqual(given, {"uid": 7}, "the caller's context is not mutated")

    def test_an_act_window_context_survives_a_missing_active_id(self):
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-ctx",
                "res_model": "res.partner",
                "context": "{'search_default_x': 1, 'default_parent_id': active_id}",
            }
        )
        self.assertEqual(
            action._eval_action_context(action.context),
            {"search_default_x": 1, "default_parent_id": False},
        )

    def test_an_act_window_context_reads_the_allowed_companies(self):
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-companies",
                "res_model": "res.partner",
                "context": "{'default_company_id': allowed_company_ids[0]}",
            }
        )
        self.assertNotIn("allowed_company_ids", action.env.context)
        with self.assertNoLogs("odoo.addons.base.models.ir_actions_actions", "WARNING"):
            self.assertEqual(
                action._eval_action_context(action.context),
                {"default_company_id": self.env.company.id},
            )
        self.assertEqual(
            action.with_context(allowed_company_ids=[42])._eval_action_context(
                action.context
            ),
            {"default_company_id": 42},
            "a context the page sent keeps its own list",
        )


@tagged("post_install", "-at_install")
class TestIrActionsUnlinkCascadesEmbedded(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_action = cls.env["ir.actions.act_window"].create(
            {"name": "audit-embedded-parent", "res_model": "res.partner"}
        )
        cls.target_action = cls.env["ir.actions.act_window"].create(
            {"name": "audit-embedded-target", "res_model": "res.partner"}
        )

    def _create_embedded(self):
        return self.env["ir.embedded.actions"].create(
            {
                "parent_action_id": self.parent_action.id,
                "parent_res_model": "res.partner",
                "action_id": self.target_action.id,
            }
        )

    def test_unlink_cascades_deletable_embedded_actions(self):
        embedded = self._create_embedded()
        self.target_action.unlink()
        self.assertFalse(
            embedded.exists(),
            "deleting an action must cascade-delete its embedded actions",
        )

    def test_unlink_blocked_by_seeded_embedded_action(self):
        embedded = self._create_embedded()
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "audit_seeded_embedded_action",
                "model": "ir.embedded.actions",
                "res_id": embedded.id,
            }
        )
        with self.assertRaises(UserError):
            self.target_action.unlink()
        self.assertTrue(embedded.exists())
        self.assertTrue(self.target_action.exists())


@tagged("post_install", "-at_install")
class TestEmbeddedActionsGroupIdsConvention(TransactionCase):
    def test_group_ids_field_renamed(self):
        fields = self.env["ir.embedded.actions"]._fields
        self.assertIn("group_ids", fields)
        self.assertNotIn("groups_ids", fields)
        self.assertIn(
            "group_ids",
            self.env["ir.embedded.actions"]._get_fields_readable(),
        )


@tagged("post_install", "-at_install")
class TestIrActionsUnenforcedReferences(TransactionCase):
    def test_registry_sweep_lists_every_declared_reference(self):
        Actions = self.env["ir.actions.actions"]
        declared = {
            (model_name, field_name)
            for model_name, model in self.env.registry.items()
            if not model._abstract
            for field_name, field in model._fields.items()
            if field.type == "many2one"
            and field.store
            and not field.related
            and field.comodel_name
            in ("ir.actions.actions", "ir.actions.act_window_close")
        }
        swept = {(m, f) for m, f, __ in Actions._get_fields_ondelete_unenforced()}
        self.assertEqual(swept, declared)

    def test_no_real_foreign_key_backs_those_fields(self):
        self.env.cr.execute(
            """
            SELECT count(*) FROM pg_constraint con
              JOIN pg_class fcl ON fcl.oid = con.confrelid
             WHERE con.contype = 'f' AND fcl.relname = 'ir_actions'
            """
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0)

    def test_cascade_reference_is_deleted(self):
        action = self.env["ir.actions.act_window"].create(
            {"name": "audit-sweep-cascade", "res_model": "res.partner"}
        )
        filter_ = self.env["ir.filters"].create(
            {
                "name": "audit-sweep-filter",
                "model_id": "res.partner",
                "action_id": action.id,
            }
        )
        todo = self.env["ir.actions.todo"].create({"action_id": action.id})
        action.unlink()
        self.assertFalse(filter_.exists())
        self.assertFalse(todo.exists())

    def test_set_null_reference_is_cleared(self):
        action = self.env["ir.actions.act_window"].create(
            {"name": "audit-sweep-home", "res_model": "res.partner"}
        )
        user = self.env["res.users"].create(
            {
                "login": "audit-sweep-user",
                "name": "audit-sweep-user",
                "action_id": action.id,
            }
        )
        action.unlink()
        self.assertFalse(user.action_id)

    def test_todo_action_id_declares_cascade(self):
        self.assertEqual(
            self.env["ir.actions.todo"]._fields["action_id"].ondelete, "cascade"
        )


@tagged("post_install", "-at_install")
class TestIrActionsCacheInvalidation(TransactionCase):
    def test_path_write_invalidates_menu_cache(self):
        menu = self.env["ir.ui.menu"].search([("action", "!=", False)], limit=1)
        action = self.env[menu.action._name].browse(menu.action.id)
        action.path = "audit_cache_path_before"
        self.env.flush_all()
        self.env.registry.clear_cache()

        self.assertEqual(
            self.env["ir.ui.menu"].load_menus(False)[menu.id]["action_path"],
            "audit_cache_path_before",
        )
        action.write({"path": "audit_cache_path_after"})
        self.env.flush_all()
        self.assertEqual(
            self.env["ir.ui.menu"].load_menus(False)[menu.id]["action_path"],
            "audit_cache_path_after",
        )

    def test_inert_field_write_keeps_cache(self):
        Actions = self.env["ir.actions.actions"]
        action = self.env["ir.actions.act_window"].create(
            {"name": "audit-inert", "res_model": "res.partner"}
        )
        self.env.flush_all()
        before = Actions._get_bindings("res.partner")
        action.write({"limit": 42})
        self.assertIs(Actions._get_bindings("res.partner"), before)


@tagged("post_install", "-at_install")
class TestIrActionsComputeDependencies(TransactionCase):
    def test_embedded_actions_are_per_active_record(self):
        partner_a = self.env["res.partner"].create({"name": "audit-emb-A"})
        partner_b = self.env["res.partner"].create({"name": "audit-emb-B"})
        parent = self.env["ir.actions.act_window"].create(
            {"name": "audit-emb-parent", "res_model": "res.partner"}
        )
        target = self.env["ir.actions.act_window"].create(
            {"name": "audit-emb-target", "res_model": "res.partner"}
        )
        embedded = self.env["ir.embedded.actions"].create(
            {
                "parent_action_id": parent.id,
                "parent_res_model": "res.partner",
                "action_id": target.id,
                "parent_res_id": partner_a.id,
            }
        )
        self.env.flush_all()

        ctx_a = {"active_id": partner_a.id, "active_model": "res.partner"}
        ctx_b = {"active_id": partner_b.id, "active_model": "res.partner"}
        self.assertEqual(
            parent.with_context(**ctx_a).embedded_action_ids.ids, embedded.ids
        )
        self.assertEqual(parent.with_context(**ctx_b).embedded_action_ids.ids, [])

    def test_views_follow_view_ids_sequence(self):
        list_view = self.env["ir.ui.view"].search(
            [("type", "=", "list"), ("model", "=", "res.partner")], limit=1
        )
        form_view = self.env["ir.ui.view"].search(
            [("type", "=", "form"), ("model", "=", "res.partner")], limit=1
        )
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-views",
                "res_model": "res.partner",
                "view_mode": "list,form",
            }
        )
        line = self.env["ir.actions.act_window.view"].create(
            {
                "act_window_id": action.id,
                "view_id": list_view.id,
                "view_mode": "list",
                "sequence": 1,
            }
        )
        self.env["ir.actions.act_window.view"].create(
            {
                "act_window_id": action.id,
                "view_id": form_view.id,
                "view_mode": "form",
                "sequence": 2,
            }
        )
        self.assertEqual(action.views[0], (list_view.id, "list"))
        line.sequence = 99
        self.assertEqual(action.views[0], (form_view.id, "form"))

    def test_client_params_depend_on_uid(self):
        params_field = self.env["ir.actions.client"]._fields["params"]
        __depends, depends_context = params_field.get_depends(
            self.env["ir.actions.client"]
        )
        self.assertIn("uid", depends_context)


@tagged("post_install", "-at_install")
class TestIrActionsReadableFieldsAreFields(TransactionCase):
    def _action_models(self):
        Actions = self.env.registry["ir.actions.actions"]
        return [
            name
            for name, model in self.env.registry.items()
            if issubclass(model, Actions)
        ]

    def test_readable_fields_are_all_orm_fields(self):
        for name in self.assertSweep(self._action_models()):
            model = self.env[name]
            virtual = sorted(
                f for f in model._get_fields_readable() if f not in model._fields
            )
            self.assertFalse(virtual, "%s lists non-fields %s" % (name, virtual))

    def test_client_only_keys_are_not_orm_fields(self):
        for name in self.assertSweep(self._action_models()):
            model = self.env[name]
            stored = sorted(
                k for k in model._get_keys_client_only() if k in model._fields
            )
            self.assertFalse(stored, "%s lists real fields %s" % (name, stored))

    def test_clean_action_keeps_client_only_keys(self):
        from odoo.addons.web.controllers.utils import clean_action

        with self.assertNoLogs("odoo.addons.web.controllers.utils", "WARNING"):
            cleaned = clean_action(
                {"type": "ir.actions.act_window_close", "effect": {"type": "rainbow"}},
                env=self.env,
            )
        self.assertEqual(cleaned["effect"], {"type": "rainbow"})

    def test_action_dict_key_order_is_deterministic(self):
        action = self.env["ir.actions.act_window"].create(
            {"name": "audit-order", "res_model": "res.partner"}
        )
        readable = action._get_fields_readable()
        keys = list(action._get_action_dict())
        self.assertEqual(set(keys), set(readable))
        self.assertEqual(keys, list(action.sudo().read(sorted(readable))[0]))
        self.assertNotEqual(
            keys, list(action.sudo().read(sorted(readable, reverse=True))[0])
        )


@tagged("post_install", "-at_install")
class TestIrActionsTodoOpenState(TransactionCase):
    def _make_todo(self, sequence):
        return self.env["ir.actions.todo"].create(
            {
                "action_id": self.env.ref("base.action_client_base_menu").id,
                "sequence": sequence,
            }
        )

    def test_reopening_a_todo_wins_over_older_open_ones(self):
        self.env["ir.actions.todo"].search([]).write({"state": "done"})
        early = self._make_todo(1)
        late = self._make_todo(5)
        self.env.flush_all()

        early.action_open()
        self.assertEqual(early.state, "open")
        self.assertEqual(late.state, "done")

        late.action_open()
        self.assertEqual(late.state, "open")
        self.assertEqual(early.state, "done")

    def test_only_one_todo_stays_open(self):
        self.env["ir.actions.todo"].search([]).write({"state": "done"})
        self._make_todo(1)
        self._make_todo(2)
        self._make_todo(3)
        self.assertEqual(
            self.env["ir.actions.todo"].search_count([("state", "=", "open")]), 1
        )

    def test_action_launch_returns_only_readable_fields(self):
        server_action = self.env["ir.actions.server"].create(
            {
                "name": "audit-launch-server",
                "model_id": self.env["ir.model"]._get("res.partner").id,
                "state": "code",
                "code": "record.name",
            }
        )
        todo = self.env["ir.actions.todo"].create({"action_id": server_action.id})
        result = todo.action_launch()
        self.assertEqual(todo.state, "done")
        self.assertLessEqual(set(result), server_action._get_fields_readable())
        self.assertNotIn("code", result)

    def test_unlink_keeps_open_menu_and_deletes_the_rest(self):
        open_menu = self.env.ref("base.open_menu")
        other = self._make_todo(50)
        (open_menu | other).unlink()
        self.assertTrue(open_menu.exists())
        self.assertFalse(other.exists())
        self.assertEqual(
            open_menu.action_id.id, self.env.ref("base.action_client_base_menu").id
        )


@tagged("post_install", "-at_install")
class TestIrActionsActWindowValidation(TransactionCase):
    def test_empty_view_mode_segment_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["ir.actions.act_window"].create(
                {
                    "name": "audit-empty-mode",
                    "res_model": "res.partner",
                    "view_mode": "list,,form",
                }
            )

    def test_create_does_not_mutate_caller_vals(self):
        vals = {"res_model": "res.partner"}
        self.env["ir.actions.act_window"].create([vals])
        self.assertEqual(vals, {"res_model": "res.partner"})

    def test_create_still_defaults_the_name(self):
        action = self.env["ir.actions.act_window"].create({"res_model": "res.partner"})
        self.assertEqual(action.name, self.env["res.partner"]._description)


@tagged("post_install", "-at_install")
class TestIrActionsUnlinkIsAtomic(TransactionCase):
    def setUp(self):
        super().setUp()
        self.action = self.env["ir.actions.act_window"].create(
            {"name": "audit-atomic-target", "res_model": "res.partner"}
        )
        self.parent = self.env["ir.actions.act_window"].create(
            {"name": "audit-atomic-parent", "res_model": "res.partner"}
        )

    def _seeded_embedded_action(self):
        embedded = self.env["ir.embedded.actions"].create(
            {
                "parent_action_id": self.parent.id,
                "parent_res_model": "res.partner",
                "action_id": self.action.id,
            }
        )
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "audit_atomic_seeded_embedded",
                "model": "ir.embedded.actions",
                "res_id": embedded.id,
            }
        )
        return embedded

    def test_failed_unlink_keeps_earlier_cascades(self):
        todo = self.env["ir.actions.todo"].create({"action_id": self.action.id})
        embedded = self._seeded_embedded_action()

        raises_without_rolling_back(self, UserError, self.action.unlink)

        self.env.invalidate_all()
        self.assertTrue(self.action.exists(), "the action itself survived")
        self.assertTrue(embedded.exists(), "the blocking reference survived")
        self.assertTrue(
            todo.exists(),
            "a reference deleted earlier in the sweep must be restored when the "
            "sweep aborts, exactly as a foreign key cascade would be",
        )

    def test_failed_unlink_keeps_earlier_set_null(self):
        user = self.env["res.users"].create(
            {
                "login": "audit-atomic-user",
                "name": "audit-atomic-user",
                "action_id": self.action.id,
            }
        )
        Actions = type(self.env["ir.actions.actions"])
        with patch.object(
            Actions,
            "_get_relations_ondelete_unenforced",
            side_effect=UserError("audit-atomic-boom"),
        ):
            error = raises_without_rolling_back(self, UserError, self.action.unlink)
        self.assertEqual(str(error), "audit-atomic-boom")

        self.env.invalidate_all()
        self.assertEqual(
            user.action_id.id,
            self.action.id,
            "a set-null applied earlier in the sweep must be restored when a "
            "later step of the same sweep aborts",
        )
        self.assertTrue(self.action.exists())

    def test_restrict_is_resolved_before_anything_is_destroyed(self):
        todo = self.env["ir.actions.todo"].create({"action_id": self.action.id})
        Actions = self.env.registry["ir.actions.actions"]
        self.patch(
            Actions,
            "_get_fields_ondelete_unenforced",
            lambda records: (
                ("ir.actions.todo", "action_id", "cascade"),
                ("res.users", "action_id", "restrict"),
            ),
        )
        self.env["res.users"].create(
            {
                "login": "audit-restrict-user",
                "name": "audit-restrict-user",
                "action_id": self.action.id,
            }
        )
        raises_without_rolling_back(self, ValidationError, self.action.unlink)
        self.env.invalidate_all()
        self.assertTrue(todo.exists())
        self.assertTrue(self.action.exists())

    def test_related_reference_field_normalises_its_ondelete(self):
        policies = {
            ondelete
            for __, __, ondelete in self.env[
                "ir.actions.actions"
            ]._get_fields_ondelete_unenforced()
        }
        self.assertNotIn(None, policies)
        self.assertLessEqual(policies, {"cascade", "restrict", "set null"})


@tagged("post_install", "-at_install")
class TestIrActionsRootModelUnlink(TransactionCase):
    def test_unlink_through_the_root_model_cleans_up_the_xml_id(self):
        action = self.env["ir.actions.act_window"].create(
            {"name": "audit-root-unlink", "res_model": "res.partner"}
        )
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "audit_root_unlink_action",
                "model": "ir.actions.act_window",
                "res_id": action.id,
            }
        )
        self.env["ir.actions.actions"].browse(action.id).unlink()
        self.env.flush_all()

        self.env.cr.execute(
            "SELECT count(*) FROM ONLY ir_act_window WHERE id = %s", [action.id]
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0)
        self.env.cr.execute(
            "SELECT count(*) FROM ir_model_data WHERE model = %s AND res_id = %s",
            ["ir.actions.act_window", action.id],
        )
        self.assertEqual(
            self.env.cr.fetchone()[0], 0, "the xml id must not outlive its record"
        )

    def test_unlink_through_the_root_model_runs_subtype_guards(self):
        action = self.env["ir.actions.act_window"].create(
            {"name": "audit-root-guard", "res_model": "res.partner"}
        )
        parent = self.env["ir.actions.act_window"].create(
            {"name": "audit-root-guard-parent", "res_model": "res.partner"}
        )
        embedded = self.env["ir.embedded.actions"].create(
            {
                "parent_action_id": parent.id,
                "parent_res_model": "res.partner",
                "action_id": action.id,
            }
        )
        self.env["ir.actions.actions"].browse(action.id).unlink()
        self.assertFalse(embedded.exists())


@tagged("post_install", "-at_install")
class TestIrActionsBindingGroupsStayIds(TransactionCase):
    def setUp(self):
        super().setUp()
        self.group = self.env["res.groups"].create(
            {"name": "audit-binding-group", "user_ids": [(4, self.env.uid)]}
        )
        self.model_id = self.env["ir.model"]._get_id("res.currency")
        self.action = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-binding-action",
                "res_model": "res.currency",
                "binding_model_id": self.model_id,
                "group_ids": [(6, 0, self.group.ids)],
            }
        )
        self.env.flush_all()
        self.env.registry.clear_cache()

    def _bound_names(self):
        bindings = self.env["ir.actions.actions"].get_bindings("res.currency")
        return {action["name"] for actions in bindings.values() for action in actions}

    def test_reading_bindings_creates_no_xml_id(self):
        self.env["ir.actions.actions"]._get_bindings("res.currency")
        self.env.cr.execute(
            "SELECT count(*) FROM ir_model_data WHERE model = 'res.groups' AND res_id = %s",
            [self.group.id],
        )
        self.assertEqual(
            self.env.cr.fetchone()[0], 0, "a cached read must not write to the database"
        )

    def test_cached_group_ids_are_ids(self):
        bindings = self.env["ir.actions.actions"]._get_bindings("res.currency")
        entries = [
            action
            for actions in bindings.values()
            for action in actions
            if action["name"] == "audit-binding-action"
        ]
        self.assertEqual([entry["group_ids"] for entry in entries], [(self.group.id,)])

    def test_member_sees_the_binding_without_an_xml_id(self):
        self.assertIn("audit-binding-action", self._bound_names())

    def test_non_member_does_not_see_the_binding(self):
        other = self.env["res.users"].create(
            {"login": "audit-binding-outsider", "name": "audit-binding-outsider"}
        )
        names = {
            action["name"]
            for actions in self.env["ir.actions.actions"]
            .with_user(other)
            .get_bindings("res.currency")
            .values()
            for action in actions
        }
        self.assertNotIn("audit-binding-action", names)

    def test_binding_survives_a_groups_only_invalidation(self):
        self.assertIn("audit-binding-action", self._bound_names())
        self.env.registry.clear_cache("groups")
        self.assertIn("audit-binding-action", self._bound_names())


@tagged("post_install", "-at_install")
class TestIrActionsBindingAccess(TransactionCase):
    def setUp(self):
        super().setUp()
        self.model_id = self.env["ir.model"]._get_id("ir.module.module")
        self.env["ir.actions.server"].create(
            {
                "name": "audit-acl-server",
                "model_id": self.model_id,
                "state": "code",
                "code": "pass",
                "binding_model_id": self.model_id,
            }
        )
        self.portal = self.env["res.users"].create(
            {
                "login": "audit-acl-portal",
                "name": "audit-acl-portal",
                "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )
        self.env.flush_all()
        self.env.registry.clear_cache()

    def test_unreadable_model_yields_no_bindings(self):
        Access = self.env["ir.model.access"].with_user(self.portal)
        self.assertFalse(Access.check("ir.module.module", "read", False))
        self.assertEqual(
            self.env["ir.actions.actions"]
            .with_user(self.portal)
            .get_bindings("ir.module.module"),
            {},
        )

    def test_unknown_model_yields_no_bindings(self):
        self.assertEqual(
            self.env["ir.actions.actions"].get_bindings("no.such.model"), {}
        )

    def test_readable_model_still_yields_its_bindings(self):
        names = {
            action["name"]
            for actions in self.env["ir.actions.actions"]
            .get_bindings("ir.module.module")
            .values()
            for action in actions
        }
        self.assertIn("audit-acl-server", names)


@tagged("post_install", "-at_install")
class TestIrActionsEmbeddedInvalidation(TransactionCase):
    def test_new_embedded_action_is_visible_immediately(self):
        parent = self.env["ir.actions.act_window"].create(
            {"name": "audit-embedded-invalidation", "res_model": "res.partner"}
        )
        partner = self.env["res.partner"].create({"name": "audit-embedded-partner"})
        scoped = parent.with_context(active_id=partner.id, active_model="res.partner")
        self.assertFalse(scoped.embedded_action_ids)

        embedded = self.env["ir.embedded.actions"].create(
            {
                "name": "audit-embedded-new",
                "parent_action_id": parent.id,
                "parent_res_model": "res.partner",
                "python_method": "action_archive",
            }
        )
        self.assertEqual(scoped.embedded_action_ids, embedded)


@tagged("post_install", "-at_install")
class TestIrActionsViewModeVocabulary(TransactionCase):
    def test_view_mode_is_view_type_minus_the_non_window_ones(self):
        from odoo.addons.base.models.ir_actions_act_window_view import (
            NON_WINDOW_VIEW_TYPES,
        )

        view_modes = set(
            self.env["ir.actions.act_window.view"]
            ._fields["view_mode"]
            .get_values(self.env)
        )
        view_types = set(self.env["ir.ui.view"]._fields["type"].get_values(self.env))
        self.assertEqual(
            view_types - view_modes,
            set(NON_WINDOW_VIEW_TYPES),
            "a view type was added to ir.ui.view without extending view_mode",
        )
        self.assertFalse(
            view_modes - view_types,
            "view_mode offers a mode that is not an ir.ui.view type",
        )


@tagged("post_install", "-at_install")
class TestIrActionsTodoLaunchContext(TransactionCase):
    def test_launch_keeps_a_context_referencing_the_eval_context(self):
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-todo-ctx",
                "res_model": "res.partner",
                "context": "{'default_user_id': uid, 'search_default_x': 1}",
            }
        )
        todo = self.env["ir.actions.todo"].create({"action_id": action.id})
        context = todo.action_launch()["context"]
        self.assertEqual(
            context,
            {
                "default_user_id": self.env.uid,
                "search_default_x": 1,
                "disable_log": True,
            },
        )


@tagged("post_install", "-at_install")
class TestIrActionsTableInheritanceRoot(TransactionCase):
    def test_the_root_declares_itself(self):
        self.assertTrue(
            self.env["ir.actions.actions"]._is_table_inheritance_root(),
            "without the declaration the ORM creates foreign keys to ir_actions "
            "that reject every id living in a subtype table",
        )

    def test_subtypes_are_ordinary_tables(self):
        for name in ("ir.actions.act_window", "ir.actions.server", "ir.actions.report"):
            with self.subTest(model=name):
                self.assertFalse(self.env[name]._is_table_inheritance_root())

    def test_a_foreign_key_to_the_root_would_reject_a_subtype_row(self):
        self.env.cr.execute("SELECT id FROM ir_act_window LIMIT 1")
        [act_window_id] = self.env.cr.fetchone()
        with self.assertRaises(IntegrityError), mute_logger("odoo.db.cursor"):
            with self.env.cr.savepoint():
                self.env.cr.execute("CREATE TABLE audit_root_fk (act_id integer)")
                self.env.cr.execute(
                    "ALTER TABLE audit_root_fk ADD CONSTRAINT audit_root_fk_con "
                    "FOREIGN KEY (act_id) REFERENCES ir_actions(id)"
                )
                self.env.cr.execute(
                    "INSERT INTO audit_root_fk VALUES (%s)", [act_window_id]
                )

    def test_many2many_relations_to_the_root_are_swept_on_unlink(self):
        Actions = self.env["ir.actions.actions"]
        roots = Actions._get_model_names_in_root_table()
        declared = {
            (field.relation, column)
            for model_name, model in self.env.registry.items()
            if not model._abstract
            for field in model._fields.values()
            if field.type == "many2many" and field.store
            for column, end in (
                (field.column2, field.comodel_name),
                (field.column1, model_name),
            )
            if end in roots
        }
        self.assertEqual(set(Actions._get_relations_ondelete_unenforced()), declared)

    def test_no_foreign_key_backs_either_end_of_such_a_relation(self):
        Actions = self.env["ir.actions.actions"]
        for relation, column in Actions._get_relations_ondelete_unenforced():
            with self.subTest(relation=relation, column=column):
                self.env.cr.execute(
                    """
                    SELECT 1 FROM information_schema.key_column_usage k
                      JOIN information_schema.table_constraints t
                        ON t.constraint_name = k.constraint_name
                     WHERE t.constraint_type = 'FOREIGN KEY'
                       AND k.table_name = %s AND k.column_name = %s
                    """,
                    [relation, column],
                )
                self.assertIsNone(self.env.cr.fetchone())


@tagged("post_install", "-at_install")
class TestIrActionsPathUniquenessAcrossSubtypes(TransactionCase):
    def _duplicate_rows(self, path):
        self.env.cr.execute(
            "SELECT id, type FROM ir_actions WHERE path = %s ORDER BY id", [path]
        )
        return self.env.cr.fetchall()

    def test_pending_write_on_a_sibling_subtype_is_seen(self):
        window = self.env["ir.actions.act_window"].create(
            {"name": "audit-path-w", "res_model": "res.currency"}
        )
        self.env.flush_all()
        window.path = "audit-dupe-a"
        with self.assertRaises(IntegrityError), mute_logger("odoo.db.cursor"):
            with self.env.cr.savepoint():
                self.env["ir.actions.client"].create(
                    {"name": "audit-path-c", "tag": "audit", "path": "audit-dupe-a"}
                )
                self.env.flush_all()
        self.env.clear()

    def test_two_subtypes_written_in_one_transaction(self):
        window = self.env["ir.actions.act_window"].create(
            {"name": "audit-path-w2", "res_model": "res.currency"}
        )
        client = self.env["ir.actions.client"].create(
            {"name": "audit-path-c2", "tag": "audit"}
        )
        self.env.flush_all()
        with self.assertRaises(IntegrityError), mute_logger("odoo.db.cursor"):
            with self.env.cr.savepoint():
                window.path = "audit-dupe-b"
                client.path = "audit-dupe-b"
                self.env.flush_all()
        self.env.clear()
        self.assertEqual(self._duplicate_rows("audit-dupe-b"), [])

    def test_a_free_path_is_still_accepted(self):
        window = self.env["ir.actions.act_window"].create(
            {"name": "audit-path-w3", "res_model": "res.currency", "path": "audit-free"}
        )
        self.env.flush_all()
        self.assertEqual(len(self._duplicate_rows("audit-free")), 1)
        self.assertEqual(window.path, "audit-free")

    def test_tree_covers_every_subtype(self):
        Actions = self.env["ir.actions.actions"]
        expected = {
            name
            for name, model in self.env.registry.items()
            if not model._abstract and model._table_inheritance_root == "ir_actions"
        }
        self.assertEqual(Actions._get_model_names_in_tree(), expected)
        self.assertLessEqual(Actions._get_model_names_in_root_table(), expected)
        self.assertIn("ir.actions.act_window", expected)


@tagged("post_install", "-at_install")
class TestIrActionsUnenforcedReferencesOwnership(TransactionCase):
    def test_only_owned_columns_are_swept(self):
        Actions = self.env["ir.actions.actions"]
        roots = Actions._get_model_names_in_root_table()
        expected = {
            (model_name, field.name, field.ondelete)
            for model_name, model in self.env.registry.items()
            if not model._abstract
            for field in model._fields.values()
            if field.type == "many2one"
            and field.store
            and not field.related
            and field.comodel_name in roots
        }
        self.assertEqual(set(Actions._get_fields_ondelete_unenforced()), expected)

    def test_no_related_or_unstored_field_is_swept(self):
        for model_name, field_name, ondelete in self.assertSweep(
            self.env["ir.actions.actions"]._get_fields_ondelete_unenforced()
        ):
            field = self.env[model_name]._fields[field_name]
            with self.subTest(field=f"{model_name}.{field_name}"):
                self.assertTrue(field.store)
                self.assertFalse(field.related)
                self.assertIn(ondelete, ("cascade", "set null", "restrict"))

    def test_every_policy_found_is_dispatched(self):
        policies = {
            ondelete
            for __, __, ondelete in self.env[
                "ir.actions.actions"
            ]._get_fields_ondelete_unenforced()
        }
        self.assertLessEqual(policies, {"restrict", "cascade", "set null"})


@tagged("post_install", "-at_install")
class TestIrActionsBindingOrder(TransactionCase):
    def test_id_breaks_ties_across_action_types(self):
        model_id = self.env["ir.model"]._get_id("res.currency")
        Actions = self.env["ir.actions.actions"]
        server = self.env["ir.actions.server"].create(
            {
                "name": "audit-order-server",
                "model_id": model_id,
                "state": "code",
                "code": "pass",
                "binding_model_id": model_id,
            }
        )
        window = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-order-window",
                "res_model": "res.currency",
                "binding_model_id": model_id,
            }
        )
        self.env.registry.clear_cache()
        ids = [vals["id"] for vals in Actions._get_bindings("res.currency")["action"]]
        self.assertLess(server.id, window.id)
        self.assertLess(ids.index(server.id), ids.index(window.id))

    def test_binding_sequence_wins_over_id_across_action_types(self):
        model_id = self.env["ir.model"]._get_id("res.currency")
        Actions = self.env["ir.actions.actions"]
        common = {
            "model_id": model_id,
            "state": "code",
            "code": "pass",
            "binding_model_id": model_id,
        }
        first = self.env["ir.actions.server"].create(
            {**common, "name": "audit-seq-late", "binding_sequence": 90}
        )
        second = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-seq-early",
                "res_model": "res.currency",
                "binding_model_id": model_id,
                "binding_sequence": 1,
            }
        )
        self.env.registry.clear_cache()
        ids = [vals["id"] for vals in Actions._get_bindings("res.currency")["action"]]
        self.assertLess(first.id, second.id)
        self.assertLess(ids.index(second.id), ids.index(first.id))

    def test_server_sequence_does_not_order_bindings(self):
        model_id = self.env["ir.model"]._get_id("res.currency")
        Actions = self.env["ir.actions.actions"]
        common = {
            "model_id": model_id,
            "state": "code",
            "code": "pass",
            "binding_model_id": model_id,
        }
        first = self.env["ir.actions.server"].create(
            {**common, "name": "audit-server-seq-high", "sequence": 90}
        )
        second = self.env["ir.actions.server"].create(
            {**common, "name": "audit-server-seq-low", "sequence": 1}
        )
        self.env.registry.clear_cache()
        ids = [vals["id"] for vals in Actions._get_bindings("res.currency")["action"]]
        self.assertLess(ids.index(first.id), ids.index(second.id))

    def test_binding_icon_is_served_with_the_binding(self):
        model_id = self.env["ir.model"]._get_id("res.currency")
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-icon",
                "res_model": "res.currency",
                "binding_model_id": model_id,
                "binding_icon": "fa-solid fa-envelope",
            }
        )
        self.env.registry.clear_cache()
        bound = {
            vals["id"]: vals
            for vals in self.env["ir.actions.actions"]._get_bindings("res.currency")[
                "action"
            ]
        }
        self.assertEqual(bound[action.id]["binding_icon"], "fa-solid fa-envelope")

    def test_binding_view_types_are_stored_in_canonical_order(self):
        model_id = self.env["ir.model"]._get_id("res.currency")
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-view-types",
                "res_model": "res.currency",
                "binding_model_id": model_id,
                "binding_view_types": "form,list,kanban",
            }
        )
        self.assertEqual(action.binding_view_types, "list,kanban,form")
        action.write({"binding_view_types": "form, list,form"})
        self.assertEqual(action.binding_view_types, "list,form")


@tagged("post_install", "-at_install")
class TestIrActionsCacheOnEmptyWrite(TransactionCase):
    def test_empty_recordset_write_keeps_the_cache(self):
        Actions = self.env["ir.actions.actions"]
        self.env.registry.clear_cache()
        before = Actions._get_bindings("res.partner")
        self.env["ir.actions.act_window"].browse().write({"path": "audit-noop"})
        self.assertIs(Actions._get_bindings("res.partner"), before)

    def test_a_real_write_still_clears_the_cache(self):
        Actions = self.env["ir.actions.actions"]
        action = self.env["ir.actions.act_window"].create(
            {"name": "audit-noop-real", "res_model": "res.currency"}
        )
        self.env.registry.clear_cache("actions")
        before = Actions._get_bindings("res.partner")
        action.binding_model_id = self.env["ir.model"]._get("res.currency")
        self.assertIsNot(Actions._get_bindings("res.partner"), before)


@tagged("post_install", "-at_install")
class TestIrActionsBindingsCacheBucket(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Actions = self.env["ir.actions.actions"]
        self.Menu = self.env["ir.ui.menu"]
        self.action = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-bucket",
                "res_model": "res.partner",
                "binding_model_id": self.env["ir.model"]._get("res.partner").id,
            }
        )
        self.env.flush_all()
        self.env.registry.clear_cache("actions")
        self.env.registry.clear_cache()
        self.bindings = self.Actions._get_bindings("res.partner")
        self.menus = self.Menu.load_menus_root()

    def test_bindings_live_in_the_actions_bucket(self):
        self.env.registry.clear_cache()
        self.assertIs(self.Actions._get_bindings("res.partner"), self.bindings)
        self.env.registry.clear_cache("actions")
        self.assertIsNot(self.Actions._get_bindings("res.partner"), self.bindings)

    def test_binding_write_invalidates_bindings_only(self):
        self.action.write({"name": "audit-bucket-renamed"})
        self.assertIsNot(self.Actions._get_bindings("res.partner"), self.bindings)
        self.assertIs(self.Menu.load_menus_root(), self.menus)

    def test_binding_unlink_invalidates_bindings_only(self):
        self.action.unlink()
        self.assertIsNot(self.Actions._get_bindings("res.partner"), self.bindings)
        self.assertIs(self.Menu.load_menus_root(), self.menus)

    def test_bound_create_invalidates_bindings_only(self):
        self.env["ir.actions.act_window"].create(
            {
                "name": "audit-bucket-2",
                "res_model": "res.partner",
                "binding_model_id": self.env["ir.model"]._get("res.partner").id,
            }
        )
        self.assertIsNot(self.Actions._get_bindings("res.partner"), self.bindings)
        self.assertIs(self.Menu.load_menus_root(), self.menus)

    def test_path_write_still_invalidates_menus(self):
        self.action.write({"path": "audit-bucket-path"})
        self.assertIsNot(self.Menu.load_menus_root(), self.menus)


@tagged("post_install", "-at_install")
class TestIrActionsMenuAclCacheInvalidation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create(
            {
                "name": "audit-menu-acl",
                "login": "audit_menu_acl",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

    def _menu_visible(self, menu):
        return menu.id in self.env["ir.ui.menu"].with_user(
            self.user
        )._get_visible_menu_ids(False)

    def test_res_model_write_on_an_unbound_action_clears_the_cache(self):
        action = self.env["ir.actions.act_window"].create(
            {"name": "audit-menu-acl-act", "res_model": "res.currency"}
        )
        menu = self.env["ir.ui.menu"].create(
            {
                "name": "audit-menu-acl-menu",
                "action": f"ir.actions.act_window,{action.id}",
            }
        )
        self.env.flush_all()
        self.env.registry.clear_cache()

        self.assertFalse(action._get_cache_groups_holding())
        self.assertTrue(self._menu_visible(menu))

        action.write({"res_model": "ir.config_parameter"})
        self.env.flush_all()
        self.assertFalse(self._menu_visible(menu))

    def test_every_subtype_declares_its_destination_model_field(self):
        Actions = self.env["ir.actions.actions"]
        declared = {}
        for model_name in Actions._get_model_names_in_tree():
            field_name = self.env[model_name]._get_field_target_model()
            if field_name:
                declared[model_name] = field_name
                with self.subTest(model=model_name):
                    self.assertIn(
                        field_name,
                        self.env[model_name]._get_fields_read_by_menus(),
                    )
        self.assertEqual(
            declared,
            {
                "ir.actions.act_window": "res_model",
                "ir.actions.client": "res_model",
                "ir.actions.report": "model",
                "ir.actions.server": "model_name",
            },
        )

    def test_the_declared_field_is_a_real_field_of_that_subtype(self):
        Actions = self.env["ir.actions.actions"]
        for model_name in Actions._get_model_names_in_tree():
            model = self.env[model_name]
            field_name = model._get_field_target_model()
            if field_name:
                with self.subTest(model=model_name):
                    self.assertIn(field_name, model._fields)

    def test_a_client_action_gates_on_res_model_like_the_others(self):
        self.assertEqual(
            self.env["ir.actions.client"]._get_field_target_model(), "res_model"
        )
        self.assertIn(
            "res_model", self.env["ir.actions.client"]._get_fields_read_by_menus()
        )

    def test_an_uncached_field_still_skips_the_clear(self):
        Actions = self.env["ir.actions.actions"]
        action = self.env["ir.actions.act_window"].create(
            {"name": "audit-menu-acl-keep", "res_model": "res.currency"}
        )
        self.env.registry.clear_cache()
        before = Actions._get_bindings("res.partner")
        action.write({"help": "<p>nothing cached reads this</p>"})
        self.assertIs(Actions._get_bindings("res.partner"), before)


@tagged("post_install", "-at_install")
class TestIrActionsTypeMatchesItsModel(TransactionCase):
    def test_a_type_naming_another_subtype_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["ir.actions.act_window"].create(
                {
                    "name": "audit-type-mismatch",
                    "res_model": "res.partner",
                    "type": "ir.actions.client",
                }
            )
            self.env.flush_all()

    def test_the_default_type_is_the_model_name_for_every_subtype(self):
        Actions = self.env["ir.actions.actions"]
        for name in self.assertSweep(Actions._get_model_names_in_tree()):
            if name == "ir.actions.actions":
                continue
            with self.subTest(model=name):
                model = self.env[name]
                self.assertEqual(model.default_get(["type"])["type"], name)

    def test_every_stored_action_agrees_with_its_table(self):
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT a.id, a.type, c.relname FROM ir_actions a"
            " JOIN pg_class c ON c.oid = a.tableoid"
        )
        mismatched = [
            (action_id, action_type, table)
            for action_id, action_type, table in self.env.cr.fetchall()
            if self.env[action_type]._table != table
        ]
        self.assertEqual(mismatched, [])


@tagged("post_install", "-at_install")
class TestIrActionsUnlinkFollowsTheStorage(TransactionCase):
    def test_a_row_whose_type_lies_is_still_deleted(self):
        action = self.env["ir.actions.act_window"].create(
            {"name": "audit-legacy-type", "res_model": "res.partner"}
        )
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "audit_legacy_type_xmlid",
                "model": "ir.actions.act_window",
                "res_id": action.id,
            }
        )
        self.env.flush_all()
        # a database upgraded with such rows keeps them: the constraint that
        # forbids them is only added once none is left
        self.env.cr.execute(
            "ALTER TABLE ir_act_window DROP CONSTRAINT ir_act_window_type_names_model"
        )
        self.env.cr.execute(
            "UPDATE ir_actions SET type = 'ir.actions.client' WHERE id = %s",
            [action.id],
        )
        self.env.invalidate_all()

        self.env["ir.actions.actions"].browse(action.id).unlink()

        self.env.cr.execute("SELECT id FROM ir_actions WHERE id = %s", [action.id])
        self.assertEqual(self.env.cr.fetchall(), [])
        self.assertFalse(
            self.env["ir.model.data"].search(
                [("module", "=", "base"), ("name", "=", "audit_legacy_type_xmlid")]
            ),
            "the dispatch went to the root, so the subtype's xml id survived",
        )

    def test_each_subtype_table_maps_back_to_its_model(self):
        Actions = self.env["ir.actions.actions"]
        by_table = Actions._get_model_names_by_table()
        for name in self.assertSweep(Actions._get_model_names_in_tree()):
            with self.subTest(model=name):
                self.assertIn(name, by_table[self.env[name]._table])

    def test_every_table_of_the_tree_names_exactly_one_model(self):
        Actions = self.env["ir.actions.actions"]
        by_table = Actions._get_model_names_by_table()
        self.assertEqual(
            {table: len(names) for table, names in by_table.items()},
            dict.fromkeys(by_table, 1),
        )
        self.assertEqual(by_table[Actions._table], ("ir.actions.actions",))

    def test_an_already_deleted_id_unlinks_like_any_other_model(self):
        action = self.env["ir.actions.act_url"].create(
            {"name": "audit-gone", "url": "/audit/gone"}
        )
        self.env.flush_all()
        action_id = action.id
        action.unlink()
        self.assertTrue(self.env["ir.actions.actions"].browse(action_id).unlink())


@tagged("post_install", "-at_install")
class TestIrActionsReferenceSweep(TransactionCase):
    def test_a_menu_reference_is_cleared_when_its_action_dies(self):
        action = self.env["ir.actions.act_window"].create(
            {"name": "audit-ref-sweep", "res_model": "res.partner"}
        )
        menu = self.env["ir.ui.menu"].create(
            {
                "name": "audit-ref-sweep-menu",
                "action": f"ir.actions.act_window,{action.id}",
            }
        )
        self.env.flush_all()

        action.unlink()
        self.env.invalidate_all()

        self.env.cr.execute("SELECT action FROM ir_ui_menu WHERE id = %s", [menu.id])
        self.assertEqual(self.env.cr.fetchall(), [(None,)])
        self.assertFalse(menu.action)

    def test_a_reference_to_another_action_is_left_alone(self):
        kept = self.env["ir.actions.act_window"].create(
            {"name": "audit-ref-keep", "res_model": "res.partner"}
        )
        doomed = self.env["ir.actions.act_window"].create(
            {"name": "audit-ref-doomed", "res_model": "res.partner"}
        )
        menu = self.env["ir.ui.menu"].create(
            {
                "name": "audit-ref-keep-menu",
                "action": f"ir.actions.act_window,{kept.id}",
            }
        )
        self.env.flush_all()

        doomed.unlink()
        self.env.invalidate_all()

        self.assertEqual(menu.action, kept)

    def test_the_sweep_covers_every_reference_that_can_name_an_action(self):
        Actions = self.env["ir.actions.actions"]
        tree = Actions._get_model_names_in_tree()
        expected = {
            (model_name, field.name)
            for model_name, model in self.env.registry.items()
            if not model._abstract
            for field in model._fields.values()
            if field.type == "reference"
            and field.store
            and (
                not isinstance(field.selection, list)
                or any(value in tree for value, __ in field.selection)
            )
        }
        self.assertEqual(set(Actions._get_selections_ondelete_unenforced()), expected)
        self.assertIn(("ir.ui.menu", "action"), expected)

    def test_a_reference_that_can_never_name_an_action_is_not_swept(self):
        swept = {
            model
            for model, __ in self.env[
                "ir.actions.actions"
            ]._get_selections_ondelete_unenforced()
        }
        for model_name, model in self.env.registry.items():
            for field in model._fields.values():
                if (
                    field.type == "reference"
                    and isinstance(field.selection, list)
                    and not any(
                        value.startswith("ir.actions.") for value, __ in field.selection
                    )
                ):
                    with self.subTest(model=model_name, field=field.name):
                        self.assertNotIn(model_name, swept)


@tagged("post_install", "-at_install")
class TestIrActionsViewTypeVocabulary(TransactionCase):
    def test_the_comma_separated_fields_and_the_lines_share_one_vocabulary(self):
        allowed = self.env["ir.actions.actions"]._get_view_types_for_window()
        line_modes = set(
            self.env["ir.actions.act_window.view"]
            ._fields["view_mode"]
            .get_values(self.env)
        )
        self.assertEqual(allowed, line_modes)

    def test_that_vocabulary_is_still_the_view_types_minus_the_unrenderable(self):
        from odoo.addons.base.models.ir_actions_act_window_view import (
            NON_WINDOW_VIEW_TYPES,
        )

        allowed = self.env["ir.actions.actions"]._get_view_types_for_window()
        view_types = set(self.env["ir.ui.view"]._fields["type"].get_values(self.env))
        self.assertEqual(allowed, view_types - set(NON_WINDOW_VIEW_TYPES))
        self.assertNotIn("search", allowed)
        self.assertIn("list", allowed)

    def test_a_view_type_from_an_earlier_version_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["ir.actions.act_window"].create(
                {
                    "name": "audit-view-mode-tree",
                    "res_model": "res.partner",
                    "view_mode": "tree,form",
                }
            )
            self.env.flush_all()

    def test_a_search_view_is_not_a_view_mode(self):
        with self.assertRaises(ValidationError):
            self.env["ir.actions.act_window"].create(
                {
                    "name": "audit-view-mode-search",
                    "res_model": "res.partner",
                    "view_mode": "list,search",
                }
            )
            self.env.flush_all()

    def test_the_mobile_and_binding_spellings_are_checked_too(self):
        for field_name in ("mobile_view_mode", "binding_view_types"):
            with self.subTest(field=field_name):
                with self.assertRaises(ValidationError):
                    self.env["ir.actions.act_window"].create(
                        {
                            "name": f"audit-{field_name}",
                            "res_model": "res.partner",
                            field_name: "nonesuch",
                        }
                    )
                    self.env.flush_all()
                self.env.invalidate_all()

    def test_every_shipped_action_uses_a_renderable_view_type(self):
        allowed = self.env["ir.actions.actions"]._get_view_types_for_window()
        offenders = []
        for action in self.env["ir.actions.act_window"].search([]):
            for field_name in ("view_mode", "mobile_view_mode"):
                unknown = [
                    mode
                    for mode in (action[field_name] or "").split(",")
                    if mode and mode not in allowed
                ]
                if unknown:
                    offenders.append((action.xml_id or action.id, field_name, unknown))
        self.assertEqual(offenders, [])


@tagged("post_install", "-at_install")
class TestIrActionsContextDegradesQuietly(TransactionCase):
    def test_an_active_id_context_is_the_normal_case_not_a_warning(self):
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-ctx-active-id",
                "res_model": "res.partner",
                "context": "{'default_parent_id': active_id}",
            }
        )
        with self.assertNoLogs(_ACTIONS_LOGGER):
            values = action.read(["help", "context"])
        self.assertEqual(values[0]["context"], "{'default_parent_id': active_id}")

    def test_a_shipped_database_would_drown_such_a_log(self):
        failing = 0
        for action in self.env["ir.actions.act_window"].search([]):
            try:
                safe_eval(action.context or "{}", dict(self.env.context))
            except Exception:
                failing += 1
        self.assertGreater(
            failing,
            0,
            "if no shipped action has a context needing an active id any more, "
            "logging the degradation becomes affordable again",
        )


@tagged("post_install", "-at_install")
class TestMenuActionReferenceIsJunkTolerant(TransactionCase):
    def test_a_reference_to_a_non_action_model_does_not_break_the_menu(self):
        menu = self.env["ir.ui.menu"].create({"name": "audit-junk-ref"})
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE ir_ui_menu SET action = %s WHERE id = %s",
            [f"res.partner,{self.env.user.partner_id.id}", menu.id],
        )
        self.env.invalidate_all()
        self.env.registry.clear_cache()

        visible = self.env["ir.ui.menu"]._get_visible_menu_ids(False)
        self.assertIsInstance(visible, frozenset)

    def test_the_gating_map_does_not_depend_on_what_menus_point_at(self):
        Actions = self.env["ir.actions.actions"]
        gating = {
            name: self.env[name]._get_field_target_model()
            for name in Actions._get_model_names_in_tree()
        }
        self.assertEqual(
            {name: field for name, field in gating.items() if field},
            {
                "ir.actions.act_window": "res_model",
                "ir.actions.client": "res_model",
                "ir.actions.report": "model",
                "ir.actions.server": "model_name",
            },
        )


@tagged("post_install", "-at_install")
class TestIrActionsPathReservation(TransactionCase):
    def test_the_reservation_table_holds_the_only_tree_wide_index(self):
        self.env.cr.execute(
            """
            SELECT c.relname FROM pg_index x
              JOIN pg_class c ON c.oid = x.indrelid
              JOIN pg_class i ON i.oid = x.indexrelid
             WHERE x.indisunique AND pg_get_indexdef(i.oid) LIKE '%(path)'
            """
        )
        tables = {row[0] for row in self.env.cr.fetchall()}
        self.assertIn(self.env["ir.actions.path"]._table, tables)

    def test_every_pathed_action_holds_a_reservation(self):
        self.env.flush_all()
        self.env.cr.execute(
            """
            SELECT a.id, a.path FROM ir_actions a
             LEFT JOIN ir_actions_path p ON p.action_id = a.id
             WHERE a.path IS NOT NULL AND p.id IS NULL
            """
        )
        self.assertEqual(self.env.cr.fetchall(), [])

    def test_no_reservation_outlives_its_action(self):
        self.env.flush_all()
        self.env.cr.execute(
            """
            SELECT p.id FROM ir_actions_path p
             LEFT JOIN ir_actions a ON a.id = p.action_id
             WHERE a.id IS NULL OR a.path IS DISTINCT FROM p.path
            """
        )
        self.assertEqual(self.env.cr.fetchall(), [])

    def test_two_subtypes_cannot_share_a_path(self):
        self.env["ir.actions.act_window"].create(
            {"name": "audit-res-a", "res_model": "res.partner", "path": "audit-res-x"}
        )
        with self.assertRaises(IntegrityError), mute_logger("odoo.db.cursor"):
            with self.env.cr.savepoint():
                self.env["ir.actions.act_url"].create(
                    {"name": "audit-res-b", "url": "/a", "path": "audit-res-x"}
                )
                self.env.flush_all()

    def test_the_reservation_follows_the_path(self):
        Reservation = self.env["ir.actions.path"]
        action = self.env["ir.actions.act_window"].create(
            {"name": "audit-res-follow", "res_model": "res.partner", "path": "audit-f1"}
        )
        self.env.flush_all()
        self.assertEqual(
            Reservation.search([("action_id", "=", action.id)]).mapped("path"),
            ["audit-f1"],
        )

        action.write({"path": "audit-f2"})
        self.env.flush_all()
        self.assertEqual(
            Reservation.search([("action_id", "=", action.id)]).mapped("path"),
            ["audit-f2"],
        )

        action.write({"path": False})
        self.env.flush_all()
        self.assertFalse(Reservation.search([("action_id", "=", action.id)]))

    def test_deleting_an_action_frees_its_path(self):
        action = self.env["ir.actions.act_window"].create(
            {"name": "audit-res-free", "res_model": "res.partner", "path": "audit-free"}
        )
        self.env.flush_all()
        action.unlink()
        self.env.flush_all()
        self.assertFalse(
            self.env["ir.actions.path"].search([("path", "=", "audit-free")])
        )
        reused = self.env["ir.actions.act_url"].create(
            {"name": "audit-res-reuse", "url": "/reuse", "path": "audit-free"}
        )
        self.env.flush_all()
        self.assertEqual(reused.path, "audit-free")

    def test_the_reservation_is_swept_like_any_other_reference(self):
        swept = {
            (model, field)
            for model, field, __ in self.env[
                "ir.actions.actions"
            ]._get_fields_ondelete_unenforced()
        }
        self.assertIn(("ir.actions.path", "action_id"), swept)


@tagged("post_install", "-at_install")
class TestIrActionsBindingAccessGate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create(
            {
                "name": "audit-gate",
                "login": "audit_gate",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.secret = cls.env["ir.model"]._get("ir.cron")
        cls.bound = cls.env["ir.model"]._get("res.partner")
        cls.env["ir.model.access"].search([("model_id", "=", cls.secret.id)]).unlink()

    def _visible_names(self):
        self.env.flush_all()
        self.env.registry.clear_cache()
        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.user)
            .get_bindings("res.partner")
        )
        return {action["name"] for bucket in bindings.values() for action in bucket}

    def test_a_server_binding_on_an_unreadable_model_is_hidden(self):
        action = self.env["ir.actions.server"].create(
            {
                "name": "audit-gate-server",
                "model_id": self.secret.id,
                "state": "code",
                "code": "pass",
                "binding_model_id": self.bound.id,
            }
        )
        self.assertNotIn(action.name, self._visible_names())

    def test_a_report_binding_on_an_unreadable_model_is_hidden(self):
        action = self.env["ir.actions.report"].create(
            {
                "name": "audit-gate-report",
                "model": "ir.cron",
                "report_name": "audit.gate.report",
                "binding_type": "report",
                "binding_model_id": self.bound.id,
            }
        )
        self.assertNotIn(action.name, self._visible_names())

    def test_a_binding_on_a_readable_model_is_still_shown(self):
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-gate-ok",
                "res_model": "res.partner",
                "binding_model_id": self.bound.id,
            }
        )
        self.assertIn(action.name, self._visible_names())

    def test_the_gating_model_never_reaches_the_browser(self):
        self.env["ir.actions.act_window"].create(
            {
                "name": "audit-gate-keys",
                "res_model": "res.partner",
                "binding_model_id": self.bound.id,
            }
        )
        self.env.flush_all()
        self.env.registry.clear_cache()
        bindings = self.env["ir.actions.actions"].get_bindings("res.partner")
        keys = {k for bucket in bindings.values() for action in bucket for k in action}
        for leaked in ("res_model", "model", "model_name"):
            self.assertNotIn(leaked, keys)
        self.assertFalse({k for k in keys if k.startswith("__")})


@tagged("post_install", "-at_install")
class TestIrActionsAsConcrete(TransactionCase):
    def test_each_subtype_round_trips_through_the_root(self):
        Actions = self.env["ir.actions.actions"]
        made = [
            self.env["ir.actions.act_window"].create(
                {"name": "audit-conc-w", "res_model": "res.partner"}
            ),
            self.env["ir.actions.act_url"].create(
                {"name": "audit-conc-u", "url": "/audit/conc"}
            ),
            self.env["ir.actions.client"].create(
                {"name": "audit-conc-c", "tag": "audit"}
            ),
        ]
        self.env.flush_all()
        for action in made:
            with self.subTest(model=action._name):
                concrete = Actions.browse(action.id)._get_concrete()
                self.assertEqual(concrete._name, action._name)
                self.assertEqual(concrete.id, action.id)

    def test_it_follows_the_storage_not_the_type_column(self):
        action = self.env["ir.actions.act_window"].create(
            {"name": "audit-conc-lie", "res_model": "res.partner"}
        )
        self.env.flush_all()
        # a database upgraded with such rows keeps them: the constraint that
        # forbids them is only added once none is left
        self.env.cr.execute(
            "ALTER TABLE ir_act_window DROP CONSTRAINT ir_act_window_type_names_model"
        )
        self.env.cr.execute(
            "UPDATE ir_actions SET type = 'ir.actions.client' WHERE id = %s",
            [action.id],
        )
        self.env.invalidate_all()
        concrete = self.env["ir.actions.actions"].browse(action.id)._get_concrete()
        self.assertEqual(concrete._name, "ir.actions.act_window")


@tagged("post_install", "-at_install")
class TestIrActionsTodoSurvivor(TransactionCase):
    def test_the_survivor_is_the_one_the_queue_picks(self):
        action = self.env["ir.actions.act_window"].create(
            {"name": "audit-todo-act", "res_model": "res.partner"}
        )
        self.env["ir.actions.todo"].search([("state", "=", "open")]).write(
            {"state": "done"}
        )
        todos = self.env["ir.actions.todo"].create(
            [
                {"action_id": action.id, "state": "open", "sequence": 30},
                {"action_id": action.id, "state": "open", "sequence": 10},
                {"action_id": action.id, "state": "open", "sequence": 20},
            ]
        )
        self.env.flush_all()

        still_open = todos.filtered(lambda todo: todo.state == "open")
        self.assertEqual(len(still_open), 1)
        self.assertEqual(still_open.sequence, 10)
        self.assertEqual(
            self.env["ir.actions.todo"].search([("state", "=", "open")], limit=1),
            still_open,
        )


@tagged("post_install", "-at_install")
class TestIrActionsBindingModelIsChecked(TransactionCase):
    def test_every_subtype_rejects_a_binding_to_a_missing_model(self):
        stale = self.env["ir.model"].create(
            {"name": "audit-stale", "model": "x_audit.stale.model"}
        )
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE ir_model SET model = %s WHERE id = %s",
            ["x_audit.not.in.registry", stale.id],
        )
        self.env.invalidate_all()

        for model_name, vals in (
            ("ir.actions.act_url", {"name": "audit-bm-u", "url": "/audit/bm"}),
            ("ir.actions.client", {"name": "audit-bm-c", "tag": "audit"}),
        ):
            with self.subTest(model=model_name):
                with self.assertRaises(ValidationError):
                    self.env[model_name].create({**vals, "binding_model_id": stale.id})
                    self.env.flush_all()
                self.env.invalidate_all()


@tagged("post_install", "-at_install")
class TestActionCreateDoesNotEditItsArgument(TransactionCase):
    def _unchanged(self, model_name, vals, extra=None):
        snapshot = dict(vals)
        self.env[model_name].create([{**vals, **(extra or {})}] if extra else [vals])
        self.assertEqual(vals, snapshot, f"{model_name}.create edited its argument")

    def test_embedded_action_create_keeps_the_caller_vals(self):
        parent = self.env["ir.actions.act_window"].create(
            {"name": "audit-arg-parent", "res_model": "res.partner"}
        )
        target = self.env["ir.actions.act_window"].create(
            {"name": "audit-arg-target", "res_model": "res.partner"}
        )
        self._unchanged(
            "ir.embedded.actions",
            {
                "parent_action_id": parent.id,
                "parent_res_model": "res.partner",
                "action_id": target.id,
            },
        )

    def test_embedded_action_create_keeps_the_coerced_pair(self):
        parent = self.env["ir.actions.act_window"].create(
            {"name": "audit-arg-parent2", "res_model": "res.partner"}
        )
        target = self.env["ir.actions.act_window"].create(
            {"name": "audit-arg-target2", "res_model": "res.partner"}
        )
        self._unchanged(
            "ir.embedded.actions",
            {
                "name": "audit-arg-xor",
                "parent_action_id": parent.id,
                "parent_res_model": "res.partner",
                "action_id": target.id,
                "python_method": "",
            },
        )

    def test_the_same_dict_twice_yields_the_same_record_twice(self):
        parent = self.env["ir.actions.act_window"].create(
            {"name": "audit-arg-parent3", "res_model": "res.partner"}
        )
        target = self.env["ir.actions.act_window"].create(
            {"name": "audit-arg-target3", "res_model": "res.partner"}
        )
        vals = {
            "parent_action_id": parent.id,
            "parent_res_model": "res.partner",
            "action_id": target.id,
        }
        first = self.env["ir.embedded.actions"].create([vals])
        second = self.env["ir.embedded.actions"].create([vals])
        self.assertEqual(first.name, second.name)
        self.assertEqual(first.action_id, second.action_id)

    def test_server_action_create_keeps_the_caller_vals(self):
        parent = self.env["ir.actions.server"].create(
            {
                "name": "audit-arg-server-parent",
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "state": "code",
                "code": "pass",
            }
        )
        self._unchanged(
            "ir.actions.server",
            {
                "name": "audit-arg-server-child",
                "model_id": self.env["ir.model"]._get_id("res.currency"),
                "state": "code",
                "code": "pass",
                "parent_id": parent.id,
            },
        )

    def test_menu_create_keeps_the_caller_vals(self):
        self._unchanged("ir.ui.menu", {"name": "audit-arg-menu", "web_icon": False})

    def test_menu_write_keeps_the_caller_vals(self):
        menu = self.env["ir.ui.menu"].create({"name": "audit-arg-menu-w"})
        vals = {"name": "audit-arg-menu-w2", "web_icon": "base,static/img/nope.png"}
        snapshot = dict(vals)
        menu.write(vals)
        self.assertEqual(vals, snapshot, "ir.ui.menu.write edited its argument")


@tagged("post_install", "-at_install")
class TestIrActionsPathIsNotCopied(TransactionCase):
    def test_duplicating_a_pathed_action_leaves_the_path_behind(self):
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-copy-path",
                "res_model": "res.partner",
                "path": "audit-copy-path",
            }
        )
        self.env.flush_all()
        copy = action.copy()
        self.env.flush_all()
        self.assertFalse(copy.path)
        self.assertEqual(action.path, "audit-copy-path")

    def test_the_copy_holds_no_reservation(self):
        action = self.env["ir.actions.act_url"].create(
            {"name": "audit-copy-res", "url": "/a", "path": "audit-copy-res"}
        )
        self.env.flush_all()
        copy = action.copy()
        self.env.flush_all()
        Reservation = self.env["ir.actions.path"]
        self.assertFalse(Reservation.search([("action_id", "=", copy.id)]))
        self.assertEqual(
            Reservation.search([("action_id", "=", action.id)]).mapped("path"),
            ["audit-copy-res"],
        )


@tagged("post_install", "-at_install")
class TestIrActionsPathFromADefault(TransactionCase):
    def test_a_path_arriving_as_a_default_still_reserves(self):
        action = (
            self.env["ir.actions.act_window"]
            .with_context(default_path="audit-default-path")
            .create({"name": "audit-default-path", "res_model": "res.partner"})
        )
        self.env.flush_all()
        self.assertEqual(action.path, "audit-default-path")
        self.assertEqual(
            self.env["ir.actions.path"]
            .search([("action_id", "=", action.id)])
            .mapped("path"),
            ["audit-default-path"],
        )

    def test_a_defaulted_path_is_not_stealable_by_another_subtype(self):
        self.env["ir.actions.act_window"].with_context(
            default_path="audit-default-steal"
        ).create({"name": "audit-default-steal", "res_model": "res.partner"})
        self.env.flush_all()
        with self.assertRaises(IntegrityError), mute_logger("odoo.db.cursor"):
            with self.env.cr.savepoint():
                self.env["ir.actions.act_url"].create(
                    {
                        "name": "audit-default-steal-2",
                        "url": "/a",
                        "path": "audit-default-steal",
                    }
                )
                self.env.flush_all()


@tagged("post_install", "-at_install")
class TestIrActionsStoredContextIsData(TransactionCase):
    def test_a_context_with_non_string_keys_does_not_break_the_loader(self):
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-ctx-int-key",
                "res_model": "res.partner",
                "context": "{1: 2}",
            }
        )
        with mute_logger(_ACTIONS_LOGGER):
            values = action._get_action_dict()
        self.assertEqual(values["context"], "{1: 2}")

    def test_a_malformed_expression_is_logged(self):
        with self.assertLogs(_ACTIONS_LOGGER, "WARNING"):
            self.assertEqual(_eval_dict_or_default("{'a':", {}, {}), {})

    def test_an_expression_that_is_not_a_dict_is_logged(self):
        with self.assertLogs(_ACTIONS_LOGGER, "WARNING"):
            self.assertEqual(_eval_dict_or_default("[1, 2]", {}, {}), {})

    def test_a_missing_runtime_name_stays_quiet(self):
        with self.assertNoLogs(_ACTIONS_LOGGER):
            self.assertEqual(
                _eval_dict_or_default("{'default_x': active_id}", {}, {}),
                {"default_x": False},
            )


@tagged("post_install", "-at_install")
class TestIrActionsServerReadableFields(TransactionCase):
    def test_the_server_subtype_adds_its_own_readable_fields(self):
        readable = self.env["ir.actions.server"]._get_fields_readable()
        self.assertLessEqual({"group_ids", "model_name"}, readable)

    def test_no_model_anywhere_spells_an_abolished_name(self):
        for model_name, model in self.env.registry.items():
            for abolished in _ABOLISHED_ACTION_METHODS:
                self.assertFalse(
                    hasattr(model, abolished),
                    f"{model_name} still declares the pre-rename {abolished}",
                )


@tagged("post_install", "-at_install")
class TestIrActionsBindingQueryMatchesItsInvalidation(TransactionCase):
    def test_every_column_the_query_reads_invalidates_the_cache(self):
        Actions = self.env["ir.actions.actions"]
        columns = {*Actions._BINDING_TYPE_FIELDS, Actions._BINDING_MODEL_FIELD}
        self.assertLessEqual(columns, Actions._get_fields_read_by_bindings())

    def test_those_columns_are_real_stored_fields_of_the_root(self):
        Actions = self.env["ir.actions.actions"]
        for name in (*Actions._BINDING_TYPE_FIELDS, Actions._BINDING_MODEL_FIELD):
            self.assertTrue(Actions._fields[name].store, name)


@tagged("post_install", "-at_install")
class TestIrActionsMixedUnlinkIsAtomic(TransactionCase):
    def _blocked_action(self):
        blocked = self.env["ir.actions.act_url"].create(
            {"name": "audit-mixed-blocked", "url": "/audit/mixed"}
        )
        parent = self.env["ir.actions.act_window"].create(
            {"name": "audit-mixed-parent", "res_model": "res.partner"}
        )
        embedded = self.env["ir.embedded.actions"].create(
            {
                "parent_action_id": parent.id,
                "parent_res_model": "res.partner",
                "action_id": blocked.id,
            }
        )
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "audit_mixed_seeded_embedded",
                "model": "ir.embedded.actions",
                "res_id": embedded.id,
            }
        )
        return blocked

    def test_a_blocked_subtype_rolls_back_the_ones_already_deleted(self):
        free = self.env["ir.actions.act_window"].create(
            {"name": "audit-mixed-free", "res_model": "res.partner"}
        )
        blocked = self._blocked_action()
        self.env.flush_all()
        root = self.env["ir.actions.actions"].browse([free.id, blocked.id])
        self.assertEqual(
            list(root._get_model_names_concrete().values()),
            ["ir.actions.act_window", "ir.actions.act_url"],
            "the free action must be deleted before the blocked one for this to bite",
        )

        raises_without_rolling_back(self, UserError, root.unlink)

        self.env.invalidate_all()
        self.assertTrue(
            free.exists(),
            "an action deleted earlier in the split must be restored when a later "
            "subtype refuses, exactly as within one subtype",
        )
        self.assertTrue(blocked.exists())

    def test_a_mixed_unlink_that_succeeds_still_deletes_everything(self):
        window = self.env["ir.actions.act_window"].create(
            {"name": "audit-mixed-ok-w", "res_model": "res.partner"}
        )
        url = self.env["ir.actions.act_url"].create(
            {"name": "audit-mixed-ok-u", "url": "/audit/mixed-ok"}
        )
        self.env.flush_all()
        self.env["ir.actions.actions"].browse([window.id, url.id]).unlink()
        self.env.invalidate_all()
        self.assertFalse(window.exists())
        self.assertFalse(url.exists())


@tagged("post_install", "-at_install")
class TestIrActionsPathHasOneResolver(TransactionCase):
    def test_the_resolver_returns_the_concrete_subtype(self):
        action = self.env["ir.actions.act_url"].create(
            {"name": "audit-resolve", "url": "/a", "path": "audit-resolve"}
        )
        self.env.flush_all()
        found = self.env["ir.actions.actions"]._get_action_by_path("audit-resolve")
        self.assertEqual(found, action)
        self.assertEqual(found._name, "ir.actions.act_url")

    def test_an_unknown_path_resolves_to_nothing(self):
        found = self.env["ir.actions.actions"]._get_action_by_path("audit-no-such")
        self.assertFalse(found)

    def test_every_caller_agrees_with_the_resolver(self):
        from odoo.addons.web.controllers.utils import get_action

        action = self.env["ir.actions.act_window"].create(
            {
                "name": "audit-resolve-w",
                "res_model": "res.partner",
                "path": "audit-resolve-w",
            }
        )
        self.env.flush_all()
        Actions = self.env["ir.actions.actions"]
        self.assertEqual(Actions._get_action_by_path("audit-resolve-w"), action)
        self.assertEqual(get_action(self.env, "audit-resolve-w"), action)

    def test_no_caller_scans_the_inheritance_tree_for_a_path(self):
        import pathlib
        import re

        root = pathlib.Path(__file__).parents[4]
        offenders = []
        pattern = re.compile(r"""\(\s*['"]path['"]\s*,\s*['"]=['"]""")
        for path in (root / "addons").rglob("controllers/*.py"):
            text = path.read_text()
            for match in pattern.finditer(text):
                line = text[: match.start()].count("\n") + 1
                window = text[max(0, match.start() - 300) : match.start()]
                if "ir.actions.path" in window or "Reservation" in window:
                    continue
                offenders.append(f"{path.relative_to(root)}:{line}")
        self.assertFalse(
            offenders,
            "a path must be resolved through ir.actions.path (see "
            "ir.actions.actions._get_action_by_path), not by searching the "
            "inheritance tree: " + ", ".join(offenders),
        )


@tagged("post_install", "-at_install")
class TestIrActionsPathReservationIsTotal(TransactionCase):
    def test_the_reservation_table_holds_the_only_path_index(self):
        self.env.cr.execute(
            """
            SELECT c.relname FROM pg_index x
              JOIN pg_class c ON c.oid = x.indrelid
              JOIN pg_class i ON i.oid = x.indexrelid
             WHERE x.indisunique AND pg_get_indexdef(i.oid) LIKE '%(path)'
            """
        )
        tables = {row[0] for row in self.env.cr.fetchall()}
        self.assertEqual(tables, {self.env["ir.actions.path"]._table})

    def test_two_actions_of_one_subtype_still_cannot_share_a_path(self):
        self.env["ir.actions.act_window"].create(
            {"name": "audit-same-a", "res_model": "res.partner", "path": "audit-same"}
        )
        with self.assertRaises(IntegrityError), mute_logger("odoo.db.cursor"):
            with self.env.cr.savepoint():
                self.env["ir.actions.act_window"].create(
                    {
                        "name": "audit-same-b",
                        "res_model": "res.partner",
                        "path": "audit-same",
                    }
                )
                self.env.flush_all()

    def test_one_create_call_cannot_smuggle_a_duplicate_through(self):
        with self.assertRaises(IntegrityError), mute_logger("odoo.db.cursor"):
            with self.env.cr.savepoint():
                self.env["ir.actions.act_window"].create(
                    [
                        {
                            "name": "audit-batch-a",
                            "res_model": "res.partner",
                            "path": "audit-batch",
                        },
                        {
                            "name": "audit-batch-b",
                            "res_model": "res.partner",
                            "path": "audit-batch",
                        },
                    ]
                )
                self.env.flush_all()


@tagged("post_install", "-at_install")
class TestEmbeddedActionsCreateValidation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_action = cls.env["ir.actions.act_window"].create(
            {"name": "audit-embedded-parent", "res_model": "res.partner"}
        )

    def test_neither_an_action_nor_a_method_is_a_validation_error(self):
        for vals in (
            {},
            {"python_method": False, "action_id": False},
        ):
            with self.subTest(vals=vals), self.assertRaises(ValidationError):
                self.env["ir.embedded.actions"].create(
                    {
                        "name": "orphan",
                        "parent_action_id": self.parent_action.id,
                        "parent_res_model": "res.partner",
                        **vals,
                    }
                )

    def test_a_missing_parent_model_is_a_validation_error(self):
        with self.assertRaises(ValidationError):
            self.env["ir.embedded.actions"].create(
                {
                    "name": "no model",
                    "parent_action_id": self.parent_action.id,
                    "python_method": "action_archive",
                }
            )


@tagged("post_install", "-at_install")
class TestEmbeddedActionsLoadForPortal(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_action = cls.env["ir.actions.act_window"].create(
            {"name": "audit-embedded-parent", "res_model": "res.partner"}
        )
        cls.target_action = cls.env["ir.actions.act_window"].create(
            {"name": "audit-embedded-target", "res_model": "res.partner"}
        )
        cls.embedded = cls.env["ir.embedded.actions"].create(
            {
                "name": "E",
                "parent_action_id": cls.parent_action.id,
                "parent_res_model": "res.partner",
                "action_id": cls.target_action.id,
            }
        )
        cls.portal = cls.env["res.users"].create(
            {
                "name": "audit portal",
                "login": "audit_portal",
                "group_ids": [(6, 0, cls.env.ref("base.group_portal").ids)],
            }
        )

    def test_a_portal_user_loads_the_action_with_its_embedded_actions(self):
        with self.assertRaises(AccessError):
            self.embedded.with_user(self.portal).read(["name"])
        result = (
            self.parent_action.with_user(self.portal)
            .with_context(
                active_id=self.portal.partner_id.id, active_model="res.partner"
            )
            ._get_action_dict()
        )
        self.assertEqual([e["name"] for e in result["embedded_action_ids"]], ["E"])


@tagged("post_install", "-at_install")
class TestIrActionsTargetModelWriteInvalidatesBindings(TransactionCase):
    """A binding is shown only to a user who can read the model it opens, and
    the cache that answers get_bindings holds that model. Measured 2026-09-17:
    writing a report's ``model`` or a server action's ``model_id`` cleared the
    menu cache and left the bindings cache answering for the old model.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.user = cls.env["res.users"].create(
            {
                "name": "bindings-target",
                "login": "bindings_target",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        Access = cls.env["ir.model.access"].with_user(cls.user)
        assert Access.check("res.partner", "read", False)
        assert not Access.check("ir.config_parameter", "read", False)

    def _visible(self, bucket):
        self.env.flush_all()
        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.user)
            .get_bindings("res.partner")
        )
        return {action["name"] for action in bindings.get(bucket, ())}

    def test_a_report_moved_to_an_unreadable_model_leaves_the_menu(self):
        report = self.env["ir.actions.report"].create(
            {
                "name": "bindings-target-report",
                "model": "res.partner",
                "report_name": "bindings.target",
                "binding_model_id": self.partner_model.id,
            }
        )
        self.assertIn("bindings-target-report", self._visible("report"))
        report.write({"model": "ir.config_parameter"})
        self.assertNotIn("bindings-target-report", self._visible("report"))

    def test_a_server_action_moved_to_an_unreadable_model_leaves_the_menu(self):
        action = self.env["ir.actions.server"].create(
            {
                "name": "bindings-target-server",
                "model_id": self.partner_model.id,
                "state": "code",
                "code": "pass",
                "binding_model_id": self.partner_model.id,
            }
        )
        self.assertIn("bindings-target-server", self._visible("action"))
        action.write({"model_id": self.env["ir.model"]._get("ir.config_parameter").id})
        self.assertNotIn("bindings-target-server", self._visible("action"))

    def test_the_bindings_cache_reads_every_target_model_field(self):
        for model_name in (
            "ir.actions.report",
            "ir.actions.server",
            "ir.actions.act_window",
        ):
            with self.subTest(model=model_name):
                Model = self.env[model_name]
                self.assertLessEqual(
                    Model._get_fields_naming_target_model(),
                    Model._get_fields_read_by_bindings(),
                )


@tagged("post_install", "-at_install")
class TestIrActionsWriteThroughTheRoot(TransactionCase):
    """ir.actions.actions is a PostgreSQL inheritance root: a write through it
    lands in the subtype's table. Measured 2026-09-17: it bypassed the
    subtype's write override and left the subtype's cache stale.
    """

    def test_a_name_given_through_the_root_is_the_subtype_s_custom_name(self):
        action = self.env["ir.actions.server"].create(
            {
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "state": "code",
                "code": "pass",
            }
        )
        self.env.flush_all()
        self.assertFalse(action.name_is_custom)
        self.env["ir.actions.actions"].browse(action.id).write({"name": "Mine"})
        self.env.flush_all()
        self.assertTrue(action.name_is_custom)
        action.write({"state": "object_write", "update_path": "name"})
        self.env.flush_all()
        self.assertEqual(action.name, "Mine")

    def test_the_subtype_reads_what_the_root_wrote_and_back(self):
        window = self.env["ir.actions.act_window"].create(
            {"name": "root-write", "res_model": "res.partner", "binding_sequence": 10}
        )
        root = self.env["ir.actions.actions"].browse(window.id)
        self.assertEqual((window.binding_sequence, root.binding_sequence), (10, 10))
        root.write({"binding_sequence": 99})
        self.assertEqual(window.binding_sequence, 99)
        window.write({"binding_sequence": 7})
        self.assertEqual(root.binding_sequence, 7)

    def test_the_root_does_not_answer_for_a_row_the_subtype_deleted(self):
        window = self.env["ir.actions.act_window"].create(
            {"name": "root-unlink", "res_model": "res.partner"}
        )
        root = self.env["ir.actions.actions"].browse(window.id)
        self.assertEqual(root.name, "root-unlink")
        window.unlink()
        with self.assertRaises(MissingError):
            root.name

    def test_a_root_write_on_an_unsaved_record_is_not_lost(self):
        Actions = self.env["ir.actions.actions"]
        window = self.env["ir.actions.act_window"].create(
            {"name": "root-new", "res_model": "res.partner"}
        )
        unsaved = Actions.new({"name": "n", "type": "ir.actions.actions"})
        unsaved.write({"name": "n2"})
        self.assertEqual(unsaved.name, "n2")
        (Actions.browse(window.id) | unsaved).write({"help": "<p>h</p>"})
        self.assertEqual(str(window.help), "<p>h</p>")
        self.assertEqual(str(unsaved.help), "<p>h</p>")
        self.assertTrue(Actions.browse().write({"help": "x"}))

    def test_a_root_write_normalizes_binding_view_types_too(self):
        window = self.env["ir.actions.act_window"].create(
            {"name": "root-normalize", "res_model": "res.partner"}
        )
        self.env["ir.actions.actions"].browse(window.id).write(
            {"binding_view_types": "form, kanban"}
        )
        self.assertEqual(window.binding_view_types, "kanban,form")


@tagged("post_install", "-at_install")
class TestIrActionsExpressionNamesOnEverySubtype(TransactionCase):
    def test_a_context_expression_evaluates_on_any_subtype_recordset(self):
        for model_name in self.env["ir.actions.actions"]._get_model_names_in_tree():
            with self.subTest(model=model_name):
                self.assertEqual(
                    self.env[model_name]._eval_action_context("{'a': uid}"),
                    {"a": self.env.uid},
                )
                self.assertEqual(
                    self.env[model_name]._eval_action_domain("[('id', '=', uid)]"),
                    [("id", "=", self.env.uid)],
                )


@tagged("post_install", "-at_install")
class TestIrActionsBindingIsOneMethod(TransactionCase):
    def test_every_type_with_a_target_model_binds_to_it(self):
        partner_model = self.env["ir.model"]._get("res.partner")
        window = self.env["ir.actions.act_window"].create(
            {"name": "bind-window", "res_model": "res.partner"}
        )
        report = self.env["ir.actions.report"].create(
            {"name": "bind-report", "model": "res.partner", "report_name": "bind.r"}
        )
        server = self.env["ir.actions.server"].create(
            {"name": "bind-server", "model_id": partner_model.id, "state": "code"}
        )
        for action, binding_type in (
            (window, "action"),
            (report, "report"),
            (server, "action"),
        ):
            with self.subTest(model=action._name):
                self.assertFalse(action.binding_model_id)
                action.create_action()
                self.assertEqual(action.binding_model_id, partner_model)
                self.assertEqual(action.binding_type, binding_type)
                action.unlink_action()
                self.assertFalse(action.binding_model_id)

    def test_a_type_without_a_target_model_refuses(self):
        close = self.env["ir.actions.act_window_close"].create({"name": "bind-close"})
        with self.assertRaises(UserError):
            close.create_action()

    def test_an_action_without_a_target_model_value_refuses(self):
        client = self.env["ir.actions.client"].create(
            {"name": "bind-client", "tag": "x"}
        )
        self.assertFalse(client.res_model)
        with self.assertRaises(UserError):
            client.create_action()
        self.assertFalse(client.binding_model_id)
