import json
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

# ``_compute_order`` logs a warning when a cycle forces it to fall back to
# sequence order. One test below builds such a cycle on purpose.
DASHBOARD_LOGGER = "odoo.addons.od19_dashboard.models.dashboard"


class TestDashboardFormulaEngine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Engine test dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.widget = cls.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": cls.dashboard.id,
                "name": "Engine widget",
                "widget_type": "kpi",
                "source_id": cls.source.id,
                "measure_key": "amount_total",
                "date_key": "date_order",
                "date_range": "this_month",
            }
        )

    def test_aggregate_specs_deduplicates(self):
        specs = self.source._aggregate_specs(["amount_total", "__count", "amount_total"])
        self.assertEqual(specs, ["amount_total:sum", "__count"])

    def test_slot_map_parses_json(self):
        self.widget.formula_slots = '{"a": "amount_total", "b": "__count", "w1": 2}'
        self.assertEqual(
            self.widget._formula_slot_map(),
            {"a": "amount_total", "b": "__count", "w1": 2},
        )

    def test_slot_map_is_empty_on_bad_json(self):
        self.widget.formula_slots = "not json"
        self.assertEqual(self.widget._formula_slot_map(), {})

    def test_requests_in_measure_mode(self):
        self.widget.formula_mode = "measure"
        self.assertEqual(
            self.widget._aggregate_requests(),
            [("value", "amount_total", "amount_total:sum")],
        )

    def test_requests_in_preset_mode(self):
        self.widget.write(
            {
                "formula_mode": "preset",
                "formula_type": "ratio",
                "formula_slots": '{"a": "amount_total", "b": "__count"}',
            }
        )
        self.assertEqual(
            self.widget._aggregate_requests(),
            [("a", "amount_total", "amount_total:sum"), ("b", "__count", "__count")],
        )

    def test_requests_in_custom_mode_use_direct_names(self):
        self.widget.write(
            {"formula_mode": "custom", "formula_expression": "amount_total / count_records"}
        )
        self.assertEqual(
            self.widget._aggregate_requests(),
            [
                ("amount_total", "amount_total", "amount_total:sum"),
                ("count_records", "__count", "__count"),
            ],
        )

    def test_allowed_names_include_slots_and_goal(self):
        self.widget.write(
            {"formula_mode": "custom", "formula_expression": "amount_total / goal"}
        )
        allowed = self.widget._allowed_names()
        for name in ("a", "b", "goal", "total_a", "count_records", "amount_total"):
            self.assertIn(name, allowed)
        self.assertNotIn("__count", allowed)

    def test_validate_formula_config_accepts_preset(self):
        self.widget.write(
            {
                "formula_mode": "preset",
                "formula_type": "ratio",
                "formula_slots": '{"a": "amount_total", "b": "__count"}',
            }
        )
        self.widget._validate_formula_config()

    def test_validate_formula_config_rejects_missing_slot(self):
        with self.assertRaises(ValidationError):
            self.widget.write(
                {
                    "formula_mode": "preset",
                    "formula_type": "ratio",
                    "formula_slots": '{"a": "amount_total"}',
                }
            )

    def test_validate_formula_config_rejects_unknown_name(self):
        with self.assertRaises(ValidationError):
            self.widget.write(
                {"formula_mode": "custom", "formula_expression": "a / secret"}
            )

    def test_effective_expression_for_measure_mode(self):
        self.widget.formula_mode = "measure"
        self.assertEqual(self.widget._effective_expression(), "value")

    def test_effective_expression_for_preset_mode(self):
        self.widget.write(
            {
                "formula_mode": "preset",
                "formula_type": "growth",
                "formula_slots": '{"a": "amount_total", "b": "__count"}',
            }
        )
        self.assertEqual(self.widget._effective_expression(), "(a - b) / b * 100")

    def test_validate_formula_config_accepts_literal_weight_slots(self):
        self.widget.write(
            {
                "formula_mode": "preset",
                "formula_type": "weighted_average",
                "formula_slots": '{"a": "amount_total", "b": "amount_untaxed", "w1": 2, "w2": 1}',
            }
        )
        self.widget._validate_formula_config()

    def test_validate_formula_config_rejects_unknown_slot_measure(self):
        with self.assertRaises(ValidationError):
            self.widget.write(
                {
                    "formula_mode": "preset",
                    "formula_type": "ratio",
                    "formula_slots": '{"a": "amout_total", "b": "__count"}',
                }
            )


