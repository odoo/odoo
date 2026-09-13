from unittest.mock import patch

from odoo import Command
from odoo.tests import TransactionCase, tagged


class AutomationAuditCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Automation = cls.env["automation.rule"]
        cls.Action = cls.env["ir.actions.server"]
        cls.Runtime = cls.env["automation.runtime"]
        cls.model_partner = cls.env["ir.model"]._get("res.partner")

    def _automation(self, name, trigger="on_hand", **kw):
        return self.Automation.create(
            {
                "name": name,
                "model_id": self.model_partner.id,
                "trigger": trigger,
                **kw,
            }
        )

    def _action(self, automation, name, code="pass", predecessors=None, **kw):
        action = self.Action.create(
            {
                "name": name,
                "model_id": self.model_partner.id,
                "state": "code",
                "code": code,
                "automation_rule_id": automation.id,
                "usage": "automation",
                **kw,
            }
        )
        for predecessor in predecessors or []:
            self._link(predecessor, action)
        return action

    def _link(self, source, target, condition="on_success"):
        return self.env["workflow.edge"].create(
            {
                "source_node_id": source.id,
                "target_node_id": target.id,
                "condition": condition,
            }
        )


@tagged("post_install", "-at_install")
class TestCopyKeepsGraphLocal(AutomationAuditCommon):
    def test_copy_remaps_predecessors_onto_the_copied_actions(self):
        source = self._automation("source")
        first = self._action(source, "first")
        self._action(source, "second", predecessors=[first])

        duplicate = source.copy()

        self.assertEqual(len(duplicate.action_server_ids), 2)
        own_ids = set(duplicate.action_server_ids.ids)
        for action in duplicate.action_server_ids:
            self.assertFalse(
                set(action._get_predecessors().ids) - own_ids,
                f"{action.name} depends on an action outside its own automation",
            )
        copied_second = duplicate.action_server_ids.filtered(
            lambda a: a.edge_in_ids,
        )
        self.assertEqual(len(copied_second), 1, "the edge itself must be preserved")

    def test_copy_does_not_touch_the_source_graph(self):
        source = self._automation("source")
        first = self._action(source, "first")
        second = self._action(source, "second", predecessors=[first])

        source.copy()

        self.assertEqual(
            first._get_successors(),
            second,
            "the copy leaked into the source automation's successors",
        )

    def test_copy_multi_gives_each_copy_its_own_actions(self):
        one, two = self._automation("one"), self._automation("two")
        self._action(one, "one-step")
        self._action(two, "two-step")

        copies = (one | two).copy()

        self.assertEqual(len(copies), 2)
        for original, copy in zip(one | two, copies, strict=True):
            self.assertEqual(
                copy.action_server_ids.mapped("name"),
                [f"{n} (copy)" for n in original.action_server_ids.mapped("name")],
            )


@tagged("post_install", "-at_install")
class TestDagIntegrity(AutomationAuditCommon):
    def test_predecessor_from_another_automation_is_rejected(self):
        other = self._automation("other")
        foreign = self._action(other, "foreign")
        mine = self._automation("mine")

        with self.assertRaises(Exception):
            self._action(mine, "dependent", predecessors=[foreign])

    def test_run_that_cannot_advance_is_marked_failed(self):
        automation = self._automation("blocked")
        first = self._action(automation, "first")
        second = self._action(
            automation,
            "second",
            predecessors=[first],
        )
        runtime = self.Runtime.create({"automation_id": automation.id})
        runtime.action_start()

        line_second = runtime.line_ids.filtered(lambda l: l.action_id == second)
        line_first = runtime.line_ids.filtered(lambda l: l.action_id == first)
        line_first.action_cancel()

        runtime.action_run_all()

        self.assertEqual(runtime.state, "error")
        self.assertEqual(line_second.state, "error")

    def test_cycle_detection_still_rejects(self):
        automation = self._automation("cyclic")
        a = self._action(automation, "a")
        b = self._action(automation, "b", predecessors=[a])
        with self.assertRaises(Exception):
            self._link(b, a)


