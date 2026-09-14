import logging
import unittest

from odoo.libs.debug_log import (
    _DISABLED_SPAN,
    CHANNELS,
    ROOT,
    DebugLog,
    debug_scope,
    format_event,
)


class _FakeCursor:
    def __init__(self) -> None:
        self.sql_log_count = 0
        self.sql_statement_count = 0


class _FakeEnv:
    def __init__(self, cr: _FakeCursor) -> None:
        self.cr = cr


class _FakeRecords:
    _name = "res.partner"

    def __init__(self, ids: tuple, cr: _FakeCursor) -> None:
        self._ids = ids
        self.env = _FakeEnv(cr)


class TestDebugScope(unittest.TestCase):
    def test_addon_layer_segment_is_dropped(self):
        self.assertEqual(
            debug_scope("odoo.addons.base.models.ir_attachment"), "base.ir_attachment"
        )
        self.assertEqual(
            debug_scope("odoo.addons.base.wizards.base_module_update"),
            "base.base_module_update",
        )
        self.assertEqual(
            debug_scope("odoo.addons.base.models.assetsbundle.bundle"),
            "base.assetsbundle.bundle",
        )

    def test_core_keeps_its_package_path(self):
        self.assertEqual(debug_scope("odoo.orm.models.base"), "orm.models.base")
        self.assertEqual(debug_scope("odoo.modules.loading"), "modules.loading")

    def test_foreign_module_is_left_alone(self):
        self.assertEqual(debug_scope("somepkg.thing"), "somepkg.thing")


class TestFormatEvent(unittest.TestCase):
    def test_plain_values_are_bare_and_spaced_strings_are_quoted(self):
        line = format_event(
            "read", {"model": "res.partner", "name": "a b", "n": 3, "f": 1.23456}
        )
        self.assertEqual(line, "event=read model=res.partner name='a b' n=3 f=1.235")

    def test_empty_string_is_quoted_so_the_key_keeps_a_value(self):
        self.assertEqual(format_event("x", {"s": ""}), "event=x s=''")

    def test_recordset_prints_its_model_and_at_most_eight_ids(self):
        cr = _FakeCursor()
        few = _FakeRecords((1, 2), cr)
        many = _FakeRecords(tuple(range(1, 13)), cr)
        none = _FakeRecords((), cr)
        self.assertEqual(
            format_event("x", {"a": few, "b": many, "c": none}),
            "event=x a=res.partner(1,2) b=res.partner(1,2,3,4,5,6,7,8,+4) "
            "c=res.partner()",
        )

    def test_a_model_class_is_not_a_recordset(self):
        self.assertEqual(
            format_event("x", {"cls": _FakeRecords}), f"event=x cls={_FakeRecords}"
        )