class TestDashboardRuleEngine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Rule engine dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.widget_a = cls.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": cls.dashboard.id,
                "name": "Widget A",
                "widget_type": "kpi",
                "source_id": cls.source.id,
                "measure_key": "amount_total",
                "date_key": "date_order",
                "date_range": "this_month",
            }
        )
        cls.widget_b = cls.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": cls.dashboard.id,
                "name": "Widget B",
                "widget_type": "kpi",
                "source_id": cls.source.id,
                "measure_key": "__count",
            }
        )

    def _rule(self, **values):
        values.setdefault("widget_id", self.widget_a.id)
        values.setdefault("status", "red")
        return self.env["od19.dashboard.widget.rule"].create(values)

    def test_operand_constant(self):
        rule = self._rule(compare_type="constant", compare_value=12.5)
        self.assertEqual(rule._compare_operand({"value": 3.0}), 12.5)

    def test_operand_goal(self):
        rule = self._rule(compare_type="goal")
        self.assertEqual(rule._compare_operand({"value": 3.0, "goal": 900.0}), 900.0)

    def test_operand_percent_of_goal(self):
        rule = self._rule(compare_type="percent_of_goal", compare_percent=80.0)
        self.assertEqual(rule._compare_operand({"value": 3.0, "goal": 1000.0}), 800.0)

    def test_operand_shifted_period(self):
        rule = self._rule(compare_type="yty")
        self.assertEqual(rule._compare_operand({"shifts": {"yty": 42.0}}), 42.0)
        self.assertIsNone(rule._compare_operand({"shifts": {}}))

    def test_operand_other_widget(self):
        rule = self._rule(compare_type="widget", compare_widget_id=self.widget_b.id)
        context = {"widget_values": {self.widget_b.id: 7.0}}
        self.assertEqual(rule._compare_operand(context), 7.0)

    def test_evaluate_rules_first_match_wins(self):
        self._rule(sequence=10, operator="<=", compare_value=100.0, status="red")
        self._rule(sequence=20, operator="<=", compare_value=500.0, status="yellow")
        status, source, message = self.widget_a._evaluate_rules({"value": 50.0})
        self.assertEqual(status, "red")
        self.assertEqual(source, "rule")
        self.assertEqual(message, "")

    def test_evaluate_rules_continues_when_rule_does_not_match(self):
        self._rule(sequence=10, operator="<=", compare_value=10.0, status="red")
        self._rule(sequence=20, operator="<=", compare_value=500.0, status="yellow")
        status, source, _message = self.widget_a._evaluate_rules({"value": 50.0})
        self.assertEqual((status, source), ("yellow", "rule"))

    def test_evaluate_rules_carries_the_alert_message(self):
        self._rule(
            sequence=10,
            operator="<=",
            compare_value=100.0,
            status="red",
            alert_message="Below the minimum",
        )
        status, _source, message = self.widget_a._evaluate_rules({"value": 50.0})
        self.assertEqual(status, "red")
        self.assertEqual(message, "Below the minimum")

    def test_evaluate_rules_falls_back_to_default_status(self):
        self.widget_a.default_status = "grey"
        self.assertEqual(
            self.widget_a._evaluate_rules({"value": 50.0}), ("grey", "default", "")
        )

    def test_evaluate_rules_skips_inactive_rules(self):
        self._rule(compare_value=100.0, status="red", active=False)
        self.widget_a.default_status = "green"
        self.assertEqual(
            self.widget_a._evaluate_rules({"value": 50.0}), ("green", "default", "")
        )

    def test_evaluate_rules_ignores_none_value(self):
        self._rule(compare_value=100.0, status="red")
        self.widget_a.default_status = "grey"
        self.assertEqual(
            self.widget_a._evaluate_rules({"value": None}), ("grey", "default", "")
        )

    def test_required_shifts_collects_delta_rules_and_formula(self):
        self.widget_a.write(
            {
                "delta_basis": "mtm",
                "formula_mode": "custom",
                "formula_expression": "amount_total",
                "formula_basis": "qtq",
            }
        )
        self._rule(compare_type="yty", status="red")
        self.assertEqual(self.widget_a._required_shifts(), {"mtm", "qtq", "yty"})

    def test_required_shifts_skips_delta_when_hidden(self):
        self.widget_a.show_delta = False
        self.widget_a.delta_basis = "mtm"
        self.assertEqual(self.widget_a._required_shifts(), set())

    def test_date_bounds_applies_previous_shift(self):
        # ``apply_shift(..., "previous")`` uses inclusive bounds, so a 12 day
        # window (2026-03-05 → 2026-03-16) shifts to 2026-02-21 → 2026-03-04.
        # This mirrors ``test_shift_previous_keeps_period_length`` in
        # ``test_dashboard_formula.py``.
        bounds = self.widget_a._date_bounds("this_year", "2026-03-05", "2026-03-16", shift="previous")
        self.assertEqual(
            bounds,
            [
                ("date_order", ">=", "2026-02-21 00:00:00"),
                ("date_order", "<=", "2026-03-04 23:59:59"),
            ],
        )

    def test_date_bounds_applies_yty_shift(self):
        bounds = self.widget_a._date_bounds("this_year", "2026-03-01", "2026-03-31", shift="yty")
        self.assertEqual(
            bounds,
            [
                ("date_order", ">=", "2025-03-01 00:00:00"),
                ("date_order", "<=", "2025-03-31 23:59:59"),
            ],
        )

    def test_date_bounds_shift_none_keeps_the_period(self):
        bounds = self.widget_a._date_bounds("this_year", "2026-03-01", "2026-03-31")
        self.assertEqual(
            bounds,
            [
                ("date_order", ">=", "2026-03-01 00:00:00"),
                ("date_order", "<=", "2026-03-31 23:59:59"),
            ],
        )

    def test_period_bounds_all_time_has_no_bounds(self):
        start, end, field_type = self.widget_a._period_bounds("all_time")
        self.assertIsNone(start)
        self.assertIsNone(end)
        self.assertEqual(field_type, "datetime")

    def test_period_bounds_without_date_key_has_no_bounds(self):
        start, end, field_type = self.widget_b._period_bounds("this_month")
        self.assertIsNone(start)
        self.assertIsNone(end)
        self.assertEqual(field_type, "date")

    def test_period_bounds_overdue_starts_at_none(self):
        today = fields.Date.context_today(self.widget_a)
        start, end, _field_type = self.widget_a._period_bounds("overdue")
        self.assertIsNone(start)
        self.assertEqual(end, today - timedelta(days=1))

    def test_period_bounds_all_time_honours_custom_dates(self):
        """An explicit custom range wins over the ``all_time`` default."""
        start, end, _field_type = self.widget_a._period_bounds(
            "all_time", "2026-03-01", "2026-03-31"
        )
        self.assertEqual(start.isoformat(), "2026-03-01")
        self.assertEqual(end.isoformat(), "2026-03-31")

    def test_build_domain_all_time_honours_custom_dates(self):
        domain = self.widget_a._build_domain("all_time", "2026-03-01", "2026-03-31")
        self.assertIn(("date_order", ">=", "2026-03-01 00:00:00"), domain)
        self.assertIn(("date_order", "<=", "2026-03-31 23:59:59"), domain)

    def test_build_domain_all_time_without_dates_stays_unbounded(self):
        domain = self.widget_a._build_domain("all_time")
        self.assertFalse([term for term in domain if term[0] == "date_order"])

    def test_date_bounds_on_a_date_field_has_no_time_suffix(self):
        widget = self.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": self.dashboard.id,
                "name": "Date field widget",
                "widget_type": "kpi",
                "source_id": self.env.ref("od19_dashboard.source_account_move").id,
                "measure_key": "amount_total",
                "date_key": "invoice_date",
                "date_range": "this_year",
            }
        )
        bounds = widget._date_bounds("this_year", "2026-03-01", "2026-03-31")
        self.assertEqual(
            bounds,
            [
                ("invoice_date", ">=", "2026-03-01"),
                ("invoice_date", "<=", "2026-03-31"),
            ],
        )

    def test_is_lower_better_inferred_from_the_first_red_rule(self):
        self.assertFalse(self.widget_a._is_lower_better())
        self._rule(operator="<=", compare_value=100.0, status="red")
        self.assertFalse(self.widget_a._is_lower_better())
        self.widget_a.rule_ids.unlink()
        self._rule(operator=">=", compare_value=100.0, status="red")
        self.assertTrue(self.widget_a._is_lower_better())

    def test_unresolved_names_detects_unbound_slot(self):
        # An unbound slot is an invalid configuration: the ``_check_formula_config``
        # constraint refuses it on a real write. Build the widget in memory with
        # ``new()`` (which never triggers a constraint) to exercise the helper.
        widget = self.env["od19.dashboard.widget"].new(
            {
                "dashboard_id": self.dashboard.id,
                "source_id": self.source.id,
                "measure_key": "amount_total",
                "formula_mode": "custom",
                "formula_expression": "a + amount_total",
            }
        )
        self.assertEqual(widget._unresolved_names(), ["a"])
        widget.formula_slots = '{"a": "amount_total"}'
        self.assertEqual(widget._unresolved_names(), [])


