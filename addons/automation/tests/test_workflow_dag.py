import logging

from dateutil.relativedelta import relativedelta
from psycopg.errors import UniqueViolation

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

_logger = logging.getLogger(__name__)


def link(env, source, target, condition="on_success", **kw):
    return env["workflow.edge"].create(
        {
            "source_node_id": source.id,
            "target_node_id": target.id,
            "condition": condition,
            **kw,
        }
    )


class TestWorkflowDAG(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Automation = self.env["automation.rule"]
        self.Action = self.env["ir.actions.server"]
        self.Runtime = self.env["automation.runtime"]
        self.Partner = self.env["res.partner"]

        self.model_partner = self.env["ir.model"]._get("res.partner")
        self.test_partner = self.Partner.create({"name": "Test Partner"})

        self.automation = self.Automation.create(
            {
                "name": "Test DAG Workflow",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
            }
        )

    def _create_action(self, name, code="pass", predecessors=None):
        vals = {
            "name": name,
            "model_id": self.model_partner.id,
            "state": "code",
            "code": code,
            "automation_rule_id": self.automation.id,
            "usage": "automation",
        }
        action = self.Action.create(vals)
        for predecessor in predecessors or []:
            self._link(predecessor, action)
        return action

    def _link(self, source, target, condition="on_success", **kw):
        return link(self.env, source, target, condition, **kw)

    def _make_runtime(self, automation=None):
        auto = automation or self.automation
        runtime = self.Runtime.create(
            {
                "automation_id": auto.id,
                "res_model": "res.partner",
                "res_id": self.test_partner.id,
            }
        )
        runtime.action_start()
        return runtime

    def _line_for(self, runtime, action):
        return runtime.line_ids.filtered(lambda l: l.action_id == action)

    def test_successor_relationship(self):
        action_a = self._create_action("A")
        action_b = self._create_action("B", predecessors=[action_a])

        self.assertIn(action_b, action_a._get_successors())
        self.assertIn(action_a, action_b._get_predecessors())

    def test_cycle_detection_direct(self):
        action_a = self._create_action("A")
        action_b = self._create_action("B", predecessors=[action_a])

        with self.assertRaises(ValidationError):
            self._link(action_b, action_a)

    def test_cycle_detection_indirect(self):
        action_a = self._create_action("A")
        action_b = self._create_action("B", predecessors=[action_a])
        action_c = self._create_action("C", predecessors=[action_b])

        with self.assertRaises(ValidationError):
            self._link(action_c, action_a)

    def test_self_dependency_prevented(self):
        action_a = self._create_action("A")

        with self.assertRaises(ValidationError):
            self._link(action_a, action_a)

    def test_runtime_lines_created_from_dag(self):
        action_a = self._create_action("A")
        action_b = self._create_action("B", predecessors=[action_a])
        action_c = self._create_action("C", predecessors=[action_b])

        runtime = self._make_runtime()

        line_a = self._line_for(runtime, action_a)
        line_b = self._line_for(runtime, action_b)
        line_c = self._line_for(runtime, action_c)

        self.assertEqual(line_a.state, "ready")
        self.assertEqual(line_b.state, "waiting")
        self.assertEqual(line_c.state, "waiting")

        self.assertIn(line_a, line_b._get_predecessors())
        self.assertIn(line_b, line_c._get_predecessors())

    def test_parallel_branches_both_ready(self):
        action_a = self._create_action("A")
        action_b = self._create_action("B", predecessors=[action_a])
        action_c = self._create_action("C", predecessors=[action_a])

        runtime = self._make_runtime()
        line_a = self._line_for(runtime, action_a)
        line_b = self._line_for(runtime, action_b)
        line_c = self._line_for(runtime, action_c)

        self.assertEqual(line_a.state, "ready")
        self.assertEqual(line_b.state, "waiting")
        self.assertEqual(line_c.state, "waiting")

        line_a.action_mark_done()

        self.assertEqual(line_b.state, "ready")
        self.assertEqual(line_c.state, "ready")

    def test_diamond_join(self):
        action_a = self._create_action("A")
        action_b = self._create_action("B", predecessors=[action_a])
        action_c = self._create_action("C", predecessors=[action_a])
        action_d = self._create_action("D", predecessors=[action_b, action_c])

        runtime = self._make_runtime()
        line_a = self._line_for(runtime, action_a)
        line_b = self._line_for(runtime, action_b)
        line_c = self._line_for(runtime, action_c)
        line_d = self._line_for(runtime, action_d)

        line_a.action_mark_done()

        self.assertEqual(line_b.state, "ready")
        self.assertEqual(line_c.state, "ready")
        self.assertEqual(line_d.state, "waiting", "D still needs B and C")
        self.assertFalse(line_d._predecessors_satisfied(), "D still needs B and C")

        line_b.action_mark_done()
        self.assertEqual(line_d.state, "waiting", "D still needs C")
        self.assertFalse(line_d._predecessors_satisfied(), "D still needs C")

        line_c.action_mark_done()
        self.assertEqual(line_d.state, "ready", "D ready after both B and C")
        self.assertTrue(line_d._predecessors_satisfied())

    def test_multiple_root_actions(self):
        action_a = self._create_action("A")
        action_b = self._create_action("B")

        runtime = self._make_runtime()
        line_a = self._line_for(runtime, action_a)
        line_b = self._line_for(runtime, action_b)

        self.assertEqual(line_a.state, "ready")
        self.assertEqual(line_b.state, "ready")

    def test_runtime_completes_when_all_lines_done(self):
        action_a = self._create_action("A")

        runtime = self._make_runtime()
        self.assertEqual(runtime.state, "in_progress")

        line_a = self._line_for(runtime, action_a)
        line_a.action_mark_done()

        self.assertEqual(runtime.state, "done")

    def test_runtime_progress_display(self):
        action_a = self._create_action("A")
        self._create_action("B", predecessors=[action_a])

        runtime = self._make_runtime()
        self.assertEqual(runtime.progress_display, "0/2 steps")

        self._line_for(runtime, action_a).action_mark_done()
        runtime.invalidate_recordset(["progress_display"])
        self.assertEqual(runtime.progress_display, "1/2 steps")

    def test_run_all_simple_chain(self):
        action_a = self._create_action("A", code="record.write({'comment': 'A'})")
        action_b = self._create_action(
            "B", code="record.write({'comment': 'B'})", predecessors=[action_a]
        )
        self._create_action(
            "C", code="record.write({'comment': 'C'})", predecessors=[action_b]
        )

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "res_model": "res.partner",
                "res_id": self.test_partner.id,
            }
        )
        runtime.action_start()
        final_state = runtime.action_run_all()

        self.assertEqual(final_state, "done")
        self.assertEqual(runtime.state, "done")

        for line in runtime.line_ids:
            self.assertEqual(line.state, "done", f"Line '{line.name}' should be done")

    def test_run_all_parallel_branches(self):
        action_a = self._create_action("A")
        action_b = self._create_action("B", predecessors=[action_a])
        action_c = self._create_action("C", predecessors=[action_a])
        self._create_action("D", predecessors=[action_b, action_c])

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "res_model": "res.partner",
                "res_id": self.test_partner.id,
            }
        )
        runtime.action_start()
        final_state = runtime.action_run_all()

        self.assertEqual(final_state, "done")
        for line in runtime.line_ids:
            self.assertEqual(line.state, "done")

    def test_manual_trigger_dag_creates_runtime(self):
        action_a = self._create_action("A")
        self._create_action("B", predecessors=[action_a])

        before_count = self.Runtime.search_count(
            [("automation_id", "=", self.automation.id)]
        )

        self.automation.with_context(
            active_model="res.partner",
            active_ids=self.test_partner.ids,
        ).action_manual_trigger()

        after_count = self.Runtime.search_count(
            [("automation_id", "=", self.automation.id)]
        )
        self.assertEqual(after_count, before_count + 1)

    def test_manual_trigger_no_dag_direct_process(self):
        self._create_action("A", code="record.write({'comment': 'triggered'})")

        before_count = self.Runtime.search_count(
            [("automation_id", "=", self.automation.id)]
        )

        result = self.automation.with_context(
            active_model="res.partner",
            active_ids=self.test_partner.ids,
        ).action_manual_trigger()

        after_count = self.Runtime.search_count(
            [("automation_id", "=", self.automation.id)]
        )
        self.assertEqual(after_count, before_count)
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["params"]["type"], "success")

    def test_manual_trigger_wrong_trigger_raises(self):
        auto = self.Automation.create(
            {
                "name": "Write Automation",
                "model_id": self.model_partner.id,
                "trigger": "on_write",
            }
        )

        with self.assertRaises(ValidationError):
            auto.action_manual_trigger()

    def test_manual_trigger_no_matching_records(self):
        self.automation.filter_domain = (
            "[('name', '=', '__no_record_will_ever_match__')]"
        )
        self._create_action("A")

        result = self.automation.with_context(
            active_model="res.partner",
            active_ids=self.test_partner.ids,
        ).action_manual_trigger()

        self.assertEqual(result["params"]["type"], "warning")

    def test_runtime_cancel(self):
        action_a = self._create_action("A")
        self._create_action("B", predecessors=[action_a])

        runtime = self._make_runtime()
        runtime.action_cancel()

        self.assertEqual(runtime.state, "cancel")
        for line in runtime.line_ids:
            self.assertIn(line.state, ["cancel", "done"])

    def test_runtime_res_model_res_id_set(self):
        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "res_model": "res.partner",
                "res_id": self.test_partner.id,
            }
        )

        self.assertEqual(runtime.res_model, "res.partner")
        self.assertEqual(runtime.res_id, self.test_partner.id)

    def test_a_node_stores_its_canvas_position(self):
        action = self._create_action("Placed")

        action.write({"pos_x": 420, "pos_y": -180})

        self.assertEqual((action.pos_x, action.pos_y), (420, -180))

    def test_an_unplaced_node_reads_as_the_origin(self):
        action = self._create_action("Never placed")

        self.assertEqual((action.pos_x, action.pos_y), (0, 0))

    def test_copying_an_automation_carries_the_layout(self):
        action_a = self._create_action("A")
        action_b = self._create_action("B", predecessors=[action_a])
        action_a.write({"pos_x": 100, "pos_y": 50})
        action_b.write({"pos_x": 300, "pos_y": 50})

        copied = self.automation.copy()

        root = copied.action_server_ids.filtered(lambda a: not a.edge_in_ids)
        leaf = copied.action_server_ids - root
        self.assertEqual((root.pos_x, root.pos_y), (100, 50))
        self.assertEqual((leaf.pos_x, leaf.pos_y), (300, 50))

    def test_a_position_is_not_a_dependency(self):
        action_a = self._create_action("A")
        action_b = self._create_action("B", predecessors=[action_a])
        ordered_before = (action_a | action_b)._sorted_by_dependency()

        action_b.write({"pos_x": -900, "pos_y": -900})

        self.assertEqual(action_b._get_predecessors(), action_a)
        self.assertEqual((action_a | action_b)._sorted_by_dependency(), ordered_before)


