# Copyright 2023 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase

from odoo.addons.mis_builder_budget.models.mis_report_instance import (
    MisBudgetAwareExpressionEvaluator,
)


class TestBudgetAwareExpressionEvaluator(TransactionCase):
    def _make_evaluator(self, kpi_data=None):
        return MisBudgetAwareExpressionEvaluator(
            date_from="2017-01-01",
            date_to="2017-01-16",
            kpi_data=kpi_data or {},
            additional_move_line_filter=[],
        )

    def test_no_expression(self):
        evaluator = self._make_evaluator()
        evaluator.eval_expressions([None], locals_dict={})

    def test_one_expression(self):
        evaluator = self._make_evaluator()
        kpi = self.env["mis.report.kpi"].new({"name": "thekpi"})
        expr = self.env["mis.report.kpi.expression"].new(
            {"kpi_id": kpi.id, "name": "a"}
        )
        vals, drilldown_args, name_error = evaluator.eval_expressions(
            [expr], locals_dict={"a": 1}
        )
        self.assertEqual(vals, [1])
        self.assertEqual(drilldown_args, [None])
        self.assertFalse(name_error)

    def test_two_expressions(self):
        evaluator = self._make_evaluator()
        kpi = self.env["mis.report.kpi"].new({"name": "thekpi"})
        expr1 = self.env["mis.report.kpi.expression"].new(
            {"kpi_id": kpi.id, "name": "a"}
        )
        expr2 = self.env["mis.report.kpi.expression"].new(
            {"kpi_id": kpi.id, "name": "b"}
        )
        vals, drilldown_args, _ = evaluator.eval_expressions(
            [expr1, expr2], locals_dict={"a": 1, "b": 2}
        )
        self.assertEqual(vals, [1, 2])
        self.assertEqual(drilldown_args, [None, None])

    def test_two_expressions_with_budget(self):
        kpi = self.env["mis.report.kpi"].new({"name": "thekpi", "budgetable": True})
        expr1 = self.env["mis.report.kpi.expression"].new(
            {"kpi_id": kpi.id, "name": "a"}
        )
        expr2 = self.env["mis.report.kpi.expression"].new(
            {"kpi_id": kpi.id, "name": "b"}
        )
        kpi_data = {
            expr1: 10,
            expr2: 20,
        }
        evaluator = self._make_evaluator(kpi_data)
        vals, _, _ = evaluator.eval_expressions(
            [expr1, expr2], locals_dict={"a": 1, "b": 2}
        )
        self.assertEqual(vals, [10, 20])  # budget values instead of locals_dict values