class TestDashboardOrdering(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Ordering dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.widget_a = cls._make_widget(cls, "Widget A")
        cls.widget_b = cls._make_widget(cls, "Widget B")
        cls.widget_c = cls._make_widget(cls, "Widget C")

    def _make_widget(self, name):
        return self.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": self.dashboard.id,
                "name": name,
                "widget_type": "kpi",
                "source_id": self.source.id,
                "measure_key": "__count",
            }
        )

    def test_dependency_ids_from_rule_and_expression(self):
        self.env["od19.dashboard.widget.rule"].create(
            {
                "widget_id": self.widget_a.id,
                "compare_type": "widget",
                "compare_widget_id": self.widget_b.id,
                "status": "green",
            }
        )
        self.widget_c.write(
            {
                "formula_mode": "custom",
                "formula_expression": "count_records + widget_%s" % self.widget_a.id,
            }
        )
        self.assertEqual(self.widget_a._dependency_ids(), [self.widget_b.id])
        self.assertEqual(self.widget_c._dependency_ids(), [self.widget_a.id])

    def test_dependency_ids_never_contains_the_widget_itself(self):
        # Both routes to a self reference are refused on a real write:
        # ``_check_formula_config`` drops the widget's own id from the allowed
        # names, and ``_check_compare_widget`` refuses a rule that compares a
        # widget with itself. Force the expression in memory so the
        # self-discard branch of ``_dependency_ids`` is actually exercised.
        widget = self._make_widget("Self referencing")
        with patch.object(
            type(widget),
            "_effective_expression",
            lambda self: "count_records + widget_%s" % self.id,
        ):
            self.assertEqual(widget._dependency_ids(), [])

    def test_compute_order_places_dependencies_first(self):
        self.widget_c.write(
            {
                "formula_mode": "custom",
                "formula_expression": "count_records + widget_%s" % self.widget_a.id,
            }
        )
        ordered = self.dashboard._compute_order()
        self.assertLess(ordered.index(self.widget_a), ordered.index(self.widget_c))

    @mute_logger(DASHBOARD_LOGGER)
    def test_compute_order_survives_a_cycle(self):
        # The ORM refuses to store a cycle by design (``_check_dependency_cycle``
        # raises ``ValidationError``), so the cycle has to be written straight
        # into the database to exercise the fail-soft branch of ``_compute_order``.
        self.env.cr.execute(
            "UPDATE od19_dashboard_widget SET formula_mode = %s, formula_expression = %s WHERE id = %s",
            ("custom", "count_records + widget_%s" % self.widget_b.id, self.widget_a.id),
        )
        self.env.cr.execute(
            "UPDATE od19_dashboard_widget SET formula_mode = %s, formula_expression = %s WHERE id = %s",
            ("custom", "count_records + widget_%s" % self.widget_a.id, self.widget_b.id),
        )
        self.env.invalidate_all()
        ordered = self.dashboard._compute_order()
        # Widget C has no dependency, so it is emitted first. The A/B pair is a
        # cycle and cannot be ordered: the fallback emits the remaining widgets
        # in (sequence, id) order, which here is A then B. No widget is lost.
        self.assertEqual(ordered, [self.widget_c, self.widget_a, self.widget_b])

    def test_compute_order_skips_inactive_widgets(self):
        self.widget_b.active = False
        self.widget_c.write(
            {
                "formula_mode": "custom",
                "formula_expression": "count_records + widget_%s" % self.widget_b.id,
            }
        )
        ordered = self.dashboard._compute_order()
        # An inactive widget is never emitted, but reading it must not block
        # the widget that refers to it.
        self.assertEqual(ordered, [self.widget_a, self.widget_c])

    def test_compute_order_ignores_a_dependency_outside_the_dashboard(self):
        other = self.env["od19.dashboard"].create({"name": "Other ordering dashboard"})
        foreign = self.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": other.id,
                "name": "Foreign widget",
                "widget_type": "kpi",
                "source_id": self.source.id,
                "measure_key": "__count",
            }
        )
        self.widget_c.write(
            {
                "formula_mode": "custom",
                "formula_expression": "count_records + widget_%s" % foreign.id,
            }
        )
        ordered = self.dashboard._compute_order()
        # A dependency that is not part of this dashboard is already satisfied,
        # so it must neither deadlock the sort nor be emitted.
        self.assertEqual(len(ordered), 3)
        self.assertNotIn(foreign, ordered)

    def test_get_dashboard_data_returns_every_widget_with_a_cross_widget_rule(self):
        self.env["od19.dashboard.widget.rule"].create(
            {
                "widget_id": self.widget_a.id,
                "compare_type": "widget",
                "compare_widget_id": self.widget_b.id,
                "operator": ">",
                "status": "green",
            }
        )
        data = self.env["od19.dashboard"].get_dashboard_data(self.dashboard.id)
        self.assertEqual(len(data["widgets"]), 3)
        self.assertEqual(
            {widget["id"] for widget in data["widgets"]},
            {self.widget_a.id, self.widget_b.id, self.widget_c.id},
        )
        # Widget A reads Widget B, so B must be rendered (and therefore
        # computed) before A: the emitted order proves the dependency wins.
        self.assertEqual(
            [widget["id"] for widget in data["widgets"]],
            [self.widget_b.id, self.widget_c.id, self.widget_a.id],
        )
        self.assertIn("status_source", data["widgets"][0])


