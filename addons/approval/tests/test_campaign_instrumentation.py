"""The campaign instrumentation's own invariants -- TEMPORARY, goes with the campaign.

`machine_doc_v1/conventions.md`, "Campaign Instrumentation", states three things a
reader is asked to rely on. Each is a test here, because a census nobody checks
drifts into a ranked work list that sends a session after noise:

* a call that SUCCEEDS logs no refusal, so `odoo.approval.refusal` aggregated over a
  corpus is what the engine actually turns away rather than what it asked itself;
* every `raise` of a user-facing error reports a refusal, so that census is complete
  and not a biased sample of the sites somebody remembered;
* every method `CALL_TRACES` names still exists, so a rename cannot silently unwrap
  an entry point and leave a target printing nothing.

THE WRAPPED LAYER DOES NOT EXIST DURING AT-INSTALL TESTS. Odoo calls
`register_model_hooks()` -- and so `base._register_hook`, and so
`approval_trace.instrument` -- after every module has loaded, which is after the
at-install phase has run. An at-install test therefore sees the hand-placed events
and no spans at all, which is why the two classes that depend on wrapping are
`post_install`. It is also worth knowing when reading a measurement: a suite run
that reports no spans may be reporting the phase, not the code.
"""

import ast
import logging
import re
from pathlib import Path
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import ApprovalCommon
from odoo.addons.approval.models import approval_trace as trace

RAISE = re.compile(r"^\s*raise (UserError|ValidationError|AccessError)\(")
REFUSAL_EVENT = re.compile(r"trace\.REFUSAL\.event\(")

# A raise reached by several callers for several reasons reports at each CALLER
# instead, so one event cannot collapse four causes into one census row.
REPORTED_BY_ITS_CALLERS = frozenset({"_raise_not_assigned_approver"})

# A `refusal` line whose own method raises nothing. The census's oracle survives it
# only because the flow it reports on refuses somewhere else.
REFUSAL_WITHOUT_A_RAISE = frozenset()

# An extension point left empty by OMISSION, not by design: there the campaign line IS
# the report that nobody implemented it, so it may be the whole body.
EMPTY_BY_OMISSION = frozenset(
    {
        "_raise_approval_category_not_configured",
        "_raise_approval_category_not_matched",
    }
)

ADDON = Path(__file__).resolve().parents[1]


def _source_files():
    for folder in ("models", "wizards", "reports"):
        yield from sorted((ADDON / folder).glob("*.py"))


