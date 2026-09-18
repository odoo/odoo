import inspect
import socket
from unittest.mock import patch

import requests
from lxml import etree
from requests.adapters import HTTPAdapter

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.libs.netguard import DestinationRefused
from odoo.tests.common import TransactionCase, tagged
from odoo.tests.transaction_case import _super_send
from odoo.tools import mute_logger
from odoo.tools.safe_eval import safe_eval

_MODULE = "odoo.addons.base.models.ir_actions_server"
_DELIVERY = "odoo.libs.webhook"


class ServerActionCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.Action = cls.env["ir.actions.server"]

    def _action(self, **vals):
        return self.Action.create(
            {"model_id": self.partner_model.id, "name": "act", **vals}
        )

    def _partners(self, n, prefix="p"):
        return self.env["res.partner"].create(
            [{"name": f"{prefix}{i}"} for i in range(n)]
        )

    def _ctx(self, records):
        return {
            "active_model": "res.partner",
            "active_ids": records.ids,
            "active_id": records[:1].id,
        }


@tagged("post_install", "-at_install")
class TestNameIsNeverNull(ServerActionCase):
    def test_an_omitted_name_is_derived_from_the_type(self):
        action = self.Action.create(
            {"model_id": self.partner_model.id, "state": "code", "code": "pass"}
        )
        self.env.flush_all()
        self.assertEqual(action.name, "Execute Code")

    def test_a_falsy_name_is_derived_too(self):
        for blank in (False, ""):
            with self.subTest(blank=blank):
                action = self.Action.create(
                    {
                        "name": blank,
                        "model_id": self.partner_model.id,
                        "state": "code",
                        "code": "pass",
                    }
                )
                self.env.flush_all()
                self.assertEqual(action.name, "Execute Code")

    def test_a_typed_name_survives_a_type_change(self):
        action = self._action(name="Execute Code", state="code", code="pass")
        self.env.flush_all()
        action.write({"state": "object_create", "value": "x"})
        self.env.flush_all()
        self.assertEqual(
            action.name,
            "Execute Code",
            "a name the user typed is theirs, whatever it happens to say",
        )

    def test_a_derived_name_follows_the_type(self):
        action = self.Action.create(
            {"model_id": self.partner_model.id, "state": "code", "code": "pass"}
        )
        self.env.flush_all()
        action.write({"state": "object_create", "value": "x"})
        self.env.flush_all()
        self.assertEqual(action.name, "Create Contact")


@tagged("post_install", "-at_install")
class TestObjectCopyDuplicatesTheRecordItNames(ServerActionCase):
    def test_it_copies_the_referenced_record_not_its_own_model(self):
        shared = sorted(
            set(self.env["res.partner"].search([]).ids)
            & set(self.env["res.country"].search([]).ids)
        )
        self.assertTrue(shared, "precondition: an id naming a record in both models")
        partner = self.env["res.partner"].browse(shared[0])
        country_model = self.env["ir.model"]._get("res.country")

        action = self.Action.create(
            {"name": "dup", "model_id": country_model.id, "state": "object_copy"}
        )
        action.write({"resource_ref": f"res.partner,{partner.id}"})
        self.assertEqual(
            action.crud_model_id.model,
            "res.country",
            "the action's own model, which is not the reference's",
        )

        countries_before = self.env["res.country"].search([]).ids
        partners_before = self.env["res.partner"].search([]).ids
        action.with_context(
            active_model="res.country",
            active_id=shared[0],
            active_ids=[shared[0]],
        ).run()
        self.env.flush_all()

        self.assertFalse(
            self.env["res.country"].search([("id", "not in", countries_before)]),
            "nothing of the action's own model was touched",
        )
        new = self.env["res.partner"].search([("id", "not in", partners_before)])
        self.assertEqual(len(new), 1, "the referenced partner was duplicated")
        self.assertEqual(new.name, f"{partner.name} (copy)")