# These tests create ``sale.order`` records. Another installed module
# (``od19_sales_project_context``) adds a required field on ``sale.order`` that
# the registry does not carry yet while ``od19_dashboard`` is being installed,
# so the class runs during ``post_install`` where the registry is complete.
# The tests are neither skipped nor weakened: they run in the same
# ``--test-enable`` pass.
@tagged("post_install", "-at_install")
class TestDashboardPreview(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Preview test dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.base_values = {
            "dashboard_id": cls.dashboard.id,
            "name": "Preview widget",
            "widget_type": "kpi",
            "source_id": cls.source.id,
            "measure_key": "amount_total",
            "date_key": "date_order",
            "date_range": "all_time",
        }

    def _preview(self, **overrides):
        values = dict(self.base_values)
        values.update(overrides)
        return self.env["od19.dashboard"].preview_widget(values)

    def test_preview_returns_a_value_and_a_count(self):
        result = self._preview()
        self.assertIn("value", result)
        self.assertIsInstance(result["record_count"], int)
        self.assertEqual(result["status"], "green")
        self.assertEqual(result["status_source"], "default")

    def test_preview_evaluates_a_preset_formula(self):
        result = self._preview(
            formula_mode="preset",
            formula_type="ratio",
            formula_slots='{"a": "amount_total", "b": "__count"}',
        )
        self.assertEqual(result["formula_expression"], "a / b")
        self.assertEqual([item["alias"] for item in result["operands"]], ["a", "b"])

    def test_preview_evaluates_a_literal_weight_slot(self):
        result = self._preview(
            formula_mode="preset",
            formula_type="weighted_average",
            formula_slots='{"a": "amount_total", "b": "amount_untaxed", "w1": 2, "w2": 1}',
        )
        operands = {item["alias"]: item["value"] for item in result["operands"]}
        expected = (operands["a"] * 2 + operands["b"] * 1) / 3
        self.assertAlmostEqual(result["value"], expected)

    def test_preview_applies_the_first_matching_rule(self):
        result = self._preview(
            rule_ids=[
                (0, 0, {
                    "operator": "<",
                    "compare_type": "constant",
                    "compare_value": -1,
                    "status": "red",
                }),
                (0, 0, {
                    "operator": ">=",
                    "compare_type": "constant",
                    "compare_value": -1,
                    "status": "yellow",
                }),
            ],
        )
        self.assertEqual(result["status"], "yellow")
        self.assertEqual(result["status_source"], "rule")

    def test_preview_reports_the_alert_message(self):
        """Phase 2, item 2: the matching rule carries a message to display."""
        result = self._preview(
            rule_ids=[
                (0, 0, {
                    "operator": ">=",
                    "compare_type": "constant",
                    "compare_value": -1,
                    "status": "red",
                    "alert_message": "Amount out of range",
                }),
            ],
        )
        self.assertEqual(result["status"], "red")
        self.assertEqual(result["status_message"], "Amount out of range")

    def test_preview_reports_a_hidden_widget(self):
        """Phase 2, item 1: a false condition hides the widget."""
        hidden = self._preview(
            formula_mode="custom",
            formula_expression="count_records",
            visible_expression="count_records < 0",
        )
        self.assertFalse(hidden["visible"])
        shown = self._preview(
            formula_mode="custom",
            formula_expression="count_records",
            visible_expression="count_records >= 0",
        )
        self.assertTrue(shown["visible"])

    def test_preview_refuses_a_broken_formula(self):
        with self.assertRaises(ValidationError):
            self._preview(formula_mode="custom", formula_expression="__import__('os').system('dir')")
        with self.assertRaises(ValidationError):
            self._preview(formula_mode="preset", formula_type="ratio", formula_slots='{"a": "amount_total"}')

    def test_preview_writes_nothing(self):
        before = self.env["od19.dashboard.widget"].search_count(
            [("dashboard_id", "=", self.dashboard.id)]
        )
        self._preview()
        after = self.env["od19.dashboard.widget"].search_count(
            [("dashboard_id", "=", self.dashboard.id)]
        )
        self.assertEqual(before, after)

    def test_preview_returns_a_series_preview_for_charts(self):
        result = self._preview(widget_type="bar", groupby_key="state", limit=5)
        self.assertLessEqual(len(result["series_preview"]), 5)

    def test_preview_reads_the_aggregate_of_an_ungrouped_row(self):
        """A KPI reads one row without a group value, so alias 0 maps to row[0]."""
        partner = self.env["res.partner"].create({"name": "Preview customer"})
        self.env["sale.order"].create({"partner_id": partner.id})
        expected = float(self.env["sale.order"].search_count([]))
        self.assertGreater(expected, 0)
        result = self._preview(
            measure_key="__count",
            formula_mode="custom",
            formula_expression="count_records",
        )
        self.assertEqual(result["value"], expected)

    def test_preview_reads_the_aggregate_of_a_grouped_row(self):
        """A chart reads grouped rows: the group value precedes the aggregates."""
        rows = self.env["sale.order"]._read_group([], ["state"], ["__count"])
        self.assertLessEqual(len(rows), 5)
        result = self._preview(
            widget_type="bar",
            groupby_key="state",
            limit=50,
            measure_key="__count",
            formula_mode="custom",
            formula_expression="count_records",
        )
        self.assertEqual(
            sum(item["value"] for item in result["series_preview"]),
            float(sum(count for _state, count in rows)),
        )

    def test_preview_ignores_non_creation_rule_commands(self):
        """Link / clear / delete commands must not become empty create commands."""
        rule = {
            "operator": ">",
            "compare_type": "constant",
            "compare_value": 1,
            "status": "red",
        }
        values = self.env["od19.dashboard"]._normalise_preview_values(
            {
                "name": "Draft",
                "rule_ids": [(4, 7, 0), (5, 0, 0), (2, 7, 0), (0, 0, rule)],
            }
        )
        self.assertEqual(values["rule_ids"], [(0, 0, rule)])

    def test_preview_reads_a_chained_dependency(self):
        """A widget the draft reads must itself be computed after its own dependency."""
        other = self.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": self.dashboard.id,
                "name": "Constant",
                "widget_type": "kpi",
                "source_id": self.source.id,
                "measure_key": "amount_total",
                "date_key": "date_order",
                "date_range": "all_time",
                "sequence": 20,
                "formula_mode": "custom",
                "formula_expression": "100",
            }
        )
        dependent = self.env["od19.dashboard.widget"].create(
            {
                "dashboard_id": self.dashboard.id,
                "name": "Chained",
                "widget_type": "kpi",
                "source_id": self.source.id,
                "measure_key": "amount_total",
                "date_key": "date_order",
                "date_range": "all_time",
                "sequence": 5,
                "formula_mode": "custom",
                "formula_expression": "widget_%s + 1" % other.id,
            }
        )
        result = self._preview(
            formula_mode="custom", formula_expression="widget_%s" % dependent.id
        )
        self.assertEqual(result["value"], 101.0)
        # The aggregate read to give the widget a row is not an operand the
        # formula names, so the builder operand list stays empty.
        self.assertEqual(result["operands"], [])

    def test_preview_shares_a_bucket_against_the_displayed_buckets(self):
        """A chart divides each bucket by the displayed buckets, not the domain.

        Three states are populated while only two buckets are displayed: using
        the domain-wide total would make the series sum to less than 100.
        """
        partner = self.env["res.partner"].create({"name": "Share customer"})
        for state in ("draft", "sent", "sale"):
            self.env["sale.order"].create({"partner_id": partner.id, "state": state})
        displayed = sum(
            count
            for _state, count in self.env["sale.order"]._read_group(
                [], ["state"], ["__count"], order="__count desc", limit=2
            )
        )
        self.assertGreater(self.env["sale.order"].search_count([]), displayed)
        result = self._preview(
            widget_type="pie",
            groupby_key="state",
            limit=2,
            measure_key="__count",
            formula_mode="preset",
            formula_type="share",
            formula_slots='{"a": "__count"}',
        )
        series = result["series_preview"]
        self.assertTrue(series)
        self.assertAlmostEqual(sum(item["value"] for item in series), 100.0)

    def test_number_text_keeps_a_single_minus_sign(self):
        widget = self.env["od19.dashboard.widget"].new({"name": "Number text"})
        self.assertEqual(widget._number_text(-1234.5, 2), "-1,234.5")
        self.assertEqual(widget._number_text(1234.5, 2), "1,234.5")
        self.assertEqual(widget._number_text(0, 0), "0")