class TestWorkflowDAGExecution(TransactionCase):
    def _link(self, source, target, condition="on_success", **kw):
        return link(self.env, source, target, condition, **kw)

    def setUp(self):
        super().setUp()
        self.Automation = self.env["automation.rule"]
        self.Action = self.env["ir.actions.server"]
        self.Runtime = self.env["automation.runtime"]
        self.model_partner = self.env["ir.model"]._get("res.partner")
        self.test_partner = self.env["res.partner"].create(
            {"name": "Exec Test Partner"}
        )

    def test_code_execution_writes_to_target_record(self):
        automation = self.Automation.create(
            {
                "name": "Email Setter",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
            }
        )
        action_a = self.Action.create(
            {
                "name": "Set Email",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'email': 'dag@example.com'})",
                "automation_rule_id": automation.id,
                "usage": "automation",
            }
        )
        action_phone = self.Action.create(
            {
                "name": "Set Phone",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'ref': '999-888-7777'})",
                "automation_rule_id": automation.id,
                "usage": "automation",
            }
        )
        self._link(action_a, action_phone)

        runtime = self.Runtime.create(
            {
                "automation_id": automation.id,
                "res_model": "res.partner",
                "res_id": self.test_partner.id,
            }
        )
        runtime.action_start()
        runtime.action_run_all()

        self.assertEqual(runtime.state, "done")
        self.test_partner.invalidate_recordset(["email", "ref"])
        self.assertEqual(self.test_partner.email, "dag@example.com")
        self.assertEqual(self.test_partner.ref, "999-888-7777")

    @mute_logger("odoo.addons.automation.models.automation_runtime_line")
    def test_error_in_action_marks_line_error(self):
        automation = self.Automation.create(
            {
                "name": "Failing Workflow",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
            }
        )
        action = self.Action.create(
            {
                "name": "Failing Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "raise Exception('deliberate test error')",
                "automation_rule_id": automation.id,
                "usage": "automation",
            }
        )

        runtime = self.Runtime.create(
            {
                "automation_id": automation.id,
                "res_model": "res.partner",
                "res_id": self.test_partner.id,
            }
        )
        runtime.action_start()

        line = runtime.line_ids.filtered(lambda l: l.action_id == action)

        self.assertFalse(line.action_execute(), "a failed step reports False")

        self.assertEqual(line.state, "error")
        self.assertIn("deliberate test error", line.error_message)
        self.assertEqual(runtime.state, "error", "the run itself is marked failed")

    @mute_logger("odoo.addons.automation.models.automation_runtime_line")
    def test_run_all_stops_the_batch_and_settles_stranded_lines_on_failure(self):
        automation = self.Automation.create(
            {
                "name": "Batch Failure Workflow",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
            }
        )
        action_fails = self.Action.create(
            {
                "name": "A-fails",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "raise Exception('deliberate test error')",
                "automation_rule_id": automation.id,
                "usage": "automation",
                "sequence": 1,
            }
        )
        action_sibling = self.Action.create(
            {
                "name": "B-sibling",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'B-ran'})",
                "automation_rule_id": automation.id,
                "usage": "automation",
                "sequence": 2,
            }
        )
        action_successor = self.Action.create(
            {
                "name": "C-depends-on-A",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'C-ran'})",
                "automation_rule_id": automation.id,
                "usage": "automation",
                "sequence": 3,
            }
        )
        self._link(action_fails, action_successor)

        runtime = self.Runtime.create(
            {
                "automation_id": automation.id,
                "res_model": "res.partner",
                "res_id": self.test_partner.id,
            }
        )
        runtime.action_start()
        runtime.action_run_all()

        line_fails = runtime.line_ids.filtered(lambda l: l.action_id == action_fails)
        line_sibling = runtime.line_ids.filtered(
            lambda l: l.action_id == action_sibling
        )
        line_successor = runtime.line_ids.filtered(
            lambda l: l.action_id == action_successor
        )

        self.assertEqual(runtime.state, "error")
        self.assertEqual(line_fails.state, "error")
        self.assertEqual(
            line_sibling.state,
            "error",
            "an independent sibling must not run once the batch has failed",
        )
        self.assertEqual(
            line_successor.state,
            "error",
            "a successor of the failed step must not be left waiting forever",
        )
        self.test_partner.invalidate_recordset(["comment"])
        self.assertFalse(
            self.test_partner.comment,
            "the sibling's side effect must not have happened",
        )