@tagged("post_install", "-at_install")
class TestUpdatePathIsHonouredOnEveryPath(ServerActionCase):
    def test_the_normal_path_writes_the_record_the_path_names(self):
        parent = self.env["res.partner"].create({"name": "PARENT"})
        child = self.env["res.partner"].create(
            {"name": "CHILD", "parent_id": parent.id}
        )
        action = self._action(
            state="object_write",
            update_path="parent_id.ref",
            evaluation_type="value",
            value="LEAF",
        )
        action.with_context(**self._ctx(child)).run()
        self.env.flush_all()
        self.assertEqual(parent.ref, "LEAF")
        self.assertFalse(child.ref, "the root record is not the target")

    def test_an_on_change_refuses_a_path_that_leaves_the_record(self):
        partner = self.env["res.partner"].create({"name": "root"})
        action = self._action(
            state="object_write",
            update_path="parent_id.ref",
            evaluation_type="value",
            value="LEAF",
        )
        with self.assertRaises(UserError):
            action.with_context(
                onchange_self=partner.new(origin=partner),
                active_model="res.partner",
                active_id=partner.id,
            ).run()

    def test_an_on_change_still_writes_a_single_segment_path(self):
        partner = self.env["res.partner"].create({"name": "root"})
        cached = partner.new(origin=partner)
        action = self._action(
            state="object_write",
            update_path="function",
            evaluation_type="value",
            value="Set By Action",
        )
        action.with_context(
            onchange_self=cached, active_model="res.partner", active_id=partner.id
        ).run()
        self.assertEqual(cached.function, "Set By Action")
        self.assertFalse(partner.function, "an on-change writes the cache only")


@tagged("post_install", "-at_install")
class TestConfigurationSurvivesAStateChange(ServerActionCase):
    def test_update_path_round_trips_through_another_state(self):
        action = self._action(
            state="object_write", update_path="ref", evaluation_type="value", value="V"
        )
        self.env.flush_all()
        action.write({"state": "code", "code": "pass"})
        self.env.flush_all()
        self.assertFalse(action.update_field_id, "the derived field is cleared")
        action.write({"state": "object_write"})
        self.env.flush_all()
        self.assertEqual(action.update_path, "ref")
        self.assertEqual(action.update_field_id.name, "ref")
        self.assertEqual(action.value, "V")

    def test_a_chosen_crud_model_is_seeded_not_imposed(self):
        users_model = self.env["ir.model"]._get("res.users")
        action = self._action(state="object_create", value="n")
        self.assertEqual(
            action.crud_model_id, self.partner_model, "seeded from the action's model"
        )
        action.write({"crud_model_id": users_model.id})
        self.env.flush_all()
        action.write({"state": "object_create"})
        self.env.flush_all()
        self.assertEqual(
            action.crud_model_id, users_model, "a value the user chose is kept"
        )


@tagged("post_install", "-at_install")
class TestBatchingIsDeliveredNotJustPromised(ServerActionCase):
    def _multi_over(self, children):
        return self._action(
            name="P", state="multi", child_ids=[Command.set(children.ids)]
        )

    def test_a_multi_over_a_code_child_still_runs_it_once_per_record(self):
        child = self._action(
            name="C",
            state="code",
            code="record.write({'ref': (record.ref or '') + 'x'})",
        )
        parent = self._multi_over(child)
        self.assertFalse(parent._is_batchable())
        records = self._partners(5, "batch")
        parent.with_context(**self._ctx(records)).run()
        self.env.flush_all()
        self.assertEqual(records.mapped("ref"), ["x"] * 5, "every record got a run")

    def test_a_multi_over_a_batchable_child_hands_it_the_whole_batch(self):
        child = self._action(
            name="C",
            state="object_write",
            update_path="ref",
            evaluation_type="value",
            value="B",
        )
        parent = self._multi_over(child)
        self.assertTrue(parent._is_batchable())
        records = self._partners(5, "whole")

        seen = []
        cls = type(self.env["ir.actions.server"])
        origin = cls._run_action_object_write

        def spy(action, eval_context=None):
            seen.append(len(eval_context["records"]))
            return origin(action, eval_context=eval_context)

        self.patch(cls, "_run_action_object_write", spy)
        parent.with_context(**self._ctx(records)).run()
        self.env.flush_all()
        self.assertEqual(seen, [5], "one call carrying the whole batch")
        self.assertEqual(records.mapped("ref"), ["B"] * 5)

    def test_an_empty_multi_batches_nothing(self):
        self.assertFalse(
            self._multi_over(self.Action.browse())._is_batchable(),
            "all() over no children is vacuously true, which is not an answer",
        )