class TestCampaignRefusalCensus(ApprovalCommon):
    def test_a_green_flow_logs_no_refusal(self):
        """The null control: nothing the engine turns away happens here, so the
        refusal target must stay silent. It did not, once: a guard answering a
        question through a refusing form filed a refusal for every caller that
        merely asked."""
        category = self._make_category(
            name="Census Green",
            approvers=[self.approver_1, self.approver_2],
        )
        with self.assertNoLogs("odoo.approval.refusal", level="DEBUG"):
            request = self._prepare_request(category)
            request.with_user(self.approver_1).action_approve()
            request.with_user(self.approver_2).action_approve()
            self.assertEqual(request.state, "approved")
            request.with_user(self.approver_2).action_withdraw()
            self.assertEqual(request.state, "pending")
            request.with_user(self.approver_2).action_approve()
            self.assertEqual(request.state, "approved")
            request.with_user(self.manager_user).action_reset_to_draft()
            self.assertEqual(request.state, "new")
            request.action_confirm()

    def test_a_refused_call_names_its_own_kind(self):
        category = self._make_category(name="Census Red", approvers=[self.approver_1])
        request = self._prepare_request(category)
        with self.assertLogs("odoo.approval.refusal", level="DEBUG") as captured:
            with self.assertRaises(UserError):
                request.action_confirm()
        self.assertTrue(
            any("confirm_not_draft" in line for line in captured.output),
            captured.output,
        )
        self.assertTrue(
            any(f"request={request.id}" in line for line in captured.output),
            captured.output,
        )

    def test_every_raise_reports_a_refusal(self):
        """Completeness, so the ranked census is not a sample of what was easy to
        instrument. A new guard either reports its own kind or is named in
        REPORTED_BY_ITS_CALLERS with the callers that report for it."""
        unreported = []
        for path in _source_files():
            lines = path.read_text().split("\n")
            for index, line in enumerate(lines):
                if not RAISE.match(line):
                    continue
                if REFUSAL_EVENT.search("\n".join(lines[max(0, index - 14) : index])):
                    continue
                owner = next(
                    (
                        match.group(1)
                        for earlier in range(index, -1, -1)
                        if (match := re.match(r"^    def (\w+)", lines[earlier]))
                    ),
                    "?",
                )
                if owner in REPORTED_BY_ITS_CALLERS:
                    continue
                unreported.append(f"{path.name}:{index + 1} {owner}")
        self.assertEqual(unreported, [], "\n".join(unreported))

    def test_no_call_site_reads_the_model_name_attribute(self):
        """A campaign line may not reach the model's own name attribute through
        `self`, and this is a ratchet because the rule was written down and then
        broken twice.

        `tooling/architecture/mixin_coupling_check.py` greps that exact token over
        `odoo/addons` and `addons` for the metadata fan-in census, which is stated in a
        docstring in CORE -- so a campaign call site that reads it moves a figure that
        would have to move back when the campaign is removed. It also cost a peer
        session an afternoon: the resulting 461-against-445 went into CLAUDE.md §4 as an
        ORM defect that did not exist.

        THE TOKEN IS BUILT RATHER THAN WRITTEN HERE, and that is not cuteness: the
        census scans `tests/` too, so a guard that spells out what it counts adds to
        the count. Writing it out three times in this file moved the figure by three
        and cost a second misattribution, this time of my own work to somebody else.

        The renderer prints a recordset, so `record=self` says more and costs nothing.
        Seven reads predate the campaign; that is the ceiling.
        """
        needle = "self." + "_name"
        reads = {path.name: path.read_text().count(needle) for path in _source_files()}
        total = sum(reads.values())
        self.assertLessEqual(
            total,
            7,
            f"{total - 7} campaign call site(s) reach the model name through self: "
            f"{ {name: n for name, n in reads.items() if n} }. "
            "Pass the record instead: `record=self` renders model#id.",
        )

    def test_the_refusal_target_carries_only_refusals(self):
        """`refusal` is the one target with an oracle -- a green flow logs zero -- and
        that only holds while every line on it precedes a `raise`.

        A method that raises through a `_raise_*` helper counts as raising: three sites
        do that on purpose, so several callers can each report their own kind while one
        helper holds the message.

        This was broken while the test was being written: a `_compute_usage_count` on
        `approval.refusal.reason` reported its `_read_group` on `REFUSAL` because the
        MODEL is about refusal reasons. The target is about refusals, and a compute that
        runs on any form view would have put a line on the one target whose value is
        that it stays empty. It also found an older one: `_parse_domain_or_warn`
        reported an unparseable domain as a refusal, where nothing is refused -- the
        domain is treated as matching nothing and the flow carries on. That is the
        `degraded` class, `_parse_domain` already says so on that target, and the line
        was deleted rather than moved.
        """
        misplaced = []
        for path in _source_files():
            tree = ast.parse(path.read_text())
            for holder in ast.walk(tree):
                if not isinstance(holder, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                raises = any(
                    isinstance(node, ast.Raise)
                    or (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr.startswith("_raise")
                    )
                    for node in ast.walk(holder)
                )
                for node in ast.walk(holder):
                    if not isinstance(node, ast.Call):
                        continue
                    target = node.func
                    if not (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Attribute)
                        and target.value.attr == "REFUSAL"
                    ):
                        continue
                    if raises or holder.name in REFUSAL_WITHOUT_A_RAISE:
                        continue
                    misplaced.append(f"{path.name}:{node.lineno} {holder.name}")
        self.assertEqual(
            misplaced,
            [],
            "these lines are on the `refusal` target inside a method that raises "
            f"nothing: {misplaced}. A question that is answered rather than declined "
            "belongs on `access`; anything else belongs on its own concern's target.",
        )

    def test_no_campaign_line_is_the_only_statement_of_a_body(self):
        """A campaign line is DELETED at the end of the campaign, so a body that holds
        nothing else becomes a syntax error the moment it is.

        `mixin.approval.state.sync._check_approval_sync_policy` is the shape:
        `def ...: return`, an adopter's veto point that vetoes nothing by default.
        Instrument the CALL SITE, which survives the deletion. A hook that is empty by
        OMISSION rather than by design (`_raise_approval_category_not_configured`) is
        the exception -- there the line is the report that nobody implemented it, and
        it is named below.
        """
        traps = []
        for path in _source_files():
            tree = ast.parse(path.read_text())
            for holder in ast.walk(tree):
                if not isinstance(holder, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                body = [
                    node
                    for node in holder.body
                    if not (
                        isinstance(node, ast.Expr)
                        and isinstance(node.value, ast.Constant)
                    )
                ]
                if len(body) != 1 or not isinstance(body[0], ast.Expr):
                    continue
                call = body[0].value
                if not (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Attribute)
                    and isinstance(call.func.value.value, ast.Name)
                    and call.func.value.value.id == "trace"
                ):
                    continue
                if holder.name in EMPTY_BY_OMISSION:
                    continue
                traps.append(f"{path.name}:{holder.lineno} {holder.name}")
        self.assertEqual(
            traps,
            [],
            "removing the campaign would leave these bodies empty: "
            f"{traps}. Instrument the call site instead.",
        )

    def test_the_reported_kinds_are_distinct(self):
        """Two sites sharing a kind are one census row, which hides one of them."""
        kinds = []
        for path in _source_files():
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                target = node.func
                if not (
                    isinstance(target, ast.Attribute)
                    and target.attr == "event"
                    and isinstance(target.value, ast.Attribute)
                    and target.value.attr == "REFUSAL"
                ):
                    continue
                first = node.args[0]
                if isinstance(first, ast.Constant):
                    kinds.append(first.value)
        duplicated = sorted({kind for kind in kinds if kinds.count(kind) > 1})
        self.assertEqual(duplicated, [], f"kinds used twice: {duplicated}")