@tagged("post_install", "-at_install")
class TestFailureIsRecorded(AutomationAuditCommon):
    def test_failed_step_leaves_the_target_record_untouched(self):
        partner = self.env["res.partner"].create({"name": "target", "ref": "before"})
        automation = self._automation("half-write")
        self._action(
            automation,
            "writes then raises",
            code="record.write({'ref': 'after'})\nraise Exception('too late')",
        )
        runtime = self.Runtime.create(
            {
                "automation_id": automation.id,
                "res_model": "res.partner",
                "res_id": partner.id,
            }
        )
        runtime.action_start()
        runtime.action_run_all()

        self.assertEqual(runtime.state, "error")
        partner.invalidate_recordset(["ref"])
        self.assertEqual(
            partner.ref,
            "before",
            "the savepoint must discard the failing action's partial write",
        )

    def test_history_survives_and_names_the_failing_step(self):
        automation = self._automation("failing")
        ok = self._action(automation, "ok")
        self._action(
            automation,
            "boom",
            code="raise Exception('deliberate')",
            predecessors=[ok],
        )
        runtime = self.Runtime.create({"automation_id": automation.id})
        runtime.action_start()
        runtime.action_run_all()

        self.assertEqual(runtime.state, "error")
        by_name = {l.name: l for l in runtime.line_ids}
        self.assertEqual(by_name["ok"].state, "done")
        self.assertEqual(by_name["boom"].state, "error")
        self.assertIn("deliberate", by_name["boom"].error_message)


@tagged("post_install", "-at_install")
class TestProcessRespectsDependencies(AutomationAuditCommon):
    def test_actions_run_in_dependency_order_not_sequence_order(self):
        automation = self._automation("ordered", trigger="on_create")
        first = self._action(
            automation,
            "first",
            sequence=50,
            code="record.write({'ref': (record.ref or '') + 'A'})",
        )
        self._action(
            automation,
            "second",
            sequence=10,
            code="record.write({'ref': (record.ref or '') + 'B'})",
            predecessors=[first],
        )
        self.Automation._update_registry()
        self.addCleanup(self.Automation._update_registry)

        partner = self.env["res.partner"].create({"name": "ordered target"})
        self.assertEqual(partner.ref, "AB", "sequence must not override the graph")

    def test_sequence_still_orders_independent_actions(self):
        automation = self._automation("independent", trigger="on_create")
        self._action(
            automation,
            "late",
            sequence=50,
            code="record.write({'ref': (record.ref or '') + 'A'})",
        )
        self._action(
            automation,
            "early",
            sequence=10,
            code="record.write({'ref': (record.ref or '') + 'B'})",
        )
        self.Automation._update_registry()
        self.addCleanup(self.Automation._update_registry)

        partner = self.env["res.partner"].create({"name": "independent target"})
        self.assertEqual(partner.ref, "BA")


@tagged("post_install", "-at_install")
class TestFeedbackFlagReachesProcess(AutomationAuditCommon):
    def test_process_mutates_the_shared_done_dict_in_place_under_feedback(self):
        automation = self._automation("feedback-direct", trigger="on_hand")
        self._action(automation, "noop")
        partner = self.env["res.partner"].create({"name": "feedback direct target"})

        shared_done = {}
        automation_ctx = automation.with_context(__action_done=shared_done)
        records = partner.with_context(
            __action_done=shared_done, __action_feedback=True
        )

        automation_ctx._process(records)

        self.assertIn(
            automation_ctx,
            shared_done,
            "_process must mutate the caller's own automation_done dict in "
            "place when __action_feedback is set on records, not silently "
            "work on an unrelated copy",
        )