@tagged("post_install", "-at_install")
class TestObjectWriteCostsNothingPerExtraRecord(ServerActionCase):
    def _cost(self, action, n):
        records = self._partners(n, f"cost{n}_")
        self.env.flush_all()
        self.env.invalidate_all()
        before = self.env.cr.sql_statement_count
        action.with_context(**self._ctx(records)).run()
        self.env.flush_all()
        return self.env.cr.sql_statement_count - before

    def test_a_static_update_costs_the_same_for_two_records_and_twenty(self):
        action = self._action(
            state="object_write", update_path="ref", evaluation_type="value", value="B"
        )
        small, large = self._cost(action, 2), self._cost(action, 20)
        self.assertLessEqual(
            large - small,
            2,
            f"18 further records must be nearly free; measured {small} -> {large}",
        )

    def test_a_sequence_still_gets_one_number_per_record(self):
        sequence = self.env["ir.sequence"].create(
            {"name": "Seq", "prefix": "S-", "padding": 3}
        )
        action = self._action(
            state="object_write",
            update_path="ref",
            evaluation_type="sequence",
            sequence_id=sequence.id,
        )
        self.assertFalse(action._resolve_runner()[1])
        records = self._partners(3, "seq")
        action.with_context(**self._ctx(records)).run()
        self.env.flush_all()
        self.assertEqual(
            len(set(records.mapped("ref"))), 3, "three records, three numbers"
        )

    def test_an_equation_is_evaluated_against_each_record(self):
        action = self._action(
            state="object_write",
            update_path="ref",
            evaluation_type="equation",
            value="record.name",
        )
        self.assertFalse(action._resolve_runner()[1])
        records = self._partners(3, "eq")
        action.with_context(**self._ctx(records)).run()
        self.env.flush_all()
        self.assertEqual(records.mapped("ref"), records.mapped("name"))