class TestCampaignSwallowedFailures(ApprovalCommon):
    """The class no refusal census can see: a failure the engine swallows.

    A peer campaign on another repo found fourteen of these -- paths that raise
    something the reporting macro never covered, two of them reachable on its read
    path and silent on every target. They are not refusals (nothing was turned away)
    and not questions (nothing was asked): the engine gave up on something and
    carried on, which is the shape a session debugging "why did nothing happen?"
    cannot find. So they are enumerated rather than measured.
    """

    #: handler line -> why saying nothing is right there
    ALLOWED_TO_STAY_SILENT = {
        "approval_trace.py": "the renderer degrades to <unrenderable>, which IS the report",
    }

    def test_no_handler_swallows_a_failure_without_a_word(self):
        offenders = []
        for path in _source_files():
            source = path.read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Try):
                    continue
                for handler in node.handlers:
                    segment = ast.get_source_segment(source, handler) or ""
                    speaks = (
                        any(isinstance(n, ast.Raise) for n in ast.walk(handler))
                        or "_logger." in segment
                        or "trace." in segment
                    )
                    if speaks or path.name in self.ALLOWED_TO_STAY_SILENT:
                        continue
                    caught = ast.unparse(handler.type) if handler.type else "everything"
                    offenders.append(f"{path.name}:{handler.lineno} catches {caught}")
        self.assertEqual(offenders, [], "\n".join(offenders))