# Like ``TestDashboardPreview`` this class creates ``sale.order`` records.
# Another installed module (``od19_sales_project_context``) adds a required
# field on ``sale.order`` that the registry does not carry yet while
# ``od19_dashboard`` is being installed, so the class runs during
# ``post_install`` where the registry is complete.
@tagged("post_install", "-at_install")
class TestDashboardAcceptance(TransactionCase):
    """Acceptance checks of spec section 10.2 no earlier task covered."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Acceptance dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        partner = cls.env["res.partner"].create({"name": "Acceptance customer"})
        product = cls.env["product.product"].create(
            {"name": "Acceptance product", "list_price": 100.0}
        )
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 2.0})
                ],
            }
        )

    def _values(self, **extra):
        values = {
            "dashboard_id": self.dashboard.id,
            "name": "Acceptance widget",
            "widget_type": "kpi",
            "source_id": self.source.id,
            "measure_key": "__count",
            "date_key": "date_order",
            "date_range": "this_month",
            "goal_value": 10.0,
            # Scope every acceptance widget to the single order created in
            # ``setUpClass`` so the expected values (1 record, 200 + 200) do
            # not depend on other sale orders already in the database.
            "domain": "[('partner_id', '=', %s)]" % self.order.partner_id.id,
        }
        values.update(extra)
        return values

    def _preview(self, **extra):
        return self.env["od19.dashboard"].preview_widget(
            self._values(**extra), date_range="this_month"
        )

    def test_every_preset_formula_returns_a_number(self):
        slots_by_type = {
            "ratio": {"a": "__count", "b": "amount_total"},
            "difference": {"a": "amount_total", "b": "amount_untaxed"},
            "growth": {"a": "amount_total", "b": "amount_untaxed"},
            "share": {"a": "amount_total"},
            "sum": {"a": "amount_total", "b": "amount_untaxed"},
            "average": {"a": "amount_total", "b": "amount_untaxed"},
            "weighted_average": {"a": "amount_total", "b": "amount_untaxed", "w1": 2, "w2": 1},
            "percent_of_goal": {"a": "amount_total"},
            "min": {"a": "amount_total", "b": "amount_untaxed"},
            "max": {"a": "amount_total", "b": "amount_untaxed"},
            "cumulative_change": {"a": "amount_total"},
            "run_rate": {"a": "amount_total"},
            "conversion_rate": {"a": "__count", "b": "amount_total"},
            "variance": {"a": "amount_total", "b": "amount_untaxed"},
        }
        for formula_type, slots in slots_by_type.items():
            result = self._preview(
                formula_mode="preset",
                formula_type=formula_type,
                formula_slots=json.dumps(slots),
            )
            self.assertIsInstance(result["value"], (int, float), formula_type)
            self.assertGreaterEqual(result["record_count"], 1, formula_type)

    def test_count_records_alias_works(self):
        result = self._preview(formula_mode="custom", formula_expression="count_records")
        self.assertEqual(result["value"], 1)

    def test_simple_slots_match_direct_names(self):
        with_slots = self._preview(
            formula_mode="custom",
            formula_expression="a + b",
            formula_slots=json.dumps({"a": "amount_total", "b": "amount_untaxed"}),
        )
        with_names = self._preview(
            formula_mode="custom",
            formula_expression="amount_total + amount_untaxed",
        )
        self.assertEqual(with_slots["value"], with_names["value"])
        self.assertEqual(
            with_slots["value"],
            self.order.amount_total + self.order.amount_untaxed,
            "Slots must resolve to the same measures as the direct names.",
        )

    def test_cross_widget_value_matches_the_source_widget(self):
        source_widget = self.env["od19.dashboard.widget"].create(
            self._values(name="Source widget", formula_mode="custom", formula_expression="count_records")
        )
        reader_widget = self.env["od19.dashboard.widget"].create(
            self._values(
                name="Reader widget",
                formula_mode="custom",
                formula_expression="widget_%s * 2" % source_widget.id,
            )
        )
        data = self.env["od19.dashboard"].get_dashboard_data(
            self.dashboard.id, date_range="this_month"
        )
        values = {widget["id"]: widget["value"] for widget in data["widgets"]}
        self.assertEqual(values[source_widget.id], 1)
        self.assertEqual(values[reader_widget.id], 2)

    def test_a_rule_may_read_a_widget_of_another_dashboard(self):
        """Phase 2, item 6: a cross-dashboard widget is resolved lazily."""
        other = self.env["od19.dashboard"].create({"name": "Foreign acceptance dashboard"})
        foreign = self.env["od19.dashboard.widget"].create(
            dict(
                self._values(
                    name="Foreign source",
                    formula_mode="custom",
                    formula_expression="count_records",
                ),
                dashboard_id=other.id,
            )
        )
        reader = self.env["od19.dashboard.widget"].create(
            self._values(
                name="Cross dashboard reader",
                formula_mode="custom",
                formula_expression="widget_%s * 10" % foreign.id,
            )
        )
        data = self.env["od19.dashboard"].get_dashboard_data(
            self.dashboard.id, date_range="this_month"
        )
        values = {widget["id"]: widget["value"] for widget in data["widgets"]}
        # The foreign widget belongs to another dashboard, so it must not be
        # emitted, but its value still has to reach the reader's formula.
        self.assertNotIn(foreign.id, values)
        self.assertEqual(values[reader.id], 10)

    def test_chart_buckets_carry_their_own_status(self):
        """Phase 2, item 4: every bar of a chart is coloured by its own status."""
        widget = self.env["od19.dashboard.widget"].create(
            self._values(name="Bucket chart", widget_type="bar", groupby_key="state", limit=50)
        )
        self.env["od19.dashboard.widget.rule"].create(
            {
                "widget_id": widget.id,
                "operator": ">=",
                "compare_type": "constant",
                "compare_value": 0.0,
                "status": "red",
                "alert_message": "Bucket alert",
            }
        )
        data = widget._get_widget_data(date_range="this_month")
        self.assertTrue(data["series"])
        for bucket in data["series"]:
            self.assertEqual(bucket["status"], "red")
            self.assertEqual(bucket["color"], "#9E2424")
            self.assertEqual(bucket["message"], "Bucket alert")
        # The widget status is the most severe bucket status.
        self.assertEqual(data["status"], "red")
        self.assertEqual(data["status_source"], "rule")
        self.assertEqual(data["status_message"], "Bucket alert")

    def test_list_rows_carry_their_own_status(self):
        """Phase 2, item 3: every row of a list is coloured by its own status."""
        widget = self.env["od19.dashboard.widget"].create(
            self._values(
                name="Status list",
                widget_type="list",
                measure_key="amount_total",
                limit=5,
            )
        )
        self.env["od19.dashboard.widget.rule"].create(
            {
                "widget_id": widget.id,
                "operator": ">=",
                "compare_type": "constant",
                "compare_value": 0.0,
                "status": "yellow",
            }
        )
        data = widget._get_widget_data(date_range="this_month")
        self.assertTrue(data["rows"])
        for row in data["rows"]:
            self.assertEqual(row["status"], "yellow")
            self.assertEqual(row["color"], "#B7791F")
        self.assertEqual(data["status"], "yellow")
        self.assertEqual(data["status_source"], "rule")

    def test_cycle_is_refused_on_save(self):
        widget_a = self.env["od19.dashboard.widget"].create(
            self._values(name="Cycle A", formula_mode="custom", formula_expression="count_records")
        )
        widget_b = self.env["od19.dashboard.widget"].create(
            self._values(name="Cycle B", formula_mode="custom", formula_expression="count_records")
        )
        widget_a.formula_expression = "count_records + widget_%s" % widget_b.id
        with self.assertRaises(ValidationError):
            widget_b.formula_expression = "count_records + widget_%s" % widget_a.id

    def test_cycle_through_a_direct_rule_write_is_refused(self):
        widget_a = self.env["od19.dashboard.widget"].create(
            self._values(name="Rule cycle A", formula_mode="custom", formula_expression="count_records")
        )
        widget_b = self.env["od19.dashboard.widget"].create(
            self._values(name="Rule cycle B", formula_mode="custom", formula_expression="count_records")
        )
        # A reads B through its expression, so the edge B -> A closes the loop.
        widget_a.formula_expression = "count_records + widget_%s" % widget_b.id
        # The owning widget is untouched here, so only the rule constraint can
        # refuse the cycle (spec section 11).
        with self.assertRaises(ValidationError):
            self.env["od19.dashboard.widget.rule"].create(
                {
                    "widget_id": widget_b.id,
                    "compare_type": "widget",
                    "compare_widget_id": widget_a.id,
                    "operator": "<=",
                    "status": "red",
                }
            )

    def test_cycle_is_refused_when_a_rule_is_reactivated(self):
        widget_a = self.env["od19.dashboard.widget"].create(
            self._values(name="Reactivate A", formula_mode="custom", formula_expression="count_records")
        )
        widget_b = self.env["od19.dashboard.widget"].create(
            self._values(name="Reactivate B", formula_mode="custom", formula_expression="count_records")
        )
        rule = self.env["od19.dashboard.widget.rule"].create(
            {
                "widget_id": widget_b.id,
                "compare_type": "widget",
                "compare_widget_id": widget_a.id,
                "operator": "<=",
                "status": "red",
                "active": False,
            }
        )
        widget_a.formula_expression = "count_records + widget_%s" % widget_b.id
        with self.assertRaises(ValidationError):
            rule.active = True

    def test_cycle_is_refused_when_a_widget_is_reactivated(self):
        widget_a = self.env["od19.dashboard.widget"].create(
            self._values(name="Widget reactivate A", formula_mode="custom", formula_expression="count_records")
        )
        widget_b = self.env["od19.dashboard.widget"].create(
            self._values(name="Widget reactivate B", formula_mode="custom", formula_expression="count_records")
        )
        self.env["od19.dashboard.widget.rule"].create(
            {
                "widget_id": widget_b.id,
                "compare_type": "widget",
                "compare_widget_id": widget_a.id,
                "operator": "<=",
                "status": "red",
            }
        )
        # Archiving B removes it from the graph, so A no longer depends on a
        # live widget and the dashboard settles.
        widget_b.active = False
        widget_a.formula_expression = "count_records + widget_%s" % widget_b.id
        with self.assertRaises(ValidationError):
            widget_b.active = True

    def test_builder_rpc_refuses_a_user_without_write_access(self):
        widget = self.env["od19.dashboard.widget"].create(self._values(name="Protected widget"))
        stranger = self.env["res.users"].create(
            {
                "name": "Acceptance stranger",
                "login": "od19_dashboard_acceptance_stranger",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        with self.assertRaises(AccessError):
            self.env["od19.dashboard"].with_user(stranger).update_widget(
                widget.id, {"name": "Hijacked"}
            )

    def test_delta_is_empty_when_both_periods_have_no_data(self):
        """Two empty periods are "not comparable", not a flat 0%."""
        widget = self.env["od19.dashboard.widget"].create(
            self._values(name="Empty delta widget", show_delta=True, date_range="yesterday")
        )
        data = self.env["od19.dashboard"].get_dashboard_data(self.dashboard.id, "yesterday")
        row = next(item for item in data["widgets"] if item["id"] == widget.id)
        self.assertEqual(row["value"], 0.0)
        self.assertIsNone(row["delta"])

    def test_update_widget_clamps_the_grid_size(self):
        widget = self.env["od19.dashboard.widget"].create(self._values(name="Clamp widget"))
        self.env["od19.dashboard"].update_widget(widget.id, {"grid_w": 99, "grid_h": 99})
        self.assertEqual(widget.grid_w, 12)
        self.assertEqual(widget.grid_h, 6)
        self.env["od19.dashboard"].update_widget(widget.id, {"grid_w": 1, "grid_h": -5})
        self.assertEqual(widget.grid_w, 2)
        self.assertEqual(widget.grid_h, 1)

    def test_get_dashboard_data_echoes_the_custom_range(self):
        self.env["od19.dashboard.widget"].create(
            self._values(name="Custom range widget", date_range="all_time")
        )
        data = self.env["od19.dashboard"].get_dashboard_data(
            self.dashboard.id, None, "2026-03-01", "2026-03-31"
        )
        self.assertEqual(data["meta"]["date_from"], "2026-03-01")
        self.assertEqual(data["meta"]["date_to"], "2026-03-31")

    def test_operands_do_not_add_aggregation_queries(self):
        """Spec 10.2: operands must be batched into one aggregation per domain.

        ``_record_count`` legitimately runs its own aggregation, so the check
        compares two formulas with a different number of slots instead of
        hard-coding a call count.
        """
        model = type(self.env["sale.order"])
        original = model._read_group
        calls = []

        def counting_read_group(recordset, *args, **kwargs):
            calls.append(recordset._name)
            return original(recordset, *args, **kwargs)

        model._read_group = counting_read_group
        try:
            self._preview(formula_mode="custom", formula_expression="amount_total")
            one_slot = len(calls)
            calls.clear()
            self._preview(
                formula_mode="custom",
                formula_expression="a + b + c + d",
                formula_slots=json.dumps(
                    {
                        "a": "amount_total",
                        "b": "amount_untaxed",
                        "c": "amount_total",
                        "d": "amount_untaxed",
                    }
                ),
            )
            four_slots = len(calls)
        finally:
            model._read_group = original
        self.assertGreater(
            one_slot,
            0,
            "One operand slot must run its own aggregation, otherwise the "
            "comparison below is vacuous.",
        )
        self.assertEqual(
            four_slots,
            one_slot,
            "Four operand slots must reuse the aggregation of a single slot.",
        )


class TestDashboardFormulaLibrary(TransactionCase):
    """Phase 2, item 5: reusable named formulas and cross-source slots."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Library dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.formula = cls.env["od19.dashboard.formula"].create(
            {"name": "Invoice rate", "expression": "invoices / orders * 100"}
        )

    def _widget(self, **values):
        base = {
            "dashboard_id": self.dashboard.id,
            "name": "Library widget",
            "widget_type": "kpi",
            "source_id": self.source.id,
            "measure_key": "__count",
        }
        base.update(values)
        return self.env["od19.dashboard.widget"].create(base)

    def test_formula_meta_exposes_its_names(self):
        meta = self.formula._to_meta()
        self.assertEqual(meta["name"], "Invoice rate")
        self.assertEqual(meta["expression"], "invoices / orders * 100")
        self.assertEqual(meta["names"], ["invoices", "orders"])

    def test_library_mode_evaluates_the_named_formula(self):
        widget = self._widget(
            formula_mode="library",
            formula_id=self.formula.id,
            formula_slots=json.dumps({"invoices": "amount_total", "orders": "__count"}),
        )
        self.assertEqual(widget._effective_expression(), "invoices / orders * 100")
        # A library formula names its own slots: any identifier is accepted.
        self.assertEqual(sorted(widget._formula_slot_map()), ["invoices", "orders"])
        self.assertEqual(
            widget._aggregate_requests(),
            [
                ("invoices", "amount_total", "amount_total:sum"),
                ("orders", "__count", "__count"),
            ],
        )

    def test_library_mode_requires_a_selected_formula(self):
        with self.assertRaises(ValidationError):
            self._widget(formula_mode="library")

    def test_library_mode_rejects_an_unbound_name(self):
        with self.assertRaises(ValidationError):
            self._widget(
                formula_mode="library",
                formula_id=self.formula.id,
                formula_slots=json.dumps({"invoices": "amount_total"}),
            )

    def test_cross_source_slot_is_read_outside_the_widget_domain(self):
        purchase = self.env.ref("od19_dashboard.source_purchase_order")
        widget = self._widget(
            formula_mode="library",
            formula_id=self.formula.id,
            formula_slots=json.dumps(
                {
                    "invoices": {"source_id": purchase.id, "measure_key": "amount_total"},
                    "orders": "__count",
                }
            ),
        )
        # A slot bound to another source is not read by the single aggregation
        # of the widget: it is resolved through ``_external_slot_values()``.
        self.assertNotIn(
            "invoices", [request[0] for request in widget._aggregate_requests()]
        )
        external = widget._external_slot_values()
        self.assertIn("invoices", external)
        rows = self.env["purchase.order"]._read_group([], [], ["amount_total:sum"])
        expected = rows[0][0] if rows else 0.0
        self.assertEqual(external["invoices"], expected)