@tagged("post_install", "-at_install")
class TestWebhookGuardHoldsAtSendTime(ServerActionCase):
    def _webhook(self, **vals):
        return self._action(
            state="webhook", webhook_url="https://example.com/hook", **vals
        )

    def _resolving(self, *answers):
        remaining = iter(answers)

        def getaddrinfo(host, port, *args, **kwargs):
            return [
                (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (a, port))
                for a in next(remaining)
            ]

        return patch("socket.getaddrinfo", side_effect=getaddrinfo)

    def _sending(self):
        sent = []

        def send(adapter, request, **kwargs):
            sent.append((request.netguard_address, request.headers.get("Host")))
            response = requests.Response()
            response.status_code = 200
            response.request = request
            response.url = request.url
            response._content = b""
            return response

        return sent, patch.object(HTTPAdapter, "send", autospec=True, side_effect=send)

    def test_an_unresolvable_host_is_blocked_not_allowed(self):
        with self.assertRaises(
            DestinationRefused,
            msg="an address the guard cannot judge is not one it may allow",
        ):
            self.env["ir.egress"].check_url("http://nx.invalid/hook")

    def test_a_public_host_is_still_allowed(self):
        self.env["ir.egress"].check_url("https://1.1.1.1/hook")

    def test_multicast_and_reserved_are_still_blocked(self):
        for host in ("224.0.0.1", "[ff02::1]", "[64:ff9b::7f00:1]"):
            with self.subTest(host=host), self.assertRaises(DestinationRefused):
                self.env["ir.egress"].check_url(f"http://{host}/h")

    def test_one_policy_decides_at_the_action_and_at_delivery(self):
        self.env["ir.config_parameter"].set_param(
            "base.egress_allowed_networks", "127.0.0.0/8"
        )
        action = self._webhook()
        action.webhook_url = "http://127.0.0.1:8069/hook"
        sent, sending = self._sending()
        with sending:
            action.with_context(**self._ctx(self._partners(1))).run()
            self.env.cr.postcommit.run()
        self.assertEqual(sent, [("127.0.0.1", "127.0.0.1:8069")])

    def test_the_request_does_not_follow_redirects(self):
        action = self._webhook()
        with patch.object(requests.Session, "post") as post:
            action.with_context(**self._ctx(self._partners(1))).run()
            self.env.cr.postcommit.run()
        self.assertIs(post.call_args.kwargs["allow_redirects"], False)

    def test_the_guard_runs_again_at_delivery(self):
        action = self._webhook()
        sent, sending = self._sending()
        with (
            self._resolving(["93.184.216.34"], ["127.0.0.1"]),
            patch.object(requests.Session, "send", _super_send),
            sending,
            self.assertLogs(_DELIVERY, "ERROR") as logs,
        ):
            action.with_context(**self._ctx(self._partners(1))).run()
            self.env.cr.postcommit.run()
        self.assertEqual(sent, [])
        self.assertIn("was NOT sent", logs.output[0])

    def test_delivery_connects_to_the_checked_address_under_the_hostname(self):
        action = self._webhook()
        sent, sending = self._sending()
        with (
            self._resolving(["93.184.216.34"], ["93.184.216.34"]),
            patch.object(requests.Session, "send", _super_send),
            sending,
        ):
            action.with_context(**self._ctx(self._partners(1))).run()
            self.env.cr.postcommit.run()
        self.assertEqual(sent, [("93.184.216.34", "example.com")])

    def test_the_timeout_is_re_checked_when_the_state_becomes_webhook(self):
        action = self._action(state="code", code="pass", webhook_timeout=0)
        with self.assertRaises(ValidationError):
            action.write({"state": "webhook", "webhook_url": "https://e.com/hook"})


@tagged("post_install", "-at_install")
class TestWebhookPayloadHasOneShape(ServerActionCase):
    def _sample_record(self):
        return (
            self.env["res.partner"].with_context(active_test=False).search([], limit=1)
        )

    def test_the_sample_is_what_would_be_sent(self):
        field = self.env["ir.model.fields"]._get("res.partner", "name")
        action = self._action(
            state="webhook",
            webhook_url="https://example.com/hook",
            webhook_field_ids=[Command.set(field.ids)],
        )
        record = self._sample_record()
        sent = {}

        def fake_post(_self, url, **kwargs):
            sent.update(kwargs)
            response = requests.Response()
            response.status_code = 200
            return response

        with patch.object(requests.Session, "post", fake_post):
            action.with_context(active_model="res.partner", active_id=record.id).run()
            self.env.cr.postcommit.run()
        self.assertEqual(
            action._dump_webhook_payload(action._get_webhook_payload(record)),
            sent["data"],
        )

    def test_the_shape_does_not_depend_on_the_field_selection(self):
        field = self.env["ir.model.fields"]._get("res.partner", "name")
        record = self._sample_record()
        bare = self._action(state="webhook", webhook_url="https://e.com/h")
        chosen = self._action(
            state="webhook",
            webhook_url="https://e.com/h",
            webhook_field_ids=[Command.set(field.ids)],
        )
        framing = {"_action", "_id", "_model", "id"}
        self.assertEqual(set(bare._get_webhook_payload(record)), framing)
        self.assertEqual(
            set(chosen._get_webhook_payload(record)) - {"name"},
            framing,
            "the framing keys are there whether or not a field is chosen",
        )


