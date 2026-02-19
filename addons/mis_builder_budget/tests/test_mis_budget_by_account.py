# Copyright 2017 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase

from odoo.addons.mis_builder.models.expression_evaluator import ExpressionEvaluator
from odoo.addons.mis_builder.tests.common import assert_matrix

from ..models.mis_report_instance_period import SRC_MIS_BUDGET_BY_ACCOUNT


class TestMisBudgetByAccount(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # create account
        account = cls.env["account.account"].create(
            dict(
                name="test account",
                code="1",
                account_type="income",
            )
        )
        # create report
        cls.report = cls.env["mis.report"].create(dict(name="test report"))
        cls.kpi1 = cls.env["mis.report.kpi"].create(
            dict(
                report_id=cls.report.id,
                name="k1",
                description="kpi 1",
                expression=f"balp[('id', '=', {account.id})]",
            )
        )
        # budget
        cls.budget = cls.env["mis.budget.by.account"].create(
            dict(
                name="the budget",
                date_from="2017-01-01",
                date_to="2017-12-31",
                company_id=cls.env.ref("base.main_company").id,
                item_ids=[
                    (
                        0,
                        0,
                        dict(
                            account_id=account.id,
                            date_from="2017-01-01",
                            date_to="2017-01-08",
                            debit=11,
                        ),
                    ),
                    (
                        0,
                        0,
                        dict(
                            account_id=account.id,
                            date_from="2017-01-09",
                            date_to="2017-01-16",
                            debit=13,
                        ),
                    ),
                ],
            )
        )

    def test_basic(self):
        """Sum all budget items in period"""
        aep = self.report._prepare_aep(self.env.ref("base.main_company"))
        ee = ExpressionEvaluator(
            aep=aep,
            date_from="2017-01-01",
            date_to="2017-01-16",
            aml_model="mis.budget.by.account.item",
        )
        d = self.report._evaluate(ee)
        assert d["k1"] == 24.0

    def test_one_item(self):
        aep = self.report._prepare_aep(self.env.ref("base.main_company"))
        ee = ExpressionEvaluator(
            aep=aep,
            date_from="2017-01-01",
            date_to="2017-01-08",
            aml_model="mis.budget.by.account.item",
        )
        d = self.report._evaluate(ee)
        assert d["k1"] == 11.0

    def test_one_item_and_prorata_second(self):
        aep = self.report._prepare_aep(self.env.ref("base.main_company"))
        ee = ExpressionEvaluator(
            aep=aep,
            date_from="2017-01-01",
            date_to="2017-01-12",
            aml_model="mis.budget.by.account.item",
        )
        d = self.report._evaluate(ee)
        assert d["k1"] == 11.0 + 13.0 / 2

    def test_with_report_instance(self):
        instance = self.env["mis.report.instance"].create(
            dict(name="test instance", report_id=self.report.id, comparison_mode=True)
        )
        self.pbud1 = self.env["mis.report.instance.period"].create(
            dict(
                name="pbud1",
                report_instance_id=instance.id,
                source=SRC_MIS_BUDGET_BY_ACCOUNT,
                source_mis_budget_by_account_id=self.budget.id,
                manual_date_from="2017-01-01",
                manual_date_to="2017-01-31",
            )
        )
        matrix = instance._compute_matrix()
        assert_matrix(matrix, [[24]])

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

    def test_budget_item_balance(self):
        item = self.budget.item_ids[0]
        item.balance = 100
        self.assertEqual(item.debit, 100)
        item.balance = -100
        self.assertEqual(item.debit, 0)
        self.assertEqual(item.credit, 100)