class TestDashboardVisibility(TransactionCase):
    """Phase 2, item 1: conditional display through ``visible_expression``."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Visibility dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")

    def _widget(self, **values):
        base = {
            "dashboard_id": self.dashboard.id,
            "name": "Visibility widget",
            "widget_type": "kpi",
            "source_id": self.source.id,
            "measure_key": "__count",
        }
        base.update(values)
        return self.env["od19.dashboard.widget"].create(base)

    def test_empty_condition_keeps_the_widget_visible(self):
        widget = self._widget()
        self.assertTrue(widget._is_visible({"value": 0.0}))

    def test_condition_hides_the_widget_when_it_is_false(self):
        widget = self._widget(visible_expression="value > 0")
        self.assertFalse(widget._is_visible({"value": 0.0}))
        self.assertTrue(widget._is_visible({"value": 1.0}))

    def test_condition_that_raises_fails_open(self):
        # ``count_records`` is zero when the period is empty: the condition
        # divides by zero and must leave the widget visible rather than hide it
        # silently.
        widget = self._widget(
            visible_expression="value / count_records > 1",
        )
        self.assertTrue(widget._is_visible({"value": 1.0, "count_records": 0}))

    def test_validate_rejects_an_unknown_name(self):
        with self.assertRaises(ValidationError):
            self._widget(visible_expression="secret > 0")

    def test_visibility_context_exposes_the_operands(self):
        widget = self._widget(
            formula_mode="custom",
            formula_expression="amount_total",
            visible_expression="amount_total > 0",
        )
        context = widget._visibility_context(
            {
                "value": 5.0,
                "record_count": 3,
                "operands": [{"alias": "amount_total", "value": 5.0}],
            }
        )
        self.assertEqual(context["value"], 5.0)
        self.assertEqual(context["amount_total"], 5.0)
        self.assertEqual(context["count_records"], 3)