@tagged("post_install", "-at_install")
class TestNeedingARecordIsAskedOfTheAction(ServerActionCase):
    def _create_action(self, **vals):
        return self._action(state="object_create", value="spawned", **vals)

    def test_a_create_with_no_link_field_runs_without_a_target(self):
        action = self._create_action()
        self.assertIn("object_create", action._get_states_needing_a_live_record())
        self.assertFalse(action._is_live_record_required())

        before = self.env["res.partner"].search([]).ids
        action.run()
        self.env.flush_all()
        made = self.env["res.partner"].search([("id", "not in", before)])
        self.assertEqual(made.mapped("name"), ["spawned"])

    @mute_logger(_MODULE)
    def test_a_create_that_links_is_skipped_without_a_target(self):
        link = self.env["ir.model.fields"]._get("res.partner", "child_ids")
        action = self._create_action(link_field_id=link.id)
        self.assertTrue(action._is_live_record_required())

        before = self.env["res.partner"].search([]).ids
        action.run()
        self.env.flush_all()
        self.assertFalse(
            self.env["res.partner"].search([("id", "not in", before)]),
            "there is nothing to link the new record to, so nothing is made",
        )

    def test_a_write_always_needs_its_target(self):
        action = self._action(
            state="object_write", update_path="ref", evaluation_type="value", value="V"
        )
        self.assertTrue(action._is_live_record_required())

    def test_the_cron_warning_follows_the_same_question(self):
        link = self.env["ir.model.fields"]._get("res.partner", "child_ids")
        plain = self._create_action(usage="ir_cron")
        linked = self._create_action(usage="ir_cron", link_field_id=link.id)
        self.assertFalse(plain.warning, "it makes its record on a schedule, fine")
        self.assertIn("would do nothing", linked.warning)


@tagged("post_install", "-at_install")
class TestOneRecordResolution(ServerActionCase):
    def test_ids_without_a_model_name_no_records(self):
        partners = self._partners(2, "amb")
        action = self._action(state="code", code="pass")
        self.assertFalse(
            action.with_context(active_ids=partners.ids).sudo()._get_records_targeted(),
            "ids that do not say which model they belong to name nothing",
        )

    def test_the_eval_context_and_the_runners_see_the_same_records(self):
        partners = self._partners(3, "same")
        action = self._action(
            state="code", code="action = {'n': len(records), 'r': record.id}"
        )
        scoped = action.with_context(**self._ctx(partners))
        eval_context = scoped._prepare_eval_context(scoped)
        self.assertEqual(eval_context["records"], scoped.sudo()._get_records_targeted())
        self.assertEqual(eval_context["record"], partners[:1])
        self.assertEqual(scoped.run(), {"n": 3, "r": partners[0].id})


@tagged("post_install", "-at_install")
class TestTheFormOffersExactlyOneValueInput(ServerActionCase):
    VALUE_FIELDS = (
        "value",
        "html_value",
        "sequence_id",
        "resource_ref",
        "selection_value",
        "update_boolean_value",
    )

    def _arch(self):
        view = self.env.ref("base.view_server_action_form")
        arch = view.arch_db if isinstance(view.arch_db, str) else view.arch
        return etree.fromstring(arch)

    def _eval_context(self, action):
        context = {"context": {}}
        for name, field in action._fields.items():
            value = action[name]
            if field.type in ("many2one", "reference"):
                context[name] = value.id if value else False
            elif field.type in ("one2many", "many2many"):
                context[name] = value.ids
            else:
                context[name] = value
        return context

    def _visible_value_inputs(self, action):
        arch = self._arch()
        parents = {child: parent for parent in arch.iter() for child in parent}
        context = self._eval_context(action)

        def hidden(node):
            while node is not None:
                expression = node.get("invisible")
                if expression and safe_eval(expression, dict(context)):
                    return True
                node = parents.get(node)
            return False

        return [
            node.get("name")
            for node in arch.iter("field")
            if node.get("name") in self.VALUE_FIELDS and not hidden(node)
        ]

    def test_every_update_record_shape_offers_one_and_only_one(self):
        selection_field = self.env["ir.model.fields"]._get("res.partner", "type")
        shapes = [
            ("a static value on a char", "ref", "value"),
            ("an expression on a char", "ref", "equation"),
            ("a static value on a m2o", "parent_id", "value"),
            ("an expression on a m2o", "parent_id", "equation"),
            ("a static value on html", "comment", "value"),
            ("a static value on a boolean", "active", "value"),
            ("a static value on a selection", "type", "value"),
            ("a sequence", "ref", "sequence"),
        ]
        for label, path, evaluation in shapes:
            with self.subTest(shape=label):
                action = self._action(
                    state="object_write",
                    update_path=path,
                    evaluation_type=evaluation,
                )
                visible = self._visible_value_inputs(action)
                self.assertEqual(
                    len(visible),
                    1,
                    f"{label}: the form offers {visible}, not one input",
                )
        self.assertTrue(selection_field, "precondition: res.partner.type exists")

    def test_an_expression_gets_the_editor_even_on_a_relational_field(self):
        action = self._action(
            state="object_write",
            update_path="parent_id",
            evaluation_type="equation",
            value="env.user.partner_id.id",
        )
        self.assertEqual(action.value_field_to_show, "value")
        self.assertEqual(self._visible_value_inputs(action), ["value"])

    def test_a_record_picker_is_still_offered_for_a_static_relational_value(self):
        action = self._action(
            state="object_write", update_path="parent_id", evaluation_type="value"
        )
        self.assertEqual(action.value_field_to_show, "resource_ref")
        self.assertEqual(self._visible_value_inputs(action), ["resource_ref"])