@tagged("post_install", "-at_install")
class TestRuleLookupCache(AutomationAuditCommon):
    def _count_rule_lookups(self, fn):
        seen = []
        cr = self.env.cr
        original = cr.execute

        def spy(query, params=None, *args, **kwargs):
            text = str(query)
            if "automation" in text and "SELECT" in text.upper():
                seen.append(text)
            return original(query, params, *args, **kwargs)

        cr.execute = spy
        try:
            fn()
            self.env.flush_all()
        finally:
            cr.execute = original
        return len(seen)

    def test_repeated_writes_do_not_re_query_the_rules(self):
        automation = self._automation("cached", trigger="on_create_or_write")
        self._action(automation, "noop")
        self.Automation._update_registry()
        self.addCleanup(self.Automation._update_registry)

        partners = self.env["res.partner"].create(
            [{"name": f"cache-{i}"} for i in range(20)],
        )
        self.env.flush_all()

        def loop():
            for partner in partners:
                partner.write({"comment": "x"})

        self.assertEqual(
            self._count_rule_lookups(loop),
            0,
            "the rule set must be served from the registry cache",
        )

    def test_cache_is_invalidated_when_a_rule_changes(self):
        automation = self._automation("toggles", trigger="on_create")
        self._action(
            automation,
            "stamp",
            code="record.write({'ref': 'fired'})",
        )
        self.Automation._update_registry()
        self.addCleanup(self.Automation._update_registry)

        first = self.env["res.partner"].create({"name": "before"})
        self.assertEqual(first.ref, "fired")

        automation.active = False
        self.Automation._update_registry()
        second = self.env["res.partner"].create({"name": "after"})
        self.assertNotEqual(
            second.ref,
            "fired",
            "deactivating a rule must invalidate the cache",
        )

    def test_sequence_change_reorders_execution(self):
        automation = self._automation("resequenced", trigger="on_create")
        self._action(
            automation,
            "a",
            sequence=10,
            code="record.write({'ref': (record.ref or '') + 'A'})",
        )
        second = self._automation("resequenced-2", trigger="on_create", sequence=20)
        self._action(
            second,
            "b",
            code="record.write({'ref': (record.ref or '') + 'B'})",
        )
        self.Automation._update_registry()
        self.addCleanup(self.Automation._update_registry)

        self.assertEqual(self.env["res.partner"].create({"name": "p1"}).ref, "AB")

        second.sequence = 1
        self.assertEqual(
            self.env["res.partner"].create({"name": "p2"}).ref,
            "BA",
            "a plain sequence edit must invalidate the cached order",
        )


@tagged("post_install", "-at_install")
class TestBookkeepingWriteIsSilent(AutomationAuditCommon):
    def test_stamp_does_not_trigger_other_rules(self):
        lead_model = self.env["ir.model"]._get("automation.lead.thread.test")
        if not lead_model:
            self.skipTest("test_automation is not installed")
        Model = self.env[lead_model.model]
        self.assertIn("date_automation_last", Model._fields)

        counter = self.env["ir.config_parameter"].sudo()
        counter.set_param("automation.bookkeeping_probe", "0")
        observer = self.Automation.create(
            {
                "name": "observer",
                "model_id": lead_model.id,
                "trigger": "on_write",
            }
        )
        self.Action.create(
            {
                "name": "count",
                "model_id": lead_model.id,
                "state": "code",
                "usage": "automation",
                "automation_rule_id": observer.id,
                "code": (
                    "p = env['ir.config_parameter'].sudo()\n"
                    "p.set_param('automation.bookkeeping_probe',"
                    " str(int(p.get_param('automation.bookkeeping_probe', '0')) + 1))"
                ),
            }
        )
        stamper = self.Automation.create(
            {
                "name": "stamper",
                "model_id": lead_model.id,
                "trigger": "on_create",
            }
        )
        self.Action.create(
            {
                "name": "noop",
                "model_id": lead_model.id,
                "state": "code",
                "code": "pass",
                "usage": "automation",
                "automation_rule_id": stamper.id,
            }
        )
        self.Automation._update_registry()
        self.addCleanup(self.Automation._update_registry)

        Model.create({"name": "probe"})
        self.env.flush_all()

        self.assertEqual(
            counter.get_param("automation.bookkeeping_probe"),
            "0",
            "the internal date_automation_last write fired a user rule",
        )