class TestDebugLog(unittest.TestCase):
    def setUp(self):
        self.log = DebugLog("odoo.addons.base.models.ir_attachment")
        self.root = logging.getLogger(ROOT)
        self.saved_level = self.root.level
        self.root.setLevel(logging.NOTSET)
        for channel in CHANNELS:
            logging.getLogger(f"{ROOT}.{channel}").setLevel(logging.NOTSET)

    def tearDown(self):
        self.root.setLevel(self.saved_level)

    def test_loggers_are_named_root_channel_scope(self):
        self.assertEqual(self.log.scope, "base.ir_attachment")
        for channel in CHANNELS:
            logger = getattr(self.log, channel).logger
            self.assertEqual(logger.name, f"{ROOT}.{channel}.base.ir_attachment")

    def test_line_channel_emits_only_when_enabled(self):
        logging.getLogger(f"{ROOT}.logic").setLevel(logging.INFO)
        with self.assertNoLogs(self.root, logging.DEBUG):
            self.log.logic("noop", a=1)
        logging.getLogger(f"{ROOT}.logic").setLevel(logging.NOTSET)
        with self.assertLogs(f"{ROOT}.logic", logging.DEBUG) as captured:
            self.log.logic("hit", model="res.partner", ids=[1, 2])
        self.assertEqual(
            captured.output,
            [
                f"DEBUG:{ROOT}.logic.base.ir_attachment:event=hit model=res.partner ids=[1, 2]"
            ],
        )

    def test_perf_span_is_a_shared_noop_when_disabled(self):
        self.root.setLevel(logging.INFO)
        span = self.log.perf("read", cr=_FakeCursor())
        self.assertIs(span, _DISABLED_SPAN)
        with span as inner:
            inner.set(rows=1)

    def test_perf_span_reports_ms_queries_and_extra_fields(self):
        cr = _FakeCursor()
        with self.assertLogs(f"{ROOT}.perf", logging.DEBUG) as captured:
            with self.log.perf("read", cr=cr, model="res.partner") as span:
                cr.sql_statement_count += 3
                span.set(rows=7)
        (line,) = captured.output
        self.assertIn("event=read model=res.partner rows=7 ms=", line)
        self.assertTrue(line.endswith(" queries=3"))

    def test_perf_span_counts_round_trips_not_rows(self):
        cr = _FakeCursor()
        with self.assertLogs(f"{ROOT}.perf", logging.DEBUG) as captured:
            with self.log.perf("insert", cr=cr):
                cr.sql_statement_count += 1
                cr.sql_log_count += 500
        (line,) = captured.output
        self.assertTrue(line.endswith(" queries=1"))

    def test_timed_names_the_method_and_reads_receiver_and_cursor(self):
        cr = _FakeCursor()

        class Model:
            _name = "res.partner"

            def __init__(self) -> None:
                self._ids = (4, 5)
                self.env = _FakeEnv(cr)

            @self.log.perf.timed
            def action_post(self, value):
                cr.sql_statement_count += 2
                return value * 2

        with self.assertLogs(f"{ROOT}.perf", logging.DEBUG) as captured:
            self.assertEqual(Model().action_post(21), 42)
        (line,) = captured.output
        self.assertIn("event=action_post records=res.partner(4,5) ms=", line)
        self.assertTrue(line.endswith(" queries=2"))
        self.assertEqual(Model.action_post.__name__, "action_post")

    def test_timed_is_a_plain_call_when_disabled(self):
        perf = logging.getLogger(f"{ROOT}.perf")
        perf.setLevel(logging.INFO)
        self.addCleanup(perf.setLevel, logging.NOTSET)
        calls = []

        @self.log.perf.timed
        def helper(value):
            calls.append(value)
            return value

        with self.assertNoLogs(self.root, logging.DEBUG):
            self.assertEqual(helper(3), 3)
        self.assertEqual(calls, [3])

    def test_timed_names_the_exception_and_reraises(self):
        @self.log.perf.timed
        def boom():
            raise ValueError("x")

        with self.assertLogs(f"{ROOT}.perf", logging.DEBUG) as captured:
            with self.assertRaises(ValueError):
                boom()
        (line,) = captured.output
        self.assertIn("event=boom ms=", line)
        self.assertTrue(line.endswith(" error=ValueError"))

    def test_perf_count_is_a_single_line(self):
        with self.assertLogs(f"{ROOT}.perf", logging.DEBUG) as captured:
            self.log.perf.count("cache", hits=3, misses=1)
        self.assertEqual(
            captured.output,
            [f"DEBUG:{ROOT}.perf.base.ir_attachment:event=cache hits=3 misses=1"],
        )

    def test_perf_span_names_the_exception_and_reraises(self):
        with self.assertLogs(f"{ROOT}.perf", logging.DEBUG) as captured:
            with self.assertRaises(ValueError):
                with self.log.perf("boom"):
                    raise ValueError("x")
        (line,) = captured.output
        self.assertTrue(line.endswith(" error=ValueError"))
        self.assertNotIn("queries=", line)

    def test_channel_enabled_reflects_the_logger_level(self):
        self.root.setLevel(logging.INFO)
        self.assertFalse(self.log.pipeline.enabled)
        logging.getLogger(f"{ROOT}.pipeline").setLevel(logging.DEBUG)
        self.assertTrue(self.log.pipeline.enabled)
        logging.getLogger(f"{ROOT}.pipeline").setLevel(logging.NOTSET)