@tagged("post_install", "-at_install")
class TestTheOverridesStayInTheirChain(ServerActionCase):
    def test_the_readable_fields_override_is_reached(self):
        action = self._action(state="code", code="pass")
        self.assertLessEqual(
            {"group_ids", "model_name"}, set(action._get_action_dict())
        )

    def test_every_eval_context_override_requires_its_action(self):
        parameter = inspect.signature(
            type(self.Action)._prepare_eval_context
        ).parameters["action"]
        self.assertIs(
            parameter.default,
            inspect.Parameter.empty,
            "the registry class, not just the base one, must require the action",
        )


@tagged("post_install", "-at_install")
class TestNameIsCustomFollowsTheAutomatedName(ServerActionCase):
    def test_saving_the_automated_name_back_does_not_pin_it(self):
        action = self._action(state="code", code="pass", name=False)
        self.assertEqual(action.name, "Execute Code")
        action.write({"name": "Execute Code"})
        self.assertFalse(action.name_is_custom)
        action.write({"state": "object_write", "update_path": "name"})
        self.assertEqual(action.name, "Update Contact")

    def test_a_form_round_trip_through_a_type_change_still_follows_the_type(self):
        action = self._action(state="code", code="pass", name=False)
        action.write(
            {"state": "object_write", "update_path": "name", "name": "Update Contact"}
        )
        self.assertFalse(action.name_is_custom)
        action.write({"state": "code", "code": "pass"})
        self.assertEqual(action.name, "Execute Code")

    def test_a_typed_name_is_still_custom(self):
        action = self._action(state="code", code="pass", name=False)
        action.write({"name": "Mine"})
        self.assertTrue(action.name_is_custom)
        action.write({"state": "object_write", "update_path": "name"})
        self.assertEqual(action.name, "Mine")

    def test_the_onchange_does_not_pin_the_name_it_was_handed(self):
        action = self._action(state="code", code="pass", name=False)
        form = action.new(origin=action)
        form.name = "Execute Code"
        form._onchange_name()
        self.assertFalse(form.name_is_custom)
        form.name = "Mine"
        form._onchange_name()
        self.assertTrue(form.name_is_custom)


@tagged("post_install", "-at_install")
class TestPerRecordLoopRebindsEverything(ServerActionCase):
    def test_record_records_and_model_carry_the_record_context(self):
        field = self.env["ir.model.fields"]._get("res.partner", "ref")
        action = self._action(
            state="object_write",
            update_path="ref",
            evaluation_type="equation",
            value=(
                "'%s/%s/%s' % (record.env.context.get('active_id'),"
                " records.env.context.get('active_id'),"
                " model.env.context.get('active_id'))"
            ),
        )
        self.assertEqual(action.update_field_id, field)
        partners = self._partners(3)
        action.with_context(**self._ctx(partners)).run()
        for partner in partners:
            self.assertEqual(partner.ref, "/".join([str(partner.id)] * 3))