@tagged("post_install", "-at_install")
class TestCampaignMeasurement(ApprovalCommon):
    """The performance switch, which is deliberately NOT one of the printing ones.

    A run with every target at DEBUG is not the run whose timings anybody wants:
    the logging dominates. So `APPROVAL_TRACE_SLOW_MS` and `APPROVAL_TRACE_NPLUSONE`
    turn measurement on while the targets stay quiet, and these tests pin that the
    two switches are independent in both directions.
    """

    def setUp(self):
        super().setUp()
        trace.forget_perf_ledger()
        self.addCleanup(trace.forget_perf_ledger)

    def _shut_printing(self, target):
        """Pin one target's level to WARNING for this test, whatever the run asked for.

        Two of these tests are about what happens while nothing is printing, and the
        suite is MEANT to be runnable under `--log-handler odoo.approval:DEBUG` --
        that is how the formatting of every call site gets exercised. A test whose
        premise is a log level has to set that level itself, or it fails on the
        operator's flag rather than on the code.
        """
        logger = logging.getLogger(f"{trace.LOG_ROOT}.{target.name}")
        before = logger.level
        logger.setLevel(logging.WARNING)
        self.addCleanup(logger.setLevel, before)

    def test_a_span_is_timed_while_every_target_is_silent(self):
        """NOT written with `assertNoLogs`, and that is the point.

        `assertNoLogs("odoo.approval", "DEBUG")` sets that logger to DEBUG for the
        duration, which is the very switch under test: it makes the span print and
        then fails on the line it caused. A test that asserts silence on the logger
        whose level controls the behaviour has changed the behaviour. The printing
        switch is `Target.on()`, so ask it.
        """
        self._shut_printing(trace.LIFECYCLE)
        self.assertFalse(trace.LIFECYCLE.on(), "the printing switch starts shut")
        with patch.object(trace, "_WATCH_NPLUSONE", True):
            with trace.LIFECYCLE.span("measured_but_not_printed", n=3) as span:
                span["sql"] = 1
            self.assertFalse(trace.LIFECYCLE.on(), "and stays shut while measuring")
        ledger = {row.call: row for row in trace.perf_ledger()}
        self.assertIn("measured_but_not_printed", ledger)
        self.assertEqual(ledger["measured_but_not_printed"].rows, 3)
        self.assertEqual(ledger["measured_but_not_printed"].sql, 1)

    def test_nothing_is_timed_when_neither_switch_is_open(self):
        # `accounting()` has THREE inputs -- the two variables and `perf` at DEBUG --
        # and a run under `--log-handler odoo.approval:DEBUG` opens the third by
        # inheritance. All three have to be shut to test the closed case.
        self._shut_printing(trace.LIFECYCLE)
        self._shut_printing(trace.PERF)
        with (
            patch.object(trace, "_WATCH_NPLUSONE", False),
            patch.object(trace, "_SLOW_MS", None),
        ):
            with trace.LIFECYCLE.span("not_measured_at_all", n=3):
                pass
        self.assertEqual(trace.perf_ledger(), [])

    def test_a_query_per_record_is_named_on_the_perf_target(self):
        with (
            patch.object(trace, "_WATCH_NPLUSONE", True),
            self.assertLogs("odoo.approval.perf", level="INFO") as captured,
        ):
            with trace.ROUTING.span("one_query_each", n=10) as span:
                span["sql"] = 20
        self.assertTrue(
            any(
                "n_plus_one" in line and "per_row=2" in line for line in captured.output
            ),
            captured.output,
        )

    def test_a_batch_too_small_to_show_growth_is_not_named(self):
        with patch.object(trace, "_WATCH_NPLUSONE", True):
            with self.assertNoLogs("odoo.approval.perf", level="INFO"):
                with trace.ROUTING.span("two_rows", n=2) as span:
                    span["sql"] = 9

    def test_a_slow_call_is_named_and_a_fast_one_is_not(self):
        with patch.object(trace, "_SLOW_MS", 0.0):
            with self.assertLogs("odoo.approval.perf", level="INFO") as captured:
                with trace.LIFECYCLE.span("always_slow", n=1) as span:
                    span["sql"] = 0
        self.assertTrue(
            any("slow" in line for line in captured.output), captured.output
        )
        with patch.object(trace, "_SLOW_MS", 60_000.0):
            with self.assertNoLogs("odoo.approval.perf", level="INFO"):
                with trace.LIFECYCLE.span("never_slow", n=1) as span:
                    span["sql"] = 0

    def test_annotate_reports_the_work_the_batch_size_hides(self):
        """`_sync_approvers` is called with one request and writes forty rows; the
        query count has to be read against the forty."""
        with patch.object(trace, "_WATCH_NPLUSONE", True):
            with self.assertLogs("odoo.approval.perf", level="INFO") as captured:
                with trace.ROUTING.span("one_request_many_rows", n=1) as span:
                    trace.annotate(work=40)
                    span["sql"] = 40
        row = {r.call: r for r in trace.perf_ledger()}["one_request_many_rows"]
        self.assertEqual(row.rows, 40)
        self.assertEqual(row.sql_per_row, 1)
        self.assertTrue(any("n_plus_one" in line for line in captured.output))

    def test_annotate_outside_a_span_is_a_no_op(self):
        trace.annotate(work=7)
        self.assertEqual(trace.perf_ledger(), [])

    def test_the_ledger_reports_the_rates_a_reader_needs(self):
        with patch.object(trace, "_WATCH_NPLUSONE", True):
            for sql in (2, 4):
                with trace.STEPS.span("summed", n=5) as span:
                    span["sql"] = sql
        row = {r.call: r for r in trace.perf_ledger()}["summed"]
        self.assertEqual((row.calls, row.rows, row.sql), (2, 10, 6))
        self.assertEqual(row.sql_per_call, 3)
        self.assertEqual(row.sql_per_row, 0.6)
        self.assertGreater(row.total_ms, 0)
        self.assertLessEqual(row.worst_ms, row.total_ms)

    def test_a_wrapped_entry_point_is_timed_with_the_targets_quiet(self):
        """The wrapper short-circuits on `target.on()`; the switch has to reopen it."""
        category = self._make_category(
            name="Measured Confirm", approvers=[self.approver_1]
        )
        with patch.object(trace, "_WATCH_NPLUSONE", True):
            self._prepare_request(category)
        calls = {row.call for row in trace.perf_ledger()}
        self.assertIn("approval.request.action_confirm", calls)
        self.assertIn("approval.request._sync_approvers", calls)


@tagged("post_install", "-at_install")
class TestCampaignCallTraces(ApprovalCommon):
    def test_every_wrapped_method_exists(self):
        missing = [
            f"{model_name}.{method}"
            for model_name, methods in trace.CALL_TRACES.items()
            for method in methods
            if model_name in self.env.registry
            and not hasattr(self.env.registry[model_name], method)
        ]
        self.assertEqual(missing, [], "\n".join(missing))

    def test_every_wrapped_model_is_concrete(self):
        """An abstract model's registry class is inherited by nobody, so wrapping it
        instruments nothing: the mixins are instrumented by hand instead."""
        abstract = [
            model_name
            for model_name in trace.CALL_TRACES
            if model_name in self.env.registry and self.env[model_name]._abstract
        ]
        self.assertEqual(abstract, [], "\n".join(abstract))

    def test_every_target_name_is_declared(self):
        unknown = sorted(
            {
                target
                for methods in trace.CALL_TRACES.values()
                for target in methods.values()
            }
            - set(trace._BY_NAME)
        )
        self.assertEqual(unknown, [], "\n".join(unknown))