class TestWorkflowEdgeConditions(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Action = self.env["ir.actions.server"]
        self.model_partner = self.env["ir.model"]._get("res.partner")
        self.partner = self.env["res.partner"].create({"name": "Edge Partner"})
        self.automation = self.env["automation.rule"].create(
            {
                "name": "Edge Conditions",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
            }
        )

    def _action(self, name, code="pass"):
        return self.Action.create(
            {
                "name": name,
                "model_id": self.model_partner.id,
                "state": "code",
                "code": code,
                "automation_rule_id": self.automation.id,
                "usage": "automation",
            }
        )

    def _run(self):
        runtime = self.env["automation.runtime"].create(
            {
                "automation_id": self.automation.id,
                "res_model": "res.partner",
                "res_id": self.partner.id,
            }
        )
        runtime.action_start()
        runtime.action_run_all()
        return runtime

    def _line(self, runtime, action):
        return runtime.line_ids.filtered(lambda line: line.action_id == action)

    def test_an_edge_defaults_to_waiting_for_success(self):
        first, second = self._action("first"), self._action("second")

        edge = link(self.env, first, second)

        self.assertEqual(edge.condition, "on_success")
        self.assertEqual(edge.automation_rule_id, self.automation)

    def test_the_same_pair_cannot_be_connected_twice(self):
        first, second = self._action("first"), self._action("second")
        link(self.env, first, second)

        with self.assertRaises(UniqueViolation):
            link(self.env, first, second, condition="always")

    def test_an_edge_across_two_automations_is_refused(self):
        mine = self._action("mine")
        other_rule = self.env["automation.rule"].create(
            {
                "name": "Other",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
            }
        )
        foreign = self.Action.create(
            {
                "name": "foreign",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "pass",
                "automation_rule_id": other_rule.id,
                "usage": "automation",
            }
        )

        with self.assertRaises(ValidationError):
            link(self.env, foreign, mine)

    def test_an_expression_edge_without_an_expression_is_refused(self):
        first, second = self._action("first"), self._action("second")

        with self.assertRaises(ValidationError):
            link(self.env, first, second, condition="expression")

    @mute_logger("odoo.addons.automation.models.automation_runtime_line")
    def test_an_on_error_edge_releases_its_target_when_the_source_fails(self):
        failing = self._action("failing", code="raise ValueError('boom')")
        handler = self._action("handler", code="record.write({'comment': 'handled'})")
        link(self.env, failing, handler, condition="on_error")

        runtime = self._run()

        self.assertEqual(self._line(runtime, failing).state, "error")
        self.assertEqual(
            self._line(runtime, handler).state,
            "done",
            "the error handler must run, not sit waiting behind a failed step",
        )
        self.partner.invalidate_recordset(["comment"])
        self.assertIn("handled", self.partner.comment or "")

    @mute_logger("odoo.addons.automation.models.automation_runtime_line")
    def test_a_handled_failure_does_not_abort_the_run(self):
        failing = self._action("failing", code="raise ValueError('boom')")
        handler = self._action("handler")
        link(self.env, failing, handler, condition="on_error")

        runtime = self._run()

        self.assertNotEqual(runtime.state, "error")

    @mute_logger("odoo.addons.automation.models.automation_runtime_line")
    def test_an_unhandled_failure_still_aborts_the_run(self):
        failing = self._action("failing", code="raise ValueError('boom')")
        successor = self._action("successor")
        link(self.env, failing, successor)

        runtime = self._run()

        self.assertEqual(runtime.state, "error")
        self.assertNotEqual(self._line(runtime, successor).state, "done")

    @mute_logger("odoo.addons.automation.models.automation_runtime_line")
    def test_an_always_edge_releases_its_target_either_way(self):
        failing = self._action("failing", code="raise ValueError('boom')")
        cleanup = self._action("cleanup", code="record.write({'comment': 'cleaned'})")
        link(self.env, failing, cleanup, condition="always")

        runtime = self._run()

        self.assertEqual(self._line(runtime, cleanup).state, "done")

    def test_an_expression_edge_gates_on_its_expression(self):
        first = self._action("first")
        taken = self._action("taken", code="record.write({'comment': 'taken'})")
        skipped = self._action("skipped", code="record.write({'ref': 'skipped'})")
        link(self.env, first, taken, condition="expression", condition_expr="True")
        link(self.env, first, skipped, condition="expression", condition_expr="False")

        runtime = self._run()

        self.assertEqual(self._line(runtime, taken).state, "done")
        self.assertNotEqual(self._line(runtime, skipped).state, "done")

    def test_an_expression_edge_can_read_the_target_record(self):
        first = self._action("first")
        second = self._action("second")
        link(
            self.env,
            first,
            second,
            condition="expression",
            condition_expr="record.name == 'Edge Partner'",
        )

        runtime = self._run()

        self.assertEqual(self._line(runtime, second).state, "done")

    def test_a_run_keeps_the_conditions_it_started_with(self):
        first, second = self._action("first"), self._action("second")
        edge = link(self.env, first, second, condition="on_error")
        runtime = self.env["automation.runtime"].create(
            {
                "automation_id": self.automation.id,
                "res_model": "res.partner",
                "res_id": self.partner.id,
            }
        )
        runtime.action_start()

        edge.condition = "on_success"

        self.assertEqual(runtime.edge_ids.condition, "on_error")


class TestWorkflowGraphPayload(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Action = self.env["ir.actions.server"]
        self.model_partner = self.env["ir.model"]._get("res.partner")
        self.partner = self.env["res.partner"].create({"name": "Canvas Partner"})
        self.automation = self.env["automation.rule"].create(
            {
                "name": "Canvas",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
            }
        )
        self.first = self._action("first")
        self.second = self._action("second")
        self.edge = link(self.env, self.first, self.second, label="then")

    def _action(self, name, code="pass"):
        return self.Action.create(
            {
                "name": name,
                "model_id": self.model_partner.id,
                "state": "code",
                "code": code,
                "automation_rule_id": self.automation.id,
                "usage": "automation",
            }
        )

    def test_the_payload_carries_the_nodes_and_the_edges(self):
        graph = self.automation.get_workflow_graph()

        self.assertEqual(
            {node["id"] for node in graph["nodes"]}, {self.first.id, self.second.id}
        )
        self.assertEqual(len(graph["edges"]), 1)
        edge = graph["edges"][0]
        self.assertEqual(edge["source"], self.first.id)
        self.assertEqual(edge["target"], self.second.id)
        self.assertEqual(edge["condition"], "on_success")
        self.assertEqual(edge["label"], "then")

    def test_an_unplaced_graph_says_so(self):
        self.assertFalse(self.automation.get_workflow_graph()["is_positioned"])

        self.first.pos_x = 120

        self.assertTrue(self.automation.get_workflow_graph()["is_positioned"])

    def test_the_payload_carries_the_stored_coordinates(self):
        self.first.write({"pos_x": 40, "pos_y": -20})

        node = next(
            n
            for n in self.automation.get_workflow_graph()["nodes"]
            if n["id"] == self.first.id
        )

        self.assertEqual((node["pos_x"], node["pos_y"]), (40, -20))

    def test_without_a_runtime_no_step_carries_a_run_state(self):
        graph = self.automation.get_workflow_graph()

        self.assertIsNone(graph["runtime_id"])
        self.assertTrue(all(node["runtime_state"] is None for node in graph["nodes"]))

    def test_a_runtime_overlays_its_per_step_state(self):
        runtime = self.env["automation.runtime"].create(
            {
                "automation_id": self.automation.id,
                "res_model": "res.partner",
                "res_id": self.partner.id,
            }
        )
        runtime.action_start()
        runtime.action_run_all()

        graph = self.automation.get_workflow_graph(runtime_id=runtime.id)

        self.assertEqual(graph["runtime_id"], runtime.id)
        self.assertEqual(
            {node["id"]: node["runtime_state"] for node in graph["nodes"]},
            {self.first.id: "done", self.second.id: "done"},
        )

    def _make_runtime(self):
        return self.env["automation.runtime"].create(
            {
                "automation_id": self.automation.id,
                "res_model": "res.partner",
                "res_id": self.partner.id,
            }
        )

    def test_a_run_still_in_flight_is_overlaid_without_being_asked(self):
        runtime = self._make_runtime()
        runtime.action_start()

        graph = self.automation.get_workflow_graph()

        self.assertEqual(graph["runtime_id"], runtime.id)
        self.assertEqual(graph["runtime_state"], "in_progress")

    def test_a_finished_run_is_not_overlaid_on_the_editor(self):
        runtime = self._make_runtime()
        runtime.action_start()
        runtime.action_run_all()

        graph = self.automation.get_workflow_graph()

        # the canvas is also the DAG editor; a settled run must not colour it
        self.assertIsNone(graph["runtime_id"])
        self.assertTrue(all(node["runtime_state"] is None for node in graph["nodes"]))

    def test_the_definition_can_be_pinned_while_a_run_is_in_flight(self):
        runtime = self._make_runtime()
        runtime.action_start()

        graph = self.automation.get_workflow_graph(runtime_id=False)

        self.assertIsNone(graph["runtime_id"])
        self.assertTrue(all(node["runtime_state"] is None for node in graph["nodes"]))

    def test_a_settled_run_is_still_reachable_by_id(self):
        runtime = self._make_runtime()
        runtime.action_start()
        runtime.action_run_all()

        graph = self.automation.get_workflow_graph(runtime_id=runtime.id)

        self.assertEqual(graph["runtime_id"], runtime.id)

    def test_the_history_lists_the_ten_most_recent_runs_newest_first(self):
        created = [self._make_runtime() for _ in range(12)]

        runs = self.automation.get_workflow_graph()["runs"]

        self.assertEqual(len(runs), 10)
        self.assertEqual(
            [run["id"] for run in runs],
            [runtime.id for runtime in reversed(created)][:10],
        )

    def test_the_history_only_holds_this_automation_runs(self):
        mine = self._make_runtime()
        other = self.env["automation.rule"].create(
            {
                "name": "Other",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
            }
        )
        self.env["automation.runtime"].create(
            {
                "automation_id": other.id,
                "res_model": "res.partner",
                "res_id": self.partner.id,
            }
        )

        runs = self.automation.get_workflow_graph()["runs"]

        self.assertEqual([run["id"] for run in runs], [mine.id])

    def test_a_runtime_from_another_automation_is_ignored(self):
        other = self.env["automation.rule"].create(
            {
                "name": "Other",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
            }
        )
        foreign = self.env["automation.runtime"].create(
            {
                "automation_id": other.id,
                "res_model": "res.partner",
                "res_id": self.partner.id,
            }
        )

        graph = self.automation.get_workflow_graph(runtime_id=foreign.id)

        self.assertIsNone(graph["runtime_id"])
        self.assertTrue(all(node["runtime_state"] is None for node in graph["nodes"]))


@tagged("post_install", "-at_install")
class TestTriggerRunsAreRecorded(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Action = cls.env["ir.actions.server"]
        cls.model_partner = cls.env["ir.model"]._get("res.partner")

    def _automation(self, **kw):
        return self.env["automation.rule"].create(
            {
                "name": "Recorded",
                "model_id": self.model_partner.id,
                "trigger": "on_create",
                **kw,
            }
        )

    def _action(self, automation, name, code="pass"):
        return self.Action.create(
            {
                "name": name,
                "model_id": self.model_partner.id,
                "state": "code",
                "code": code,
                "automation_rule_id": automation.id,
                "usage": "automation",
            }
        )

    def _runtimes_of(self, automation):
        return self.env["automation.runtime"].search(
            [("automation_id", "=", automation.id)],
        )

    def test_a_trigger_records_a_run_when_asked(self):
        automation = self._automation(create_runtime_instance=True)
        first = self._action(automation, "first", "record.write({'comment': 'ran'})")
        second = self._action(automation, "second")
        link(self.env, first, second)

        partner = self.env["res.partner"].create({"name": "Recorded Partner"})

        runtimes = self._runtimes_of(automation)
        self.assertEqual(len(runtimes), 1)
        self.assertEqual(runtimes.res_id, partner.id)
        self.assertEqual(set(runtimes.line_ids.mapped("state")), {"done"})

    def test_a_trigger_records_nothing_by_default(self):
        automation = self._automation()
        self._action(automation, "only", "record.write({'comment': 'ran'})")

        partner = self.env["res.partner"].create({"name": "Unrecorded Partner"})

        self.assertFalse(self._runtimes_of(automation))
        self.assertIn("ran", partner.comment or "")

    def test_a_condition_is_honoured_on_a_trigger_path(self):
        automation = self._automation(create_runtime_instance=True)
        first = self._action(automation, "first")
        taken = self._action(automation, "taken", "record.write({'comment': 'taken'})")
        skipped = self._action(
            automation, "skipped", "record.write({'ref': 'skipped'})"
        )
        link(self.env, first, taken, condition="expression", condition_expr="True")
        link(self.env, first, skipped, condition="expression", condition_expr="False")

        partner = self.env["res.partner"].create({"name": "Branching Partner"})

        self.assertIn("taken", partner.comment or "")
        self.assertNotEqual(partner.ref, "skipped")

    def test_a_condition_that_could_not_be_honoured_is_refused(self):
        automation = self._automation()
        first = self._action(automation, "first")
        second = self._action(automation, "second")

        with self.assertRaises(ValidationError):
            link(self.env, first, second, condition="on_error")

    def test_switching_the_recording_off_under_a_condition_is_refused(self):
        automation = self._automation(create_runtime_instance=True)
        first = self._action(automation, "first")
        second = self._action(automation, "second")
        link(self.env, first, second, condition="on_error")

        with self.assertRaises(ValidationError):
            automation.create_runtime_instance = False

    def test_a_manual_automation_needs_no_flag_to_branch(self):
        automation = self._automation(trigger="on_hand")
        first = self._action(automation, "first")
        second = self._action(automation, "second")

        edge = link(self.env, first, second, condition="on_error")

        self.assertEqual(edge.condition, "on_error")


class TestWaitNode(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Action = self.env["ir.actions.server"]
        self.model_partner = self.env["ir.model"]._get("res.partner")
        self.partner = self.env["res.partner"].create({"name": "Waiting Partner"})
        self.automation = self.env["automation.rule"].create(
            {
                "name": "With a wait",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
            }
        )

    def _action(self, name, code="pass", **kw):
        return self.Action.create(
            {
                "name": name,
                "model_id": self.model_partner.id,
                "state": "code",
                "code": code,
                "automation_rule_id": self.automation.id,
                "usage": "automation",
                **kw,
            }
        )

    def _run(self):
        runtime = self.env["automation.runtime"].create(
            {
                "automation_id": self.automation.id,
                "res_model": "res.partner",
                "res_id": self.partner.id,
            }
        )
        runtime.action_start()
        runtime.action_run_all()
        return runtime

    def _line(self, runtime, action):
        return runtime.line_ids.filtered(lambda step: step.action_id == action)

    def test_a_wait_pauses_the_run_instead_of_finishing_it(self):
        first = self._action("first", "record.write({'comment': 'first'})")
        pause = self._action("pause", node_type="wait", wait_delay=2, wait_unit="hour")
        after = self._action("after", "record.write({'ref': 'after'})")
        link(self.env, first, pause)
        link(self.env, pause, after)

        runtime = self._run()

        self.assertEqual(runtime.state, "waiting_resume")
        self.assertEqual(self._line(runtime, pause).state, "paused")
        self.assertEqual(self._line(runtime, after).state, "waiting")
        self.partner.invalidate_recordset(["ref"])
        self.assertNotEqual(self.partner.ref, "after")

    def test_a_wait_records_when_it_resumes(self):
        pause = self._action("pause", node_type="wait", wait_delay=3, wait_unit="day")

        runtime = self._run()

        line = self._line(runtime, pause)
        self.assertTrue(line.date_resume)
        self.assertGreater(line.date_resume, self.env.cr.now())

    def test_the_cron_leaves_a_wait_that_is_not_due(self):
        pause = self._action("pause", node_type="wait", wait_delay=6, wait_unit="hour")
        after = self._action("after")
        link(self.env, pause, after)
        runtime = self._run()

        self.env["automation.runtime"]._resume_waiting_executions()

        self.assertEqual(runtime.state, "waiting_resume")
        self.assertEqual(self._line(runtime, pause).state, "paused")

    def test_the_cron_resumes_a_wait_that_is_due(self):
        pause = self._action("pause", node_type="wait", wait_delay=1, wait_unit="hour")
        after = self._action("after", "record.write({'ref': 'resumed'})")
        link(self.env, pause, after)
        runtime = self._run()
        self.assertEqual(runtime.state, "waiting_resume")

        self._line(runtime, pause).date_resume = self.env.cr.now() - relativedelta(
            hours=1,
        )
        self.env["automation.runtime"]._resume_waiting_executions()

        self.assertEqual(self._line(runtime, pause).state, "done")
        self.assertEqual(self._line(runtime, after).state, "done")
        self.assertEqual(runtime.state, "done")
        self.partner.invalidate_recordset(["ref"])
        self.assertEqual(self.partner.ref, "resumed")

    def test_a_wait_of_zero_is_refused(self):
        with self.assertRaises(ValidationError):
            self._action("pause", node_type="wait", wait_delay=0)

    def test_the_edge_model_already_provides_the_other_node_types(self):
        offered = dict(
            self.Action._fields["node_type"]._description_selection(self.env),
        )

        self.assertEqual(set(offered), {"action", "wait", "approval", "subflow"})


class TestApprovalNode(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Action = self.env["ir.actions.server"]
        self.model_partner = self.env["ir.model"]._get("res.partner")
        self.partner = self.env["res.partner"].create({"name": "Approval Partner"})
        self.approver = self.env["res.users"].create(
            {
                "name": "Approver",
                "login": "approver_wf",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.automation = self.env["automation.rule"].create(
            {
                "name": "Needs approval",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
            }
        )

    def _action(self, name, code="pass", **kw):
        return self.Action.create(
            {
                "name": name,
                "model_id": self.model_partner.id,
                "state": "code",
                "code": code,
                "automation_rule_id": self.automation.id,
                "usage": "automation",
                **kw,
            }
        )

    def _run(self):
        runtime = self.env["automation.runtime"].create(
            {
                "automation_id": self.automation.id,
                "res_model": "res.partner",
                "res_id": self.partner.id,
            }
        )
        runtime.action_start()
        runtime.action_run_all()
        return runtime

    def _line(self, runtime, action):
        return runtime.line_ids.filtered(lambda step: step.action_id == action)

    def _approval(self, name="approve"):
        return self._action(
            name,
            node_type="approval",
            approval_user_ids=[(6, 0, self.approver.ids)],
            approval_note="Please approve",
        )

    def test_an_approval_pauses_the_run_and_raises_an_activity(self):
        gate = self._approval()
        after = self._action("after", "record.write({'ref': 'approved'})")
        link(self.env, gate, after)

        runtime = self._run()

        line = self._line(runtime, gate)
        self.assertEqual(runtime.state, "waiting_resume")
        self.assertEqual(line.state, "paused")
        self.assertFalse(line.date_resume, "an approval waits on a person, not a clock")
        self.assertEqual(line.activity_ids.user_id, self.approver)
        self.assertEqual(line.activity_ids.summary, "Please approve")

    def test_marking_the_activity_done_resumes_the_run(self):
        gate = self._approval()
        after = self._action("after", "record.write({'ref': 'approved'})")
        link(self.env, gate, after)
        runtime = self._run()

        self._line(runtime, gate).activity_ids._action_done()

        self.assertEqual(self._line(runtime, gate).state, "done")
        self.assertEqual(self._line(runtime, after).state, "done")
        self.assertEqual(runtime.state, "done")
        self.partner.invalidate_recordset(["ref"])
        self.assertEqual(self.partner.ref, "approved")

    def test_one_approver_of_two_is_not_enough(self):
        second = self.env["res.users"].create(
            {
                "name": "Second",
                "login": "approver_wf_2",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        gate = self._action(
            "approve",
            node_type="approval",
            approval_user_ids=[(6, 0, (self.approver | second).ids)],
        )
        after = self._action("after")
        link(self.env, gate, after)
        runtime = self._run()
        line = self._line(runtime, gate)
        self.assertEqual(len(line.activity_ids), 2)

        line.activity_ids.filtered(lambda a: a.user_id == self.approver)._action_done()

        self.assertEqual(line.state, "paused")
        self.assertEqual(runtime.state, "waiting_resume")

    @mute_logger("odoo.addons.automation.models.automation_runtime_line")
    def test_a_refusal_routes_through_an_on_error_edge(self):
        gate = self._approval()
        rejected = self._action("rejected", "record.write({'comment': 'rejected'})")
        link(self.env, gate, rejected, condition="on_error")
        runtime = self._run()

        self._line(runtime, gate).action_refuse_approval("Not this time")

        self.assertEqual(self._line(runtime, gate).state, "error")
        self.assertEqual(self._line(runtime, rejected).state, "done")
        self.partner.invalidate_recordset(["comment"])
        self.assertIn("rejected", self.partner.comment or "")

    def test_an_approval_without_approvers_is_refused(self):
        with self.assertRaises(ValidationError):
            self._action("approve", node_type="approval")


class TestSubflowNode(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Action = self.env["ir.actions.server"]
        self.Rule = self.env["automation.rule"]
        self.model_partner = self.env["ir.model"]._get("res.partner")
        self.partner = self.env["res.partner"].create({"name": "Subflow Partner"})
        self.parent = self._rule("Parent")
        self.child = self._rule("Child")

    def _rule(self, name):
        return self.Rule.create(
            {
                "name": name,
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
            }
        )

    def _action(self, rule, name, code="pass", **kw):
        return self.Action.create(
            {
                "name": name,
                "model_id": self.model_partner.id,
                "state": "code",
                "code": code,
                "automation_rule_id": rule.id,
                "usage": "automation",
                **kw,
            }
        )

    def _run(self, rule=None):
        runtime = self.env["automation.runtime"].create(
            {
                "automation_id": (rule or self.parent).id,
                "res_model": "res.partner",
                "res_id": self.partner.id,
            }
        )
        runtime.action_start()
        runtime.action_run_all()
        return runtime

    def _line(self, runtime, action):
        return runtime.line_ids.filtered(lambda step: step.action_id == action)

    def test_a_subflow_runs_its_child_and_carries_on(self):
        self._action(self.child, "child step", "record.write({'comment': 'child ran'})")
        gate = self._action(
            self.parent,
            "call child",
            node_type="subflow",
            subflow_automation_id=self.child.id,
        )
        after = self._action(self.parent, "after", "record.write({'ref': 'after'})")
        link(self.env, gate, after)

        runtime = self._run()

        self.assertEqual(self._line(runtime, gate).state, "done")
        self.assertEqual(self._line(runtime, after).state, "done")
        self.assertEqual(runtime.state, "done")
        self.partner.invalidate_recordset(["comment", "ref"])
        self.assertIn("child ran", self.partner.comment or "")
        self.assertEqual(self.partner.ref, "after")

    def test_the_child_run_is_linked_from_the_step_that_started_it(self):
        self._action(self.child, "child step")
        gate = self._action(
            self.parent,
            "call child",
            node_type="subflow",
            subflow_automation_id=self.child.id,
        )

        runtime = self._run()

        child_runtime = self._line(runtime, gate).created_record_ref
        self.assertEqual(child_runtime._name, "automation.runtime")
        self.assertEqual(child_runtime.automation_id, self.child)
        self.assertEqual(child_runtime.parent_line_id, self._line(runtime, gate))

    def test_a_parent_waits_while_its_child_waits(self):
        self._action(
            self.child, "child pause", node_type="wait", wait_delay=4, wait_unit="hour"
        )
        gate = self._action(
            self.parent,
            "call child",
            node_type="subflow",
            subflow_automation_id=self.child.id,
        )
        after = self._action(self.parent, "after", "record.write({'ref': 'after'})")
        link(self.env, gate, after)

        runtime = self._run()

        self.assertEqual(runtime.state, "waiting_resume")
        self.assertEqual(self._line(runtime, gate).state, "paused")
        self.assertEqual(self._line(runtime, after).state, "waiting")

    @mute_logger("odoo.addons.automation.models.automation_runtime_line")
    def test_a_failing_child_routes_through_an_on_error_edge(self):
        self._action(self.child, "child fails", "raise ValueError('nope')")
        gate = self._action(
            self.parent,
            "call child",
            node_type="subflow",
            subflow_automation_id=self.child.id,
        )
        rescue = self._action(self.parent, "rescue", "record.write({'ref': 'rescued'})")
        link(self.env, gate, rescue, condition="on_error")

        runtime = self._run()

        self.assertEqual(self._line(runtime, gate).state, "error")
        self.assertEqual(self._line(runtime, rescue).state, "done")
        self.partner.invalidate_recordset(["ref"])
        self.assertEqual(self.partner.ref, "rescued")

    def test_a_subflow_naming_no_automation_is_refused(self):
        with self.assertRaises(ValidationError):
            self._action(self.parent, "call nothing", node_type="subflow")

    def test_a_subflow_cannot_contain_the_workflow_that_runs_it(self):
        self._action(
            self.child,
            "call back",
            node_type="subflow",
            subflow_automation_id=self.parent.id,
        )

        with self.assertRaises(ValidationError):
            self._action(
                self.parent,
                "call child",
                node_type="subflow",
                subflow_automation_id=self.child.id,
            )

    def test_a_subflow_cannot_be_itself(self):
        with self.assertRaises(ValidationError):
            self._action(
                self.parent,
                "call self",
                node_type="subflow",
                subflow_automation_id=self.parent.id,
            )


class TestWorkflowBusChannel(TransactionCase):
    def setUp(self):
        super().setUp()
        self.model_partner = self.env["ir.model"]._get("res.partner")
        self.partner = self.env["res.partner"].create({"name": "Bus Partner"})
        self.automation = self.env["automation.rule"].create(
            {
                "name": "Watched",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
            }
        )
        self.env["ir.actions.server"].create(
            {
                "name": "step",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "pass",
                "automation_rule_id": self.automation.id,
                "usage": "automation",
            }
        )

    def _channels(self, requested, user=None):
        websocket = self.env["ir.websocket"]
        if user:
            websocket = websocket.with_user(user)
        return websocket._get_bus_channels(list(requested))

    def test_the_string_channel_becomes_a_record_channel(self):
        channels = self._channels([f"automation.workflow/{self.automation.id}"])

        self.assertIn((self.automation, "WORKFLOW"), channels)
        self.assertNotIn(f"automation.workflow/{self.automation.id}", channels)

    def test_a_channel_for_an_unreadable_automation_is_dropped(self):
        plain = self.env["res.users"].create(
            {
                "name": "Plain",
                "login": "plain_bus_user",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )

        channels = self._channels(
            [f"automation.workflow/{self.automation.id}"],
            user=plain,
        )

        self.assertNotIn((self.automation, "WORKFLOW"), channels)
        self.assertNotIn(f"automation.workflow/{self.automation.id}", channels)

    def test_a_channel_for_a_nonexistent_automation_is_dropped(self):
        channels = self._channels(["automation.workflow/999999999"])

        self.assertFalse(
            [
                c
                for c in channels
                if not isinstance(c, str)
                and c
                and c[0:1]
                and getattr(c[0], "_name", None) == "automation.rule"
            ],
        )

    def test_a_malformed_channel_is_dropped_rather_than_raising(self):
        channels = self._channels(["automation.workflow/not-a-number"])

        self.assertNotIn("automation.workflow/not-a-number", channels)

    def test_other_channels_are_left_alone(self):
        channels = self._channels(["some.other/channel"])

        self.assertIn("some.other/channel", channels)

    def test_a_run_announces_itself_on_its_rule_channel(self):
        runtime = self.env["automation.runtime"].create(
            {
                "automation_id": self.automation.id,
                "res_model": "res.partner",
                "res_id": self.partner.id,
            }
        )

        runtime.action_start()
        runtime.action_run_all()
        self.env.cr.precommit.run()

        sent = self.env["bus.bus"].search([], order="id desc", limit=20)
        self.assertTrue(
            any("automation.workflow/update" in (row.message or "") for row in sent),
            "the run must announce itself so an open canvas can follow it",
        )


@tagged("post_install", "-at_install")
class TestRunSettlement(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Action = self.env["ir.actions.server"]
        self.model_partner = self.env["ir.model"]._get("res.partner")
        self.partner = self.env["res.partner"].create({"name": "Settle Partner"})
        self.automation = self.env["automation.rule"].create(
            {
                "name": "Settling",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
            }
        )

    def _action(self, name, code="pass", **kw):
        return self.Action.create(
            {
                "name": name,
                "model_id": self.model_partner.id,
                "state": "code",
                "code": code,
                "automation_rule_id": self.automation.id,
                "usage": "automation",
                **kw,
            }
        )

    def _run(self):
        runtime = self.env["automation.runtime"].create(
            {
                "automation_id": self.automation.id,
                "res_model": "res.partner",
                "res_id": self.partner.id,
            }
        )
        runtime.action_start()
        runtime.action_run_all()
        return runtime

    def _line(self, runtime, action):
        return runtime.line_ids.filtered(lambda step: step.action_id == action)

    @mute_logger("odoo.addons.automation.models.automation_runtime_line")
    def test_a_handled_failure_leaves_the_run_finished_not_hanging(self):
        failing = self._action("failing", "raise ValueError('boom')")
        handler = self._action("handler")
        link(self.env, failing, handler, condition="on_error")

        runtime = self._run()

        self.assertEqual(self._line(runtime, handler).state, "done")
        self.assertNotEqual(
            runtime.state,
            "in_progress",
            "a run with every line settled must not stay in progress",
        )
        self.assertEqual(runtime.state, "done")

    def test_pausing_one_branch_does_not_halt_the_others(self):
        root = self._action("root")
        pause = self._action("pause", node_type="wait", wait_delay=1)
        sibling = self._action("sibling", "record.write({'ref': 'sibling ran'})")
        link(self.env, root, pause)
        link(self.env, root, sibling)

        runtime = self._run()

        self.assertEqual(runtime.state, "waiting_resume")
        self.assertEqual(self._line(runtime, sibling).state, "done")
        self.partner.invalidate_recordset(["ref"])
        self.assertEqual(self.partner.ref, "sibling ran")

    def test_two_parallel_waits_both_resume(self):
        first = self._action("w1", node_type="wait", wait_delay=1)
        second = self._action("w2", node_type="wait", wait_delay=1)
        tail = self._action("tail")
        link(self.env, first, tail)
        link(self.env, second, tail)
        runtime = self._run()
        self.assertEqual(
            len(runtime.line_ids.filtered(lambda step: step.state == "paused")),
            2,
            "both waits must pause; one used to block the other from starting",
        )

        runtime.line_ids.filtered(
            lambda step: step.state == "paused",
        ).date_resume = self.env.cr.now()
        self.env["automation.runtime"]._resume_waiting_executions()

        self.assertEqual(runtime.state, "done")
        self.assertEqual(self._line(runtime, tail).state, "done")

    @mute_logger("odoo.addons.automation.models.automation_runtime_line")
    def test_a_failed_run_leaves_no_step_showing_as_paused(self):
        root = self._action("root")
        pause = self._action("pause", node_type="wait", wait_delay=1)
        failing = self._action("failing", "raise ValueError('boom')")
        link(self.env, root, pause)
        link(self.env, root, failing)

        runtime = self._run()

        self.assertEqual(runtime.state, "error")
        self.assertFalse(
            runtime.line_ids.filtered(lambda step: step.state == "paused"),
            "a finished run must leave nothing paused",
        )

    @mute_logger("odoo.addons.automation.models.automation_runtime_line")
    def test_deleting_an_approval_activity_is_not_approval(self):
        approver = self.env["res.users"].create(
            {
                "name": "Gone",
                "login": "approver_gone",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        gate = self._action(
            "gate",
            node_type="approval",
            approval_user_ids=[(6, 0, approver.ids)],
        )
        after = self._action("after", "record.write({'ref': 'APPROVED'})")
        link(self.env, gate, after)
        runtime = self._run()

        self._line(runtime, gate).activity_ids.unlink()

        self.assertEqual(self._line(runtime, gate).state, "error")
        self.partner.invalidate_recordset(["ref"])
        self.assertNotEqual(self.partner.ref, "APPROVED")