@tagged("post_install", "-at_install")
class TestAnEmptiedNameReturnsToTheAutomatedOne(ServerActionCase):
    def test_writing_an_empty_name_yields_the_automated_name(self):
        action = self._action(state="code", code="pass", name="Mine")
        self.env.flush_all()
        self.assertTrue(action.name_is_custom)
        for blank in (False, ""):
            with self.subTest(blank=blank):
                action.write({"name": "Mine"})
                action.write({"name": blank})
                self.env.flush_all()
                self.assertEqual(action.name, "Execute Code")
                self.assertFalse(action.name_is_custom)

    def test_releasing_the_custom_flag_alone_yields_the_automated_name(self):
        action = self._action(state="code", code="pass", name="Mine")
        action.write({"name_is_custom": False})
        self.env.flush_all()
        self.assertEqual(action.name, "Execute Code")


@tagged("post_install", "-at_install")
class TestAnX2manyValueIsANumberOrRefused(ServerActionCase):
    def _tag_action(self, operation, value):
        return self._action(
            state="object_write",
            update_path="tag_ids",
            evaluation_type="value",
            update_m2m_operation=operation,
            value=value,
        )

    def test_a_value_that_is_not_an_id_is_refused_as_a_number_is(self):
        partners = self._partners(2)
        action = self._tag_action("add", "not-an-id")
        with self.assertRaises(UserError):
            action.with_context(**self._ctx(partners)).run()

    def test_an_id_links_removes_and_sets(self):
        tag = self.env["res.partner.tag"].create({"name": "x2m"})
        partners = self._partners(2)
        self._tag_action("add", str(tag.id)).with_context(**self._ctx(partners)).run()
        self.assertEqual(partners.tag_ids, tag)
        self._tag_action("remove", str(tag.id)).with_context(
            **self._ctx(partners)
        ).run()
        self.assertFalse(partners.tag_ids)
        self._tag_action("set", str(tag.id)).with_context(**self._ctx(partners)).run()
        self.assertEqual(partners.tag_ids, tag)
        self._tag_action("clear", "").with_context(**self._ctx(partners)).run()
        self.assertFalse(partners.tag_ids)

    def test_an_empty_value_writes_nothing(self):
        partners = self._partners(1)
        self._tag_action("add", "").with_context(**self._ctx(partners)).run()
        self.assertFalse(partners.tag_ids)


@tagged("post_install", "-at_install")
class TestASequenceValueNeedsASequence(ServerActionCase):
    def test_the_form_warns_and_the_run_refuses(self):
        action = self._action(
            state="object_write", update_path="ref", evaluation_type="sequence"
        )
        self.assertIn("sequence", (action.warning or "").lower())
        with self.assertRaises(UserError):
            action._eval_value()
        action.sequence_id = self.env["ir.sequence"].create(
            {"name": "seq", "code": "seq.test", "prefix": "S"}
        )
        self.assertFalse(action.warning)
        partners = self._partners(1)
        action.with_context(**self._ctx(partners)).run()
        self.assertTrue(partners.ref.startswith("S"))