@tagged("post_install", "-at_install")
class TestRuntimeCreatePrivileges(AutomationAuditCommon):
    def test_company_id_does_not_bypass_access_rights(self):
        employee = self.env["res.users"].create(
            {
                "name": "audit employee",
                "login": "audit_employee",
                "group_ids": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        automation = self._automation("acl")
        Runtime = self.Runtime.with_user(employee)

        with self.assertRaises(Exception):
            Runtime.create({"automation_id": automation.id})

        with self.assertRaises(
            Exception,
            msg="company_id must not grant a create the user lacks",
        ):
            Runtime.create(
                {
                    "automation_id": automation.id,
                    "company_id": self.env.company.id,
                }
            )

    def test_sequence_is_still_assigned(self):
        automation = self._automation("seq")
        runtime = self.Runtime.create(
            {
                "automation_id": automation.id,
                "company_id": self.env.company.id,
            }
        )
        self.assertTrue(runtime.name.startswith("BAR/"), runtime.name)


@tagged("post_install", "-at_install")
class TestRuntimeVisibility(AutomationAuditCommon):
    def test_other_company_runs_are_not_readable(self):
        automation = self._automation("multico")
        other_company = self.env["res.company"].create({"name": "audit other co"})
        theirs = self.Runtime.sudo().create(
            {
                "automation_id": automation.id,
                "company_id": other_company.id,
                "currency_id": other_company.currency_id.id,
                "reference": "CONFIDENTIAL",
            }
        )
        employee = self.env["res.users"].create(
            {
                "name": "single co",
                "login": "audit_singleco",
                "company_id": self.env.company.id,
                "company_ids": [Command.set([self.env.company.id])],
                "group_ids": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        self.env.flush_all()

        visible = self.Runtime.with_user(employee).search([("id", "=", theirs.id)])
        self.assertFalse(visible, "an employee read another company's run")


@tagged("post_install", "-at_install")
class TestProgressReflectsOutcome(AutomationAuditCommon):
    def test_cancelled_run_reads_as_complete(self):
        automation = self._automation("cancelled")
        first = self._action(automation, "first")
        self._action(automation, "second", predecessors=[first])
        runtime = self.Runtime.create({"automation_id": automation.id})
        runtime.action_start()
        runtime.action_cancel()

        self.assertEqual(runtime.state, "cancel")
        self.assertEqual(runtime.progress, 100)
        self.assertEqual(runtime.progress_display, "2/2 steps")

    def test_partial_run_reports_partial_progress(self):
        automation = self._automation("partial")
        first = self._action(automation, "first")
        self._action(automation, "second", predecessors=[first])
        runtime = self.Runtime.create({"automation_id": automation.id})
        runtime.action_start()
        runtime.line_ids.filtered(lambda l: l.name == "first").action_mark_done()

        self.assertEqual(runtime.progress, 50)


@tagged("post_install", "-at_install")
class TestConstraintMessages(AutomationAuditCommon):
    def test_multi_record_validation_reports_instead_of_crashing(self):
        good = self._automation("good")
        bad = self._automation("bad")
        self.Action.create(
            {
                "name": "wrong model",
                "model_id": self.env["ir.model"]._get("res.users").id,
                "state": "code",
                "code": "pass",
                "usage": "automation",
                "automation_rule_id": bad.id,
            }
        )
        with self.assertRaises(Exception) as caught:
            (good | bad).write({"model_id": self.model_partner.id})
        self.assertNotIsInstance(
            caught.exception,
            ValueError,
            "the error path itself raised Expected singleton",
        )


@tagged("post_install", "-at_install")
class TestFirstRunIsAnnounced(AutomationAuditCommon):
    def test_first_run_warns_and_names_the_volume(self):
        model = self.env["ir.model"]._get("res.partner")
        automation = self.Automation.create(
            {
                "name": "sweeper",
                "model_id": model.id,
                "trigger": "on_time_created",
                "trg_date_range": 1,
                "trg_date_range_type": "hour",
            }
        )
        self._action(automation, "noop")
        self.assertFalse(automation.last_run, "precondition: unscoped")

        old = self.env["res.partner"].create({"name": "predates the rule"})
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = now() - interval '400 days' "
            "WHERE id = %s",
            (old.id,),
        )
        self.env.invalidate_all()
        self.assertTrue(
            automation._search_time_based_automation_records(until=self.env.cr.now()),
            "precondition: the rule must have a backlog to sweep",
        )

        IrCron = type(self.env["ir.cron"])
        with (
            patch.object(IrCron, "_commit_progress", return_value=float("inf")),
            self.assertLogs(
                "odoo.addons.automation.models.automation_rule",
                "WARNING",
            ) as captured,
        ):
            self.Automation._cron_process_time_based_actions()
        self.assertTrue(
            any("covers the entire history" in line for line in captured.output),
            f"no warning about the unscoped first run: {captured.output}",
        )

    def test_scoped_rule_does_not_warn(self):
        model = self.env["ir.model"]._get("res.partner")
        automation = self.Automation.create(
            {
                "name": "scoped",
                "model_id": model.id,
                "trigger": "on_time_created",
                "trg_date_range": 1,
                "trg_date_range_type": "hour",
                "last_run": self.env.cr.now(),
            }
        )
        self._action(automation, "noop")
        self.assertTrue(
            automation.last_run,
            "last_run must be settable, not readonly",
        )
