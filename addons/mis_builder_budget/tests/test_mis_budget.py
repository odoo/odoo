# Copyright 2017 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import datetime

from odoo.tests.common import TransactionCase

from odoo.addons.mis_builder.tests.common import assert_matrix

from ..models.mis_report_instance_period import SRC_MIS_BUDGET


class TestMisBudget(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # create report
        cls.report = cls.env["mis.report"].create(dict(name="test report"))
        cls.kpi1 = cls.env["mis.report.kpi"].create(
            dict(
                report_id=cls.report.id,
                name="k1",
                description="kpi 1",
                expression="10",
                budgetable=True,
            )
        )
        cls.expr1 = cls.kpi1.expression_ids[0]
        cls.kpi2 = cls.env["mis.report.kpi"].create(
            dict(
                report_id=cls.report.id,
                name="k2",
                description="kpi 2",
                expression="k1 + 1",
                sequence=0,  # kpi2 before kpi1 to test out of order evaluation
            )
        )
        # budget
        cls.budget = cls.env["mis.budget"].create(
            dict(
                name="the budget",
                report_id=cls.report.id,
                date_from="2017-01-01",
                date_to="2017-12-31",
                item_ids=[
                    (
                        0,
                        0,
                        dict(
                            kpi_expression_id=cls.expr1.id,
                            date_from="2017-01-01",
                            date_to="2017-01-31",
                            amount=10,
                        ),
                    ),
                    (
                        0,
                        0,
                        dict(
                            kpi_expression_id=cls.expr1.id,
                            date_from="2017-02-01",
                            date_to="2017-02-28",
                            amount=20,
                        ),
                    ),
                ],
            )
        )
        # instance
        cls.instance = cls.env["mis.report.instance"].create(
            dict(name="test instance", report_id=cls.report.id, comparison_mode=True)
        )
        cls.pact1 = cls.env["mis.report.instance.period"].create(
            dict(
                name="pact1",
                report_instance_id=cls.instance.id,
                manual_date_from="2017-01-01",
                manual_date_to="2017-01-31",
            )
        )
        cls.pbud1 = cls.env["mis.report.instance.period"].create(
            dict(
                name="pbud1",
                report_instance_id=cls.instance.id,
                source=SRC_MIS_BUDGET,
                source_mis_budget_id=cls.budget.id,
                manual_date_from="2017-01-01",
                manual_date_to="2017-01-31",
            )
        )
        cls.pact2 = cls.env["mis.report.instance.period"].create(
            dict(
                name="pact2",
                report_instance_id=cls.instance.id,
                manual_date_from="2017-02-01",
                manual_date_to="2017-02-28",
            )
        )
        cls.pbud2 = cls.env["mis.report.instance.period"].create(
            dict(
                name="pbud2",
                report_instance_id=cls.instance.id,
                source=SRC_MIS_BUDGET,
                source_mis_budget_id=cls.budget.id,
                manual_date_from="2017-02-01",
                manual_date_to="2017-02-21",
            )
        )
        # clear cache to force re-read of kpis ordered by sequence
        cls.env.clear()

    def test1(self):
        matrix = self.instance._compute_matrix()
        assert_matrix(
            matrix,
            [
                # jan, bud jan, feb (3w), bud feb (3w),
                [11, 11, 11, 16],  # k2 = k1 + 1
                [10, 10, 10, 15],  # k1
            ],
        )

    def test_drilldown(self):
        act = self.instance.drilldown(
            dict(period_id=self.pbud1.id, expr_id=self.expr1.id)
        )
        self.assertEqual(act["res_model"], "mis.budget.item")
        self.assertEqual(
            act["domain"],
            [
                ("date_from", "<=", datetime.date(2017, 1, 31)),
                ("date_to", ">=", datetime.date(2017, 1, 1)),
                ("kpi_expression_id", "=", self.expr1.id),
                ("budget_id", "=", self.budget.id),
            ],
        )

    def test_copy(self):
        budget2 = self.budget.copy()
        self.assertEqual(len(budget2.item_ids), len(self.budget.item_ids))

    def test_workflow(self):
        self.assertEqual(self.budget.state, "draft")
        self.budget.action_confirm()
        self.assertEqual(self.budget.state, "confirmed")
        self.budget.action_cancel()
        self.assertEqual(self.budget.state, "cancelled")
        self.budget.action_draft()
        self.assertEqual(self.budget.state, "draft")

    def test_name_search(self):
        report2 = self.report.copy()
        report2.kpi_ids.filtered(lambda k: k.name == "k1").name = "k1_1"
        budget2 = self.budget.copy()
        budget2.report_id = report2.id
        # search restricted to the context of budget2
        # hence we find only k1_1 in report2 and not k1
        expr = (
            self.env["mis.report.kpi.expression"]
            .with_context(default_budget_id=budget2.id)
            .name_search("k1")
        )
        self.assertEqual(len(expr), 1)
        self.assertEqual(expr[0][1], "kpi 1 (k1_1)")
        expr = (
            self.env["mis.report.kpi.expression"]
            .with_context(default_budget_id=budget2.id)
            .name_search("kpi 1")
        )
        self.assertEqual(len(expr), 1)
        self.assertEqual(expr[0][1], "kpi 1 (k1_1)")