@tagged("post_install", "-at_install")
class TestCrudTargetsAreCheckedWithoutGroups(ServerActionCase):
    """Measured 2026-09-17: with no group on the action, a user who could
    write the action's model created and copied records of a model they
    could not create, because only the group-gated branch checked the target.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create(
            {
                "name": "crud-target",
                "login": "crud_target",
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("base.group_partner_manager").id,
                        ],
                    )
                ],
            }
        )
        Access = cls.env["ir.model.access"].with_user(cls.user)
        assert Access.check("res.partner", "write", False)
        assert not Access.check("res.users", "create", False)
        cls.users_model = cls.env["ir.model"]._get("res.users")

    def test_an_ungated_create_needs_create_access_on_its_target(self):
        partners = self._partners(1)
        action = self._action(
            state="object_create", crud_model_id=self.users_model.id, value="nope"
        )
        self.assertFalse(action.group_ids)
        with self.assertRaises(AccessError):
            action.with_user(self.user).with_context(**self._ctx(partners)).run()

    def test_an_ungated_copy_needs_create_access_on_the_copied_model(self):
        partners = self._partners(1)
        action = self._action(state="object_copy", crud_model_id=self.users_model.id)
        action.write(
            {"resource_ref": f"res.users,{self.env.ref('base.user_admin').id}"}
        )
        before = self.env["res.users"].sudo().search_count([])
        with self.assertRaises(AccessError):
            action.with_user(self.user).with_context(**self._ctx(partners)).run()
        self.assertEqual(self.env["res.users"].sudo().search_count([]), before)

    def test_a_copy_is_checked_against_the_record_it_copies(self):
        partners = self._partners(1)
        action = self._action(state="object_copy", crud_model_id=self.partner_model.id)
        action.write(
            {"resource_ref": f"res.users,{self.env.ref('base.user_admin').id}"}
        )
        self.assertEqual(action.crud_model_id.model, "res.partner")
        with self.assertRaises(AccessError):
            action.with_user(self.user).with_context(**self._ctx(partners)).run()

    def test_a_copy_within_the_user_s_rights_runs(self):
        partners = self._partners(2)
        action = self._action(state="object_copy")
        action.write({"resource_ref": f"res.partner,{partners[1].id}"})
        before = self.env["res.partner"].search_count([])
        action.with_user(self.user).with_context(**self._ctx(partners[:1])).run()
        self.assertEqual(self.env["res.partner"].search_count([]), before + 1)


@tagged("post_install", "-at_install")
class TestHistoryRecordsCodeNotItsAbsence(ServerActionCase):
    def test_a_create_without_code_writes_no_history(self):
        History = self.env["ir.actions.server.history"]
        action = self._action(state="object_write", update_path="name", code=False)
        self.assertFalse(History.search([("action_id", "=", action.id)]))
        action.write({"code": "pass", "state": "code"})
        self.assertEqual(len(History.search([("action_id", "=", action.id)])), 1)


@tagged("post_install", "-at_install")
class TestACopysNameIsKept(ServerActionCase):
    def test_the_copy_suffix_marks_the_name_custom(self):
        action = self._action(state="code", code="pass", name=False)
        self.env.flush_all()
        self.assertFalse(action.name_is_custom)
        copy = action.copy()
        self.env.flush_all()
        self.assertEqual(copy.name, "Execute Code (copy)")
        self.assertTrue(copy.name_is_custom)
        copy.write({"state": "object_write", "update_path": "name"})
        self.env.flush_all()
        self.assertEqual(copy.name, "Execute Code (copy)")

    def test_a_copy_given_its_own_name_keeps_that_one(self):
        action = self._action(state="code", code="pass", name=False)
        copy = action.copy({"name": "Second"})
        self.env.flush_all()
        self.assertEqual((copy.name, copy.name_is_custom), ("Second", True))


@tagged("post_install", "-at_install")
class TestADelegatingCreatorsNameIsCustom(ServerActionCase):
    """ir.cron creates its server action through _inherits, and a delegating
    create hands every parent field a default, name_is_custom included; a
    default of False there read as "not custom" and the cron's name went back
    to the automated one on the next type change.
    """

    def test_a_cron_s_name_survives_a_type_change(self):
        cron = self.env["ir.cron"].create(
            {
                "name": "Nightly",
                "model_id": self.partner_model.id,
                "state": "code",
                "code": "pass",
                "repeat_interval": 1,
                "repeat_unit": "day",
            }
        )
        self.env.flush_all()
        self.assertTrue(cron.ir_actions_server_id.name_is_custom)
        cron.write({"state": "object_write", "update_path": "name"})
        self.env.flush_all()
        self.assertEqual(cron.name, "Nightly")
